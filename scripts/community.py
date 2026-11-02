"""Add the openly licensed Rosetta Swadesh lists that volunteers uploaded outside the `rosettaproject`
collection (Internet Archive `opensource` / `opensource_media`, 2010-2011).

Only items with an open licence tag (CC BY or CC0) are taken; see release/inventory.csv for every item and
why it is or is not included. Each list is downloaded, converted to `concept: form` lines and written to
bulk/raw/<identifier>.txt with a .json metadata file, so build.py treats it like the other lists.
Word files are converted with antiword. Resumable: an item whose two output files exist is skipped.

Formats seen: `N.<tab>concept - form` (zlm, slv; slv adds grammatical notes in brackets, kept as written),
`concept: form` (oru-1), and pairs of lines `N.<Arabic-script form>` / `concept ; IPA form` (oru-3; the IPA
form becomes entry 1 and the Arabic-script form entry 2).

Usage: python community.py
"""
import json, os, re, subprocess, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, DL = os.path.join(HERE, "bulk", "raw"), os.path.join(HERE, "bulk", "community")
os.makedirs(DL, exist_ok=True)
H = {"User-Agent": "Arktos research (Rosetta Swadesh consolidation)"}

ITEMS = {  # identifier: (file in the item, language code, language name)
    "rosettaproject_zlm_swadesh-1": ("zlm-swadesh-1.txt", "zlm", "Malay (Johor)"),
    "rosettaproject_slv_swadesh-1": ("SwadeshList.doc", "slv", "Slovenian"),
    "rosettaproject_oru_swadesh-1": ("OrmuriWords.doc", "oru", "Ormuri"),
    "rosettaproject_oru_swadesh-2": ("OrmuriWordsList.doc", "oru", "Ormuri"),
    "rosettaproject_oru_swadesh-3": ("OrmuriSwadeshList.doc", "oru", "Ormuri"),
}
# Concept labels written differently in these lists -> labels used by the main lists.
CONCEPT = {"you (singular)": "thou", "you (plural)": "you", "you (pl)": "you", "he": "he/she",
           "man (adult male)": "man", "man (human being)": "person", "eyes": "eye", "winɡs": "wing",
           "sucking": "suck"}
NUM = re.compile(r"^\s*\d+\s*[.)]?\s*")
SEP = re.compile(r"\s*(?::|;|-\s+|\s+-|[–—�])\s*")   # hyphens inside forms (ca-ra) do not split
ARABIC = re.compile(r"[؀-ۿ]")


def get(url):
    for attempt in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read()
        except Exception:
            time.sleep(5 * (attempt + 1))
    return None


def to_text(path, data):
    if path.endswith(".doc"):
        r = subprocess.run(["antiword", "-w", "0", "-m", "UTF-8.txt", path], capture_output=True)
        return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252")


def parse(text):
    out, script, num, last = [], None, None, None
    for line in text.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        m = NUM.match(line)
        if m and m.group().strip():
            num = int(re.match(r"\s*(\d+)", line).group(1))
        body = NUM.sub("", line)
        if ARABIC.search(body) and not re.search(r"[A-Za-z]", body):   # oru-3: script form on its own line
            script = body.strip(" .")
            continue
        parts = SEP.split(body, maxsplit=1)
        if len(parts) != 2 or not parts[0] or not parts[1].strip():
            script = None
            continue
        concept, form = parts[0].strip().lower(), parts[1].strip()
        if len(concept) > 40:   # headings and notes, not entries
            continue
        if concept == "nd" and last:        # oru-3 "2nd ; deem": a second form of the previous concept
            concept = last
        if concept == "you" and num == 2:   # Swadesh no. 2 is the singular (oru-3 writes plain "you")
            concept = "thou"
        concept = CONCEPT.get(concept, concept)
        out.append(f"{concept}: {form}")
        last = concept
        if script:
            out.append(f"{concept}: {script}")
            script = None
    return out


for ident, (fname, code, name) in ITEMS.items():
    tpath, jpath = os.path.join(RAW, ident + ".txt"), os.path.join(RAW, ident + ".json")
    if os.path.exists(tpath) and os.path.exists(jpath):
        print("skip", ident); continue
    src = os.path.join(DL, ident + os.path.splitext(fname)[1])
    if not os.path.exists(src) or os.path.getsize(src) < 1000:
        data = get(f"https://archive.org/download/{ident}/{fname}")
        if not data or data.lstrip().startswith(b"<html"):
            print("download failed", ident); continue
        open(src, "wb").write(data)
    meta = json.loads(get("https://archive.org/metadata/" + ident) or b"{}").get("metadata", {})
    lines = parse(to_text(src, open(src, "rb").read()))
    if not lines:
        print("nothing parsed", ident); continue
    meta.update({"language": code, "title": name + " Swadesh List", "origin": "community upload"})
    open(tpath, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    json.dump({"identifier": ident, "text_file": fname, "metadata": meta},
              open(jpath, "w", encoding="utf-8"), ensure_ascii=False)
    print(ident, len(lines), "entries,", meta.get("licenseurl"))
