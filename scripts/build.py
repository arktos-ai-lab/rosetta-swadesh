"""Build the consolidated Rosetta Swadesh dataset from bulk/raw/ (see harvest.py).

Outputs in release/:
  swadesh_long.csv     one row per entry: lang_code, language, concept, entry_no, form, source_url, licence
  swadesh_wide.csv     one row per concept, one column per language (entries joined with " | ")
  languages.csv        one row per list: code, name, entries, concepts, licence, origin, source_url
  concepts.csv         one row per concept label, with the number of languages that have it
  swadesh.sqlite       the long, languages and concepts tables
  BUILD_REPORT.md      counts, lines that could not be parsed, lists with no licence tag (left out)

Parsing rule: each non-empty line is `concept: form`, split at the first colon. A concept can occur on
several lines (the lists merge more than one source); each line is kept as its own entry, in file order.
Forms are kept exactly as written (commas inside a form are not split).

Concept labels: spelling variants of the same Swadesh gloss are merged via LABEL_MAP (checked 2026-11-02:
no list has both the variant and the target, except where noted). The label as written is kept in
`label_original`. Labels that look similar but may mean something else (`fat` vs `fat (n.)`: Gaelic
`reamhar` is the adjective; `fullness`, `large`, `heat`, `grease`, `woods`) are left as they are.
"""
import collections, csv, glob, json, os, sqlite3, unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, OUT = os.path.join(HERE, "bulk", "raw"), os.path.join(HERE, "release")
os.makedirs(OUT, exist_ok=True)

LABEL_MAP = {
    "fat n.": "fat (n.)", "fly v.": "fly (v.)", "walk (go)": "walk", "burn tr.": "burn",
    "full(ness)": "full", "claw (nail": "claw", "claw(nail)": "claw",
    "how?": "how", "when?": "when", "where?": "where", "meat?": "meat",   # pag has both `how?` and `how` (same word)
    "tonge": "tongue", "breat": "breast", "snooth": "smooth",
    "ye": "you",            # 2nd person plural in the 14 lists that pair it with `thou`
    "he": "he/she",         # ktb has both
    "ash": "ashes",         # tam, tel have both (two different words, kept as entry 1 and 2)
    "fly": "fly (v.)",      # tam, tel: verb forms; tel has both
}

langs, rows, bad, nolic = [], [], [], []
for jp in sorted(glob.glob(os.path.join(RAW, "*.json"))):
    j = json.load(open(jp, encoding="utf-8"))
    m, ident = j["metadata"], j["identifier"]
    code = (m.get("language") or ident.split("_")[1].split("-")[0])
    code = code[0] if isinstance(code, list) else code
    name = (m.get("title") or "").removesuffix(" Swadesh List").strip()
    lic = m.get("licenseurl") or ""
    if not lic:  # no licence tag: left out of the release (only openly licensed material is redistributed)
        nolic.append(ident)
        continue
    origin = m.get("origin") or "rosettaproject collection"
    url = "https://archive.org/details/" + ident
    text = open(jp[:-5] + ".txt", encoding="utf-8", errors="replace").read()
    # Split on newlines only: str.splitlines() also splits on U+2028, which occurs inside one entry (tay "strike").
    text = unicodedata.normalize("NFC", text.lstrip("﻿")).replace(" ", " ").replace("\r", "")
    seen = collections.Counter()
    n = 0
    for ln, line in enumerate(text.split("\n"), 1):
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            bad.append((ident, ln, line[:80]))
            continue
        concept, form = (s.strip() for s in line.split(":", 1))
        if not concept or not form:
            bad.append((ident, ln, line[:80]))
            continue
        label = concept.lower()
        concept = LABEL_MAP.get(label, label)
        seen[concept] += 1
        rows.append({"lang_code": code, "language": name, "concept": concept, "entry_no": seen[concept],
                     "form": form, "label_original": label, "identifier": ident, "source_url": url, "licence": lic})
        n += 1
    langs.append({"code": code, "name": name, "identifier": ident, "entries": n, "concepts": len(seen),
                  "licence": lic, "origin": origin, "source_url": url})

