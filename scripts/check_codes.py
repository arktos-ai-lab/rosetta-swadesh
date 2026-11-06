"""Check every list's language code against ISO 639-3 (SIL code table) and Glottolog (languoid table).

Inputs: release/languages.csv and two small reference tables in --raw (default bulk/):
- iso.tab: the SIL ISO 639-3 code table (https://iso639-3.sil.org/code_tables/download_tables, iso-639-3.tab)
- glot.csv: Glottolog's CLDF languages table (github.com/glottolog/glottolog-cldf, cldf/languages.csv; CC BY 4.0)
Output: language_code_check.csv, one row per list, with a status and a short note. Standard library only.
Usage: python scripts/check_codes.py [--raw <dir with iso.tab and glot.csv>]
"""
import argparse, csv, difflib, os, unicodedata

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LAB_RAW = os.path.join(HERE, "..", "..", "10-license-audits", "00-world-language-sources", "raw")
DEFAULT_RAW = _LAB_RAW if os.path.exists(os.path.join(_LAB_RAW, "iso.tab")) else os.path.join(HERE, "bulk")


# Hand mappings for retired codes, each checked against the SIL code table (2026-11-05).
MANUAL_CODE = {"mwd": "dmw"}
MANUAL = {"mwd": "retired code; Mudburra is ISO 639-3 dmw (checked in SIL code table); glottocode taken from dmw"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    if "," in s:  # Ethnologue-style inverted names: "Arabic, Omani Spoken" -> "omani spoken arabic"
        head, _, rest = s.partition(",")
        s = rest + " " + head
    s = s.replace(" spoken", " ").replace("spoken ", " ")
    return " ".join("".join(c for c in s if c.isalnum() or c == " ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=DEFAULT_RAW)
    a = ap.parse_args()
    iso = {r["Id"]: r for r in csv.DictReader(open(os.path.join(a.raw, "iso.tab"), encoding="utf8"), delimiter="\t")}
    glot = {}
    for r in csv.DictReader(open(os.path.join(a.raw, "glot.csv"), encoding="utf8")):
        if r["ISO639P3code"]:
            glot[r["ISO639P3code"]] = r
    out = []
    for r in csv.DictReader(open(os.path.join(HERE, "release", "languages.csv"), encoding="utf8")):
        code, name = r["code"], r["name"]
        i, g = iso.get(code), glot.get(code)
        sim = 0.0
        if i:
            sim = difflib.SequenceMatcher(None, norm(name), norm(i["Ref_Name"])).ratio()
        if code in MANUAL:
            status, note = "remapped", MANUAL[code]
            i, g = iso.get(MANUAL_CODE[code]), glot.get(MANUAL_CODE[code])
        elif not i and not g:
            status, note = "unknown_code", "not a current ISO 639-3 code (retired, private or typo); map by hand"
        elif i and i["Scope"] == "M":
            status, note = "macrolanguage", "ISO macrolanguage; the list may be one member language"
        elif i and sim < 0.5 and norm(name) not in norm(i["Ref_Name"]) and norm(i["Ref_Name"]) not in norm(name):
            status, note = "name_mismatch", f"Rosetta name differs from ISO name '{i['Ref_Name']}'; check which language is meant"
        elif g and g["Level"] == "dialect":
            status, note = "dialect", "Glottolog classifies this code's languoid as a dialect"
        elif not g:
            status, note = "no_glottocode", "valid ISO code but no Glottolog languoid with it"
        else:
            status, note = "ok", ""
        out.append(dict(identifier=r["identifier"], code=code, rosetta_name=name,
                        iso_name=i["Ref_Name"] if i else "", iso_scope=i["Scope"] if i else "",
                        iso_type=i["Language_Type"] if i else "",
                        glottocode=g["Glottocode"] if g else "", glottolog_name=g["Name"] if g else "",
                        glottolog_level=g["Level"] if g else "", macroarea=g["Macroarea"] if g else "",
                        name_similarity=round(sim, 2), status=status, note=note))
    path = os.path.join(HERE, "language_code_check.csv")
    with open(path, "w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(path)
    for k, v in Counter(o["status"] for o in out).most_common():
        print(f"{k}\t{v}")


if __name__ == "__main__":
    main()
