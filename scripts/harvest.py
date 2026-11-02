"""Download every Rosetta Project Swadesh list from the Internet Archive (collection `rosettaproject`,
query `swadesh`; 1,237 items on 2026-11-02) with its item metadata.

Item metadata (title, language, licence) comes from one Archive search call. Each item holds one
`<code>.txt` file of `concept: form` lines, downloaded with a few parallel workers; when the expected file
name is missing, the item's file list is looked up. Files go to bulk/raw/<identifier>.txt and metadata to
bulk/raw/<identifier>.json. Resumable: an item whose two files exist is skipped, and each file is written to
a .tmp and renamed, so a crash loses at most the items in flight.

Usage: python harvest.py [--workers 6]
"""
import argparse, json, os, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(HERE, "bulk", "raw"); os.makedirs(RAW, exist_ok=True)
H = {"User-Agent": "Arktos research (Rosetta Swadesh consolidation)"}
ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6)
args = ap.parse_args()


def get(url, binary=False):
    for attempt in range(6):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60).read()
            return data if binary else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (attempt + 1))
        except Exception:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("giving up on " + url)


def save(path, data):
    with open(path + ".tmp", "wb") as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(path + ".tmp", path)


FIELDS = ["identifier", "title", "language", "licenseurl", "contributor", "description", "subject", "date"]
q = urllib.parse.urlencode([("q", "swadesh AND collection:rosettaproject"), ("rows", 5000), ("output", "json")]
                           + [("fl[]", f) for f in FIELDS])
docs = get("https://archive.org/advancedsearch.php?" + q)["response"]["docs"]
print(len(docs), "items", flush=True)


def fetch(d):
    ident = d["identifier"]
    jpath, tpath = os.path.join(RAW, ident + ".json"), os.path.join(RAW, ident + ".txt")
    if os.path.exists(jpath) and os.path.exists(tpath):
        return "skip"
    code = ident.split("_")[1].split("-")[0]
    name = code + ".txt"
    body = get(f"https://archive.org/download/{ident}/{name}", binary=True)
    if body is None:                                   # unexpected file name: look it up
        meta = get("https://archive.org/metadata/" + ident) or {}
        txt = [f["name"] for f in meta.get("files", []) if f.get("format") == "Text"
               and f["name"].endswith(".txt") and not f["name"].endswith("_meta.txt")]
        name = txt[0] if txt else None
        body = get(f"https://archive.org/download/{ident}/{urllib.parse.quote(name)}", binary=True) if name else None
    save(tpath, body or b"")
    save(jpath, json.dumps({"identifier": ident, "text_file": name if body else None, "metadata": d},
                           ensure_ascii=False).encode("utf-8"))
    return "ok" if body else "empty"


stats = {"ok": 0, "skip": 0, "empty": 0}
with ThreadPoolExecutor(args.workers) as ex:
    for i, fut in enumerate(as_completed([ex.submit(fetch, d) for d in docs]), 1):
        stats[fut.result()] += 1
        if i % 100 == 0:
            print(i, "/", len(docs), stats, flush=True)
print("done", stats, flush=True)
