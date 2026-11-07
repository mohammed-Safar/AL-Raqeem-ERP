# Arabic translation workspace

- `in/*.tsv` — source batches (all reviewed as of 2026-11-06)
  (Frappe settings doctypes and the less-used ERPNext modules). Format: key, English, current Arabic.
- `out/*.tsv` — finished work: `key<TAB>Arabic` (M/N = newly translated, R = corrections).
- `glossary_overrides.tsv` — terms forced everywhere (see `../../raqim_sales/translations/glossary.md`).
- Rebuild `raqim_sales/translations/ar.csv`:  `python3 build.py <this folder's parent of tr>`
  (build.py expects `<dir>/tr/items.json`, `<dir>/tr/out/`, `<dir>/tr/glossary_overrides.tsv`).

After rebuilding: `bench --site site2.local clear-cache` and reload the browser.
