"""Write docs/index.html: a single-file, searchable view of release/swadesh_long.csv.

Data is embedded as compact JSON: L = [[code, name, url], ...], C = [concept, ...] (most widely attested
first), D = one list per concept of [language index, "form | form"] pairs.

Usage: python make_viewer.py
"""
import csv, json, os, collections

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REL, OUT = os.path.join(HERE, "release"), os.path.join(HERE, "docs")   # docs/ is served by GitHub Pages
os.makedirs(OUT, exist_ok=True)

langs, lidx = [], {}
for r in csv.DictReader(open(os.path.join(REL, "languages.csv"), encoding="utf-8")):
    if int(r["entries"]) == 0:
        continue
    lidx[r["source_url"]] = len(langs)
    langs.append([r["code"], r["name"], r["source_url"].rsplit("/", 1)[-1]])
concepts = [r["concept"] for r in csv.DictReader(open(os.path.join(REL, "concepts.csv"), encoding="utf-8"))]
cidx = {c: i for i, c in enumerate(concepts)}
cells = collections.defaultdict(list)
for r in csv.DictReader(open(os.path.join(REL, "swadesh_long.csv"), encoding="utf-8")):
    cells[(cidx[r["concept"]], lidx["https://archive.org/details/" + r["identifier"]])].append(r["form"])
D = [[] for _ in concepts]
for (ci, li), forms in sorted(cells.items()):
    D[ci].append([li, " | ".join(forms)])
data = json.dumps({"L": langs, "C": concepts, "D": D}, ensure_ascii=False, separators=(",", ":"))
data = data.replace("</", "<\\/")
html = open(os.path.join(HERE, "scripts", "viewer_template.html"), encoding="utf-8").read()
html = html.replace("__DATA__", data).replace("__NLANG__", f"{len(langs):,}").replace("__NCON__", f"{len(concepts):,}")
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(html)
print("docs/index.html", round(len(html.encode("utf-8")) / 1e6, 2), "MB;", len(langs), "lists,", len(concepts), "concepts")
