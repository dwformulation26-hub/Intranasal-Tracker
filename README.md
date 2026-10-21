# Intranasal Pipeline Radar

Bilingual (EN/KR) competitor tracker for intranasal products across all disease areas: sprays, powders, gels, implants and nasal vaccines. Same three-page format as the Presbyopia Pipeline Radar.

1. **Competitors**: 102 products in stage lanes (on market → stopped), with a disease-area × stage table, Korea/Global and disease-area filters, delivery device, and ClinicalTrials.gov trial records.
2. **Endpoints**: the usual approval routes (PK bridge vs efficacy program), pivotal endpoints by product type, nasal safety/device tests, guidance documents and next steps.
3. **News**: dated events Jan 2025 – Oct 2026, including delivery-system (device/platform) news.

Data as of 2026-10-21. Internal use only.

## Deploy

`index.html` is a single static file with all data built in, so it can be served as-is (GitHub Pages, Netlify, Vercel, an intranet web server). It loads only Google Fonts from outside.

## Update the data

| File | Role |
| --- | --- |
| `nasal_data.json` | All cards, news and endpoint content — edit this by hand |
| `template.html` | Page design and rendering code |
| `build.py` | `python build.py --from-data` re-renders `index.html` from `nasal_data.json` |
| `curate.py`, `tidy.py` | One-off clean-up steps already applied to `nasal_data.json` (duplicate removal, shortened labels) |
| `endpoints_frame.json` | Title, intro and "two routes" box of the Endpoints page (used when re-merging research) |
| `research_notes.json` | Researchers' notes on unconfirmed items |

`intranasal_tracker.html` is an identical copy of `index.html`.

## Verification

Accuracy audit completed 2026-10-21: every card, news item and endpoint row was checked against its source; every NCT matches ClinicalTrials.gov; every source link opens.

| Script | Checks |
| --- | --- |
| `verify_trials.py` | Every NCT against the ClinicalTrials.gov API (`--fix` overwrites trial fields with API values) |
| `verify_links.py` | Every source URL. SEC, BusinessWire, StockTitan and fda.gov block scripts (403/404), so check those in a browser |

Items still marked "(unconfirmed)" on the page are claims no public source could confirm.
