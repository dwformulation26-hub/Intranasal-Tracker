# Intranasal Pipeline Radar

Bilingual (EN/KR) competitor tracker for intranasal products across all disease areas: sprays, powders, gels, implants
and nasal vaccines. Same three-page format as the Presbyopia Pipeline Radar.

1. **Competitors**: product cards in stage lanes (on market → stopped), disease-area × stage table, Korea/Global and
   disease-area filters, delivery device, ClinicalTrials.gov records. "New" / "Updated" badges mark recent changes.
2. **Endpoints**: approval routes, pivotal endpoints by product type, nasal safety/device tests, guidance, next steps.
3. **News**: dated events since Jan 2025, including delivery-system news.

`index.html` is one static file with all data built in - deploy it as-is. Internal use only.

## Weekly automation

| When (KST) | What | Where |
|---|---|---|
| Every day 03:00 | `scripts/collect_news.py`: ~50 feeds + Bluesky + openFDA → `data/weekly/news_cache.json` | GitHub Actions (`.github/workflows/collect.yml`) |
| Monday 03:00 | also `scripts/sync_trials.py` (refresh every tracked NCT) and `scripts/discover_trials.py` (new intranasal studies) | GitHub Actions |
| Monday 08:00 | Claude verifies the week's leads, updates cards and news in EN/KR, adds new products with an official source, runs QC, pushes to `main`, leaves a Gmail draft | Claude cloud routine, following `.claude/skills/intranasal-weekly-update/SKILL.md` |

Weekly reports: `data/weekly/reports/<date>.md`. Sources and the social-media evaluation: [docs/sources.md](docs/sources.md).
Routine definition (recoverable copy): [docs/routine.md](docs/routine.md).

Run the Action by hand: GitHub → Actions → "Collect leads" → Run workflow.

## Files

| File | Role |
|---|---|
| `nasal_data.json` | All cards, news and endpoint content |
| `template.html` | Page design and rendering code |
| `build.py` | `python build.py [--as-of YYYY-MM-DD]` validates the data and renders `index.html`; `--check` validates only |
| `config/feeds.json`, `config/keywords.json` | What the daily collector reads and keeps |
| `scripts/` | Collector, trial sync/discovery, ClinicalTrials.gov client, link checker |
| `data/meta.json` | Run bookkeeping: last collection/update, feed health, rotation cursor |
| `research_notes.json` | Original researchers' notes |

Accuracy audit completed 2026-10-21; items still marked "(unconfirmed)" are claims no public source could confirm.
