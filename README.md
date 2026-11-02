# Rosetta Swadesh Lists

**Browse online: https://arktos-ai-lab.github.io/rosetta-swadesh/**

The Rosetta Project's Swadesh lists in one dataset: 1,232 lists (one per language or variety), 292 concept
labels, 362,236 word forms. The lists were moved to the Internet Archive in 2010
([announcement](https://rosettaproject.org/blog/02010/sep/20/Rosetta_Project_Swadesh_List_Data/)) as
1,237 separate items. This repository brings them together as CSV and SQLite files, with a searchable page
for browsing by concept or by language. Intended use includes seed vocabulary for multilingual databases.

## Files

| File | Content |
|---|---|
| `release/swadesh_long.csv` | one row per entry: `lang_code, language, concept, entry_no, form, label_original, identifier`. The format for importing into a database |
| `release/swadesh_wide.csv` | one row per concept, one column per list; several forms in one cell are joined with ` \| ` |
| `release/languages.csv` | one row per list: `code, name, identifier, entries, concepts, licence, origin, source_url` (join on `identifier`) |
| `release/inventory.csv` | every Rosetta Swadesh or vocabulary item on the Internet Archive (1,338), with kind, licence, and whether it is included and why not; also the **Sources** tab of the browsing page |
| `release/concepts.csv` | the concept labels and the number of lists that have each |
| `release/swadesh.sqlite` | tables `entries`, `languages`, `concepts` |
| `release/BUILD_REPORT.md` | counts, skipped lines, left-out items |
| `docs/index.html` | the browsing page (served by GitHub Pages) |
| `scripts/` | `harvest.py` (download the collection), `community.py` (add the openly licensed volunteer uploads), `build.py` (parse and write `release/`), `inventory.py` (write `release/inventory.csv`), `make_viewer.py` (write `docs/index.html`) |

Rebuild from scratch: `python scripts/harvest.py`, `python scripts/community.py`, `python scripts/build.py`,
`python scripts/inventory.py`, `python scripts/make_viewer.py` (Python 3.9 or newer, standard library only;
`community.py` needs `antiword` for three Word files; downloads go to `bulk/`).

## Source and processing

- Internet Archive, collection `rosettaproject`, search `swadesh`: 1,237 items, uploaded 2010-09-16. Each
  item has one text file of `concept: form` lines.
- Each line is split at the first colon. A concept can occur on several lines when a list merges more than
  one source; each line is kept as its own entry (`entry_no` 1, 2, ...). Forms are kept as written
  (Unicode NFC), commas inside a form are not split.
- Concept labels: 18 spelling variants of the same gloss are merged (for example `fat n.` → `fat (n.)`,
  `how?` → `how`, `tonge` → `tongue`; 348 entries; see `LABEL_MAP` in `scripts/build.py`). The label as
  written stays in `label_original`.
- The 10 collection items without a licence tag are left out (all 10 are empty there).
- Volunteers uploaded more Swadesh lists outside the collection in 2010-2011 (Internet Archive `opensource`,
  `opensource_media`, `opensource_audio`). The five with an open licence are included: Malay (Johor, CC BY 3.0),
  Slovenian (CC0) and three Ormuri lists (CC0; Ormuri is an endangered Iranian language of Pakistan and
  Afghanistan; list 3 gives each word in IPA and in Arabic script, kept as entry 1 and 2).
- `release/inventory.csv` accounts for all 1,338 Rosetta Swadesh and vocabulary items found on the Internet
  Archive: 1,232 included; 106 not included because they have no licence tag (68), are audio recordings (14),
  carry CC BY-SA (4), or are scanned book pages rather than typed lists (20 with a public domain mark, which
  could be OCRed later).

## Licence

- **Data:** the Internet Archive items carry the Rosetta Project's
  [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) tag (the five volunteer lists: CC BY 3.0 or CC0). Attribute "The Rosetta Project"; each list
  keeps its item URL in `languages.csv`. The 2010 announcement says the lists combine original work by Tim
  Usher and Paul Whitehouse with outside resources, among them Darrell Tryon's *Comparative Austronesian
  Dictionary* (1995), George Starostin's Dravidian database and Ilya Peiros' Mon-Khmer database. The files
  do not say which form came from which source, so the CC BY tag is the uploader's statement; we have not
  verified the rights in the underlying sources.
- **Code** (`scripts/`): MIT, see `LICENSE`.

## Known limitations

- `you` means 2nd person singular in some lists and plural in others (where `thou` is present). `we`,
  `we (incl.)` and `we (excl.)` reflect how each list was compiled.
- Some labels look alike but may differ in meaning and are not merged: `fat` (in Gaelic the adjective) vs
  `fat (n.)`, `large` vs `big`, `woods` vs `forest`.
- Language codes are kept as given (ISO 639-3 in most cases); not checked against Glottolog.
- Concept labels are not yet mapped to [Concepticon](https://concepticon.clld.org/) IDs, which would make
  the data comparable with CLDF/Lexibank datasets. Contributions welcome.

## Citation

> The Rosetta Project (2010). Swadesh lists, Internet Archive collection `rosettaproject`. Consolidated by
> Ernst van Gassen, Arktos AI Lab (2026), https://github.com/arktos-ai-lab/rosetta-swadesh
