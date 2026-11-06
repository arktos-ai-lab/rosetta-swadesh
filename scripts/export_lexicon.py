"""Export a lexicon-ready view of the Swadesh data: one synset per concept, one lemma row per distinct form.

Written 2026-11-05 for importing into a wordnet-style database (synsets + lemmas). Reads release/swadesh.sqlite,
release/languages.csv and language_code_check.csv (from scripts/check_codes.py). Writes to export/:
- synsets.csv: synset_id, concept, gloss_note (sense to use; ambiguity warnings), n_lists
- lemmas.csv: synset_id, lemma, lang_code, glottocode, language, identifier, form_original, entry_nos,
  split_from_slash, flags, code_status, licence, source_url
Rules: forms are deduplicated per (synset, list, lemma); a form with "/" is split into separate lemmas only when
it has no backslash and no brackets (so tone notation such as `lo\\/n` and `a(-bi/ba)` stay whole); nothing else
is split. Standard library only.
"""
import csv, os, re, sqlite3
from collections import OrderedDict

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "export")

# Which sense the Swadesh/Leipzig-Jakarta tradition intends, and known ambiguities in this data.
NOTES = {
    "bark": "bark of a tree (noun), not a dog's bark",
    "lie": "lie down / lie on one's side (verb), not tell a lie",
    "fly (v.)": "to fly (verb)", "fly (n.)": "the insect (noun)",
    "fat (n.)": "fat, grease (noun)", "fat": "unmerged label: adjective in some lists (e.g. Gaelic), noun in others; check per list",
    "grease": "grease, fat (noun); close to 'fat (n.)'",
    "you": "2nd person: singular in some lists, plural in others (where 'thou' is present it is plural)",
    "thou": "2nd person singular", "he/she": "3rd person singular", "they": "3rd person plural",
    "we": "1st person plural; lists that distinguish use 'we (incl.)' / 'we (excl.)' instead",
    "we (incl.)": "1st person plural inclusive", "we (excl.)": "1st person plural exclusive",
    "we two": "1st person dual", "we two (incl.)": "1st person dual inclusive", "we two (excl.)": "1st person dual exclusive",
    "right": "right side (direction), not 'correct'", "left": "left side (direction)",
    "correct": "correct, right (adjective of truth)", "wood": "wood (material)", "woods": "woods (area); close to 'forest'",
    "forest": "forest", "large": "unmerged label; close to 'big'", "big": "big",
    "stick": "stick (noun)", "count": "to count (verb)", "turn": "to turn (verb)", "play": "to play (verb)",
}

# Source label errors corrected in the export (2026-11-06): (identifier, label) -> concept. The entry keeps the
# flag `label_fixed`. Gaelic `to: dà` is the numeral two (the list has no other 'two'); Atayal `strike tsy: mahiy`
# repeats its 'hit' entry with the same form.
LABEL_FIX = {
    ("rosettaproject_gla_swadesh-1", "to"): "two",
    ("rosettaproject_tay_swadesh-1", "strike tsy"): "hit",
}


def slug(c):
    return "swadesh_" + re.sub(r"[^a-z0-9]+", "_", c.lower()).strip("_")


def split_form(f):
    if "/" in f and "\\" not in f and not re.search(r"[()\[\]]", f):
        parts = [p.strip() for p in f.split("/") if p.strip()]
        if len(parts) > 1:
            return parts, True
    return [f.strip()], False


def flags(lemma):
    fl = []
    if lemma.startswith("-") or lemma.endswith("-"):
        fl.append("affix")
    if re.search(r"[()\[\]]", lemma):
        fl.append("brackets")
    if "," in lemma or ";" in lemma:
        fl.append("list_in_form")
    if " " in lemma:
        fl.append("multiword")
    if "?" in lemma:
        fl.append("uncertain")
    if "ø" in lemma or "Ø" in lemma:
        fl.append("zero_morph")
    if lemma.endswith("!"):
        fl.append("imperative_mark")
    return "|".join(fl)


