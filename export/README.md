# Lexicon export (synsets + lemmas)

A database-ready view of the Rosetta Swadesh lists for importing into a wordnet-style lexicon: one synset per
concept, one row per distinct lemma per list. Built from `release/` by `scripts/export_lexicon.py`; nothing here
is hand-edited. Licence as for the release: CC BY 3.0 (a few lists CC0), attribute "The Rosetta Project"; the
licence and source URL of every list are in `languages.csv`. Concepticon IDs are from Concepticon 3.2.0 (CC BY 4.0;
mapping in `concepticon_map.csv`, made by `scripts/map_concepticon.py`); Glottocodes and macroareas are from Glottolog
(CC BY 4.0), matched by `scripts/check_codes.py` (result in `language_code_check.csv`).

## Files

| File | Rows | One row per |
|---|---|---|
| `synsets.csv` | 290 | concept |
| `lemmas.csv` | 296,956 | distinct lemma per (synset, list) |
| `languages.csv` | 1,232 | list (a language or variety; some languages have several lists) |

Join keys: `lemmas.synset_id` → `synsets.synset_id`; `lemmas.identifier` → `languages.identifier`.

## synsets.csv

| Column | Meaning |
|---|---|
| `synset_id` | `swadesh_` + the concept label in lower case, non-letters replaced by `_` (`fly (n.)` → `swadesh_fly_n`) |
| `concept` | the English concept label as used in the lists |
| `gloss_note` | the intended sense where the label is ambiguous (e.g. `bark` = tree bark, `lie` = lie down) and known problems |
| `n_lists` | number of lists with at least one lemma for this synset |
| `concepticon_id`, `concepticon_gloss` | the matching [Concepticon](https://concepticon.clld.org) concept set, a stable cross-dataset concept ID with a definition (e.g. 1504 = FLY (INSECT)); empty for `fat`, `grease`, `fullness` |

Two pairs share a Concepticon ID because the lists used two labels for one concept: `big`/`large` (1202) and
`forest`/`woods` (420). Merge them if you want one synset per concept.

## lemmas.csv

| Column | Meaning |
|---|---|
| `synset_id` | the concept |
| `lemma` | the word form |
| `lang_code` | ISO 639-3 code as given by the Rosetta Project |
| `glottocode` | Glottolog code (empty only for `wra`, see below) |
| `language` | language name as given by the Rosetta Project |
| `identifier` | the list (Internet Archive item) |
| `form_original` | the form(s) as written in the list, joined with ` \|\| ` when several entries gave the same lemma |
| `entry_nos` | which entries of that concept in that list, joined with `\|` |
| `split_from_slash` | `True` when the list wrote alternatives as `a/b` and they were split into separate lemmas |
| `flags` | `\|`-separated: `affix` (starts or ends with `-`), `brackets`, `list_in_form` (contains `,` or `;`), `multiword`, `uncertain` (`?`), `zero_morph` (`ø`), `imperative_mark` (ends in `!`), `label_fixed` (see below) |
| `code_status` | result of the language code check (see languages.csv) |
| `licence`, `source_url` | per list |

Splitting rule: a form with `/` is split only when it has no backslash and no brackets, so tone notation such as
`lo\/n` and optional parts such as `a(-bi/ba)` stay whole. Nothing else is split. Forms are otherwise exactly as in
the lists (Unicode NFC); lemmas with flags may need cleaning before use as dictionary headwords.

Two label errors in the source are corrected here and flagged `label_fixed`: Scottish Gaelic `to: dà` is the
numeral *two* (the list has no other entry for two), and Atayal `strike tsy: mahiy` repeats the list's *hit*
entry with the same form, so it is merged into `swadesh_hit`.

## languages.csv

| Column | Meaning |
|---|---|
| `identifier`, `lang_code`, `language` | the list, its ISO code and name as given by the Rosetta Project |
| `glottocode`, `glottolog_name`, `macroarea` | from Glottolog, matched on the ISO code |
| `code_status` | `ok` (1,179); `name_mismatch` (47: the Rosetta name differs from the ISO name, check which language is meant); `dialect` (4: Glottolog treats the code's languoid as a dialect); `remapped` (1: retired code `mwd` → `dmw` Mudburra); `unknown_code` (1: `wra`, not a current ISO 639-3 code) |
| `code_note` | what to check for non-`ok` rows |
| `n_lemmas`, `n_synsets` | counts in this export |
| `licence`, `source_url` | per list |

## Suggested import

1. Create the 290 synsets from `synsets.csv`; store `concepticon_id` on each as an external reference.
2. For the English side, create one new English lemma per synset from `concept` (with `gloss_note` as its
   definition) rather than attaching to existing English lemmas with the same spelling; the labels are
   ambiguous (`bark`, `lie`, `right`, `you`) and the Concepticon ID tells you which sense is meant.
3. Import `lemmas.csv` per language, using `glottocode` or `lang_code` to find or create the language, and keep
   `identifier` so every lemma stays traceable to its source list and licence.