concept_langs = collections.defaultdict(set)
for r in rows:
    concept_langs[r["concept"]].add(r["lang_code"] + "|" + r["source_url"])
concepts = sorted(({"concept": c, "languages": len(s)} for c, s in concept_langs.items()),
                  key=lambda d: (-d["languages"], d["concept"]))


def write_csv(name, recs, fields):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader(); w.writerows(recs)


# Source URL and licence live in languages.csv (join on identifier); repeating them per row tripled the size.
write_csv("swadesh_long.csv", rows, ["lang_code", "language", "concept", "entry_no", "form", "label_original", "identifier"])
write_csv("languages.csv", langs, ["code", "name", "identifier", "entries", "concepts", "licence", "origin", "source_url"])
write_csv("concepts.csv", concepts, ["concept", "languages"])

# Wide: column header is the identifier's language code; two lists for one code get a suffix.
cols, colkey = [], {}
for l in langs:
    h = l["code"]
    k = 2
    while h in cols:
        h = f"{l['code']}_{k}"; k += 1
    cols.append(h); colkey[l["source_url"]] = h
cells = collections.defaultdict(list)
for r in rows:
    cells[(r["concept"], colkey[r["source_url"]])].append(r["form"])
with open(os.path.join(OUT, "swadesh_wide.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["concept"] + cols)
    for c in concepts:
        w.writerow([c["concept"]] + [" | ".join(cells.get((c["concept"], h), [])) for h in cols])

db = os.path.join(OUT, "swadesh.sqlite")
if os.path.exists(db):
    os.remove(db)
con = sqlite3.connect(db)
con.execute("CREATE TABLE languages (code TEXT, name TEXT, identifier TEXT PRIMARY KEY, entries INT, concepts INT, licence TEXT, origin TEXT, source_url TEXT)")
con.execute("CREATE TABLE concepts (concept TEXT PRIMARY KEY, languages INT)")
con.execute("CREATE TABLE entries (identifier TEXT REFERENCES languages(identifier), lang_code TEXT, concept TEXT, entry_no INT, form TEXT, label_original TEXT)")
con.executemany("INSERT INTO languages VALUES (:code,:name,:identifier,:entries,:concepts,:licence,:origin,:source_url)", langs)
con.executemany("INSERT INTO concepts VALUES (:concept,:languages)", concepts)
con.executemany("INSERT INTO entries VALUES (:identifier,:lang_code,:concept,:entry_no,:form,:label_original)", rows)
con.execute("CREATE INDEX ix_e ON entries(lang_code, concept)")
con.commit(); con.close()

empty = [l["identifier"] for l in langs if l["entries"] == 0]
dup_codes = [c for c, n in collections.Counter(l["code"] for l in langs).items() if n > 1]
per = sorted(l["concepts"] for l in langs if l["entries"])
rep = ["# Build report", "",
       f"- Lists: {len(langs)} ({len(empty)} empty); distinct language codes: {len(set(l['code'] for l in langs))}",
       f"- Entries: {len(rows)}; distinct concept labels: {len(concepts)}",
       f"- Concepts per list: min {per[0] if per else 0}, median {per[len(per)//2] if per else 0}, max {per[-1] if per else 0}",
       f"- Concepts in at least 1,000 lists: {sum(c['languages'] >= 1000 for c in concepts)}; in at least 500: {sum(c['languages'] >= 500 for c in concepts)}",
       f"- Entries whose label was merged into a standard gloss (LABEL_MAP): {sum(r['label_original'] != r['concept'] for r in rows)}",
       f"- Lines not in `concept: form` shape (skipped): {len(bad)}",
       f"- Lists without a licence tag (left out): {len(nolic)}: {', '.join(nolic) or 'none'}",
       f"- Language codes with more than one list: {len(dup_codes)}: {', '.join(sorted(dup_codes)) or 'none'}",
       f"- Empty lists: {', '.join(empty) or 'none'}", "", "## Skipped lines (first 50)", ""]
rep += [f"- `{i}` line {ln}: `{t}`" for i, ln, t in bad[:50]]
open(os.path.join(OUT, "BUILD_REPORT.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")
print("\n".join(rep[:10]))