def main():
    os.makedirs(OUT, exist_ok=True)
    langs = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(HERE, "release", "languages.csv"), encoding="utf8"))}
    chk_path = os.path.join(HERE, "language_code_check.csv")
    chk = {r["identifier"]: r for r in csv.DictReader(open(chk_path, encoding="utf8"))} if os.path.exists(chk_path) else {}
    db = sqlite3.connect(os.path.join(HERE, "release", "swadesh.sqlite"))
    cmap_path = os.path.join(HERE, "concepticon_map.csv")
    cmap = {r["concept"]: r for r in csv.DictReader(open(cmap_path, encoding="utf8"))} if os.path.exists(cmap_path) else {}
    rows = db.execute("select identifier, lang_code, concept, entry_no, form from entries order by identifier, concept, entry_no")
    lemmas = OrderedDict()
    for ident, code, concept, eno, form in rows:
        fixed = (ident, concept) in LABEL_FIX
        concept = LABEL_FIX.get((ident, concept), concept)
        parts, was_split = split_form(form)
        for lem in parts:
            key = (slug(concept), ident, lem)
            if key in lemmas:
                lemmas[key]["entry_nos"].append(str(eno))
                if form not in lemmas[key]["form_original"]:
                    lemmas[key]["form_original"].append(form)
                lemmas[key]["split_from_slash"] = lemmas[key]["split_from_slash"] or was_split
                if fixed and "label_fixed" not in lemmas[key]["flags"]:
                    lemmas[key]["flags"] = "|".join(filter(None, [lemmas[key]["flags"], "label_fixed"]))
                continue
            L, C = langs.get(ident, {}), chk.get(ident, {})
            fl = "|".join(filter(None, [flags(lem), "label_fixed" if fixed else ""]))
            lemmas[key] = dict(synset_id=key[0], lemma=lem, lang_code=code, glottocode=C.get("glottocode", ""),
                               language=L.get("name", ""), identifier=ident, form_original=[form], entry_nos=[str(eno)],
                               split_from_slash=was_split, flags=fl, code_status=C.get("status", ""),
                               licence=L.get("licence", ""), source_url=L.get("source_url", ""))
    with open(os.path.join(OUT, "lemmas.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(next(iter(lemmas.values()))))
        w.writeheader()
        for v in lemmas.values():
            w.writerow(dict(v, entry_nos="|".join(v["entry_nos"]), form_original=" || ".join(v["form_original"])))
    n = {}
    for (sid, ident, _), v in lemmas.items():
        n.setdefault(sid, set()).add(ident)
    concepts = [r[0] for r in db.execute("select distinct concept from entries") if slug(r[0]) in n]
    with open(os.path.join(OUT, "synsets.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["synset_id", "concept", "gloss_note", "n_lists", "concepticon_id", "concepticon_gloss"])
        for c in sorted(concepts, key=lambda c: -len(n.get(slug(c), ()))):
            m = cmap.get(c, {})
            note = "; ".join(filter(None, [NOTES.get(c, ""), m.get("note", "")]))
            w.writerow([slug(c), c, note, len(n.get(slug(c), ())), m.get("concepticon_id", ""), m.get("concepticon_gloss", "")])
    with open(os.path.join(OUT, "languages.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["identifier", "lang_code", "language", "glottocode", "glottolog_name", "macroarea", "code_status",
                    "code_note", "n_lemmas", "n_synsets", "licence", "source_url"])
        nl = {}
        for (sid, ident, _) in lemmas:
            nl.setdefault(ident, [0, set()])
            nl[ident][0] += 1
            nl[ident][1].add(sid)
        for ident, L in langs.items():
            C = chk.get(ident, {})
            w.writerow([ident, L["code"], L["name"], C.get("glottocode", ""), C.get("glottolog_name", ""),
                        C.get("macroarea", ""), C.get("status", ""), C.get("note", ""), nl.get(ident, [0])[0],
                        len(nl.get(ident, [0, ()])[1]), L.get("licence", ""), L.get("source_url", "")])
    total = db.execute("select count(*) from entries").fetchone()[0]
    print(f"entries {total} -> lemmas {len(lemmas)}; split rows {sum(v['split_from_slash'] for v in lemmas.values())}; "
          f"synsets {len(concepts)}; languages {len(langs)}; out {OUT}")


if __name__ == "__main__":
    main()
