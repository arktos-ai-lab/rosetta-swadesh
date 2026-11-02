"""Write release/inventory.csv: every Rosetta Project Swadesh or vocabulary item on the Internet Archive, with
whether it is in this dataset and, if not, why.

Scope: items whose identifier starts with `rosettaproject` and whose identifier contains `swadesh` or `vocab`,
or whose title or description mentions Swadesh, plus every `swadesh` hit in the `rosettaproject` collection.
This also finds the lists volunteers uploaded outside the collection in 2010-2011 (`opensource`,
`opensource_media`, `opensource_audio`). Search results and item metadata are cached in bulk/ (delete
bulk/inventory_search.json to search again). Run after build.py; make_viewer.py shows the result.

Usage: python inventory.py
"""
import csv, json, os, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BULK, REL = os.path.join(HERE, "bulk"), os.path.join(HERE, "release")
META = os.path.join(BULK, "inventory_meta"); os.makedirs(META, exist_ok=True)
H = {"User-Agent": "Arktos research (Rosetta Swadesh consolidation)"}
FL = ["identifier", "title", "collection", "licenseurl", "date", "publicdate", "language", "mediatype", "creator"]


def get(url):
    for attempt in range(5):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=120).read())
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("giving up on " + url)


def search(q):
    qs = urllib.parse.urlencode([("q", q), ("rows", 5000), ("output", "json")] + [("fl[]", f) for f in FL])
    return get("https://archive.org/advancedsearch.php?" + qs)["response"]["docs"]


def s(v):
    return "; ".join(map(str, v)) if isinstance(v, list) else str(v or "")


cache = os.path.join(BULK, "inventory_search.json")
if os.path.exists(cache):
    items = json.load(open(cache, encoding="utf-8"))
else:
    items = {d["identifier"]: d for d in search("identifier:rosettaproject* AND (identifier:*swadesh* OR "
                                                "identifier:*vocab* OR title:swadesh OR description:swadesh)")}
    items.update({d["identifier"]: d for d in search("collection:rosettaproject AND swadesh")})
    json.dump(items, open(cache, "w", encoding="utf-8"), ensure_ascii=False)

released = {r["identifier"]: r for r in csv.DictReader(open(os.path.join(REL, "languages.csv"), encoding="utf-8"))}


def meta(ident):
    p = os.path.join(META, ident + ".json")
    if not os.path.exists(p):
        m = get("https://archive.org/metadata/" + ident)
        json.dump({"files": [{k: f.get(k) for k in ("name", "format", "size")} for f in m.get("files", [])],
                   "metadata": m.get("metadata", {})}, open(p, "w", encoding="utf-8"), ensure_ascii=False)
    return json.load(open(p, encoding="utf-8"))


with ThreadPoolExecutor(6) as ex:
    metas = dict(zip(sorted(items), ex.map(meta, sorted(items))))


def licence_class(url):
    u = url.lower()
    if not u:
        return "no tag"
    if "-nc" in u or "-nd" in u or "-sa" in u:
        return "restricted"
    if "/by/" in u or "zero" in u or "publicdomain" in u:
        return "open"
    return "other"


def short(url):
    u = url.lower().rstrip("/")
    if not u:
        return "none"
    if "publicdomain/zero" in u:
        return "CC0 1.0"
    if "publicdomain" in u:
        return "Public domain mark"
    part = u.split("/licenses/")[-1].split("/")
    return "CC " + part[0].upper() + (" " + part[1] if len(part) > 1 else "")


rows = []
for ident, d in sorted(items.items()):
    m = metas[ident]
    md = m["metadata"]
    lic = s(d.get("licenseurl"))
    fmts = {f.get("format") for f in m["files"]}
    media = s(d.get("mediatype"))
    title = s(md.get("title") or d.get("title"))
    if "audio" in ident or media == "audio":
        kind = "audio recording"
    elif "swadesh" in ident and ("Text" in fmts or "Word Document" in fmts):
        kind = "Swadesh list (typed)"
    elif "swadesh" in ident:
        kind = "Swadesh list (scanned)"
    elif "swadesh" in (title + s(md.get("description"))).lower():
        kind = "Swadesh list (scanned)"
    else:
        kind = "scanned excerpt"
    lc = licence_class(lic)
    if ident in released:
        status, reason = "included", ("Rosetta Project collection" if released[ident]["origin"].startswith("rosetta")
                                      else "volunteer upload outside the collection, open licence")
    elif kind == "audio recording":
        status = "not included"
        reason = "audio, not text" + ("; licence open, candidate for a separate audio set" if lc == "open" else "")
    elif lc == "no tag":
        status, reason = "not included", "no licence tag"
    elif lc == "restricted":
        status, reason = "not included", f"licence not open enough for this release ({short(lic)})"
    elif kind != "Swadesh list (typed)":
        status, reason = "not included", "scanned pages, not a typed list" + ("; public domain mark, could be OCRed" if lc == "open" else "")
    else:
        status, reason = "not included", "open licence but not yet converted"
    rows.append({"identifier": ident, "lang_code": (ident.split("_")[1] if ident.count("_") >= 2 else ""),
                 "title": title, "kind": kind, "licence": short(lic), "licence_class": lc,
                 "ia_collection": s(d.get("collection")), "uploaded": s(d.get("publicdate"))[:10],
                 "status": status, "reason": reason, "source_url": "https://archive.org/details/" + ident})

with open(os.path.join(REL, "inventory.csv"), "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader(); w.writerows(rows)
from collections import Counter
print(len(rows), "items:", dict(Counter(r["status"] for r in rows)))
for k, v in sorted(Counter((r["status"], r["kind"], r["reason"]) for r in rows).items()):
    print(f"{v:5d}  {k[0]} | {k[1]} | {k[2]}")
missing = set(released) - set(items)
if missing:
    print("in release but not found by the inventory search:", sorted(missing))
