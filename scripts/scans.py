"""Write release/scanned_texts/: the OCR text of the scanned Rosetta vocabulary items that passed the
copyright check.

The Internet Archive gives these 20 items a public domain mark, but they are scans of book pages, not typed
lists. A separate check (PD_CHECK_pre1931.csv, 2026-11-02) verified the publication year from other
catalogues and the authors' death years, and required public domain in the US, in the country of
publication and in the Netherlands. Only the items that passed (`OPEN`) are taken; the others are listed in
release/inventory.csv with the reason.

The text is the Internet Archive's own OCR (`_djvu.txt`, ABBYY), kept as delivered: it has OCR errors and
the scans are excerpts (the vocabulary pages), not whole books. Resumable: files already downloaded are skipped.

Usage: python scans.py
"""
import csv, json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BULK, OUT = os.path.join(HERE, "bulk"), os.path.join(HERE, "release", "scanned_texts")
os.makedirs(os.path.join(BULK, "ocr"), exist_ok=True); os.makedirs(OUT, exist_ok=True)
H = {"User-Agent": "Arktos research (Rosetta Swadesh consolidation)"}


def get(url):
    for attempt in range(6):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=120).read()
        except Exception:
            time.sleep(10 * (attempt + 1))
    return None


check = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(HERE, "PD_CHECK_pre1931.csv"), encoding="utf-8"))}
inv = [r for r in csv.DictReader(open(os.path.join(HERE, "release", "inventory.csv"), encoding="utf-8"))
       if r["kind"] == "scanned excerpt" and r["licence_class"] == "open"]
rows = []
for r in inv:
    ident = r["identifier"]
    c = check.get(ident)
    if not c or c["overall"].strip().upper() != "OPEN":
        continue
    raw = os.path.join(BULK, "ocr", ident + ".txt")
    if not os.path.exists(raw):
        m = json.load(open(os.path.join(BULK, "inventory_meta", ident + ".json"), encoding="utf-8"))
        names = [f["name"] for f in m["files"] if f.get("format") == "DjVuTXT"]
        data = get(f"https://archive.org/download/{ident}/{urllib.parse.quote(names[0])}") if names else None
        if not data:
            print("no OCR text for", ident); continue
        open(raw + ".tmp", "wb").write(data); os.replace(raw + ".tmp", raw)
    text = open(raw, encoding="utf-8", errors="replace").read()
    open(os.path.join(OUT, ident + ".txt"), "w", encoding="utf-8").write(text)
    rows.append({"identifier": ident, "lang_code": r["lang_code"], "title": r["title"],
                 "creator": c["creator"], "year": c["verified_year"], "authors_death": c["latest_death_year"],
                 "country": c["country_of_publication"], "chars": len(text), "source_url": r["source_url"]})
    print(ident, len(text), "chars")
with open(os.path.join(OUT, "index.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader(); w.writerows(rows)
print(len(rows), "texts")
