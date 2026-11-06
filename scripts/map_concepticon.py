"""Map each Swadesh concept label to a Concepticon concept set (Concepticon 3.2.0, CC BY 4.0).

Order: the mapping Concepticon itself gives for Swadesh 1952 (200 items), Swadesh 1955 (100) and Tadmor 2009
(Leipzig-Jakarta); then an exact match on the Concepticon gloss; then MANUAL, checked by hand (2026-11-06).
Inputs (download once into bulk/concepticon/ from github.com/concepticon/concepticon-data, tag v3.2.0):
concepticon.tsv, Swadesh-1952-200.tsv, Swadesh-1955-100.tsv, Tadmor-2009-100.tsv.
Output: concepticon_map.csv (concept, concepticon_id, concepticon_gloss, match, note). Standard library only.
"""
import csv, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(HERE, "bulk", "concepticon")
LISTS = ["Swadesh-1952-200", "Swadesh-1955-100", "Tadmor-2009-100"]

# concept -> (concepticon_id or "", note). Overrides automatic matches too.
MANUAL = {
    "fly (n.)": ("1504", "the automatic match gave FLY (MOVE THROUGH AIR); the noun is the insect"),
    "fly (v.)": ("1441", ""),
    "he/she": ("262", ""),
    "fat (n.)": ("323", ""),
    "fat": ("", "unmerged label: adjective in some lists, noun in others; no single concept set"),
    "grease": ("", "no Concepticon set for grease; close to FAT (ORGANIC SUBSTANCE) 323"),
    "day": ("1225", "Swadesh 'day' is daytime, not 24 hours"),
    "weep": ("1839", ""),
    "nape": ("1347", ""),
    "we (incl.)": ("1131", ""), "we (excl.)": ("1130", ""),
    "we two (incl.)": ("2637", ""), "we two (excl.)": ("2636", ""),
    "correct": ("1725", ""),
    "excrement": ("675", ""),
    "woomera": ("2677", "Australian spear-thrower"),
    "large": ("1202", "same concept set as 'big'"),
    "woods": ("420", "same concept set as 'forest'"),
    "calf": ("498", "lists with this label are body-part lists (calf of the leg), not young cattle"),
    "fullness": ("", "single list (car); no matching concept set"),
}


def main():
    cc = {r["ID"]: r for r in csv.DictReader(open(os.path.join(B, "concepticon.tsv"), encoding="utf8"), delimiter="\t")}
    by_gloss = {r["GLOSS"]: r["ID"] for r in cc.values()}
    listed = {}
    for name in LISTS:
        for r in csv.DictReader(open(os.path.join(B, name + ".tsv"), encoding="utf8"), delimiter="\t"):
            if r.get("CONCEPTICON_ID"):
                listed.setdefault(r["ENGLISH"].strip().lower(), (r["CONCEPTICON_ID"], name))
    concepts = [r["concept"] for r in csv.DictReader(open(os.path.join(HERE, "release", "concepts.csv"), encoding="utf8"))]
    out = []
    for c in concepts:
        k = c.replace(" (n.)", "").replace(" (v.)", "")
        if c in MANUAL:
            cid, note = MANUAL[c]
            how = "manual" if cid else "none"
        else:
            m = listed.get(c) or listed.get(k) or listed.get("the " + k) or listed.get("to " + k)
            cid, how = m if m else (by_gloss.get(k.upper(), ""), "gloss")
            note = ""
            if not cid:
                how = "none"
        out.append(dict(concept=c, concepticon_id=cid, concepticon_gloss=cc[cid]["GLOSS"] if cid else "",
                        match=how, note=note))
    with open(os.path.join(HERE, "concepticon_map.csv"), "w", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(Counter(o["match"] for o in out), [o["concept"] for o in out if not o["concepticon_id"]])


if __name__ == "__main__":
    main()
