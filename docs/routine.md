# Scheduled routine (recoverable copy)

The weekly update runs from a Claude cloud routine stored on the Claude account, not in this repo. If it ever has to be
recreated, use this definition, and update this file whenever the routine changes. Created 2026-10-22.

| Setting | Value |
|---|---|
| Name | Intranasal Radar - Weekly Update |
| Trigger id | `trig_01MbEiXWj4RQL6CGybWzNQxB` |
| Fires | Monday 08:00 KST - cron as stored (UTC): `0 23 * * 0` |
| Repository | `https://github.com/dwformulation26-hub/Intranasal-Tracker` |
| Output branch | none (must stay empty, or runs push to a side branch instead of `main`) |
| Environment | `env_016gKCnQEPe5JJhX4cWBatL5` (shared with the LAI Tracker routines) |
| Model | `claude-sonnet-5` |
| Allowed tools | Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch |
| Connector | Gmail, `create_draft` only |

Manage at <https://claude.ai/code/routines> or with `RemoteTrigger`. The GitHub Actions collector
(`.github/workflows/collect.yml`) runs at 06:00 KST every day; on Mondays it also syncs trials, two hours before the routine.

## Prompt

```text
Run the Intranasal Pipeline Radar weekly update. This repo is a bilingual (EN/KR) competitor tracker of intranasal drug, vaccine and device-drug products. Read .claude/skills/intranasal-weekly-update/SKILL.md in this checked-out repo first -- it is the complete, authoritative instructions for this task. Where this prompt and the skill differ, the skill wins.

All timing is KST. Start by running `TZ=Asia/Seoul date '+%Y-%m-%dT%H:%M:%S+09:00'` and use that single value as "now" for the whole run; every date you write is the KST date from `TZ=Asia/Seoul date +%F`. The sandbox clock is UTC, so never use a bare `date`.

Work in this one session: do not spawn sub-agents. Inputs are already collected by GitHub Actions in data/weekly/ (news_cache.json, trial_changes.json, trial_leads.json) and data/meta.json; clinicaltrials.gov is blocked in this sandbox, so use those files and never re-run sync_trials.py or discover_trials.py. If meta.json last_collect is more than 2 days old, run `python3 scripts/collect_news.py --when 8d` once and say the daily collector looked stalled.

Follow the skill's run order: triage every lead once (breadth first), update existing cards only on a Tier 1 source or two independent Tier 2 sources you opened this run, run the 25-card rotation check, add new products automatically only when all five conditions in the skill hold (explicitly intranasal, defined product, Tier 1 source opened this run, not already a card), add news items with the event's own date, and write every text field in English and Korean. Social (Bluesky) items are leads only and are never cited. Never cite a URL you did not open this run; never advance a lane on plans or expectations.

Before committing run `python3 build.py --as-of <KST date>`; it must pass, and a failure is fixed in the data, never in code. Never edit template.html, build.py, scripts/, config/, .github/, the endpoints content or the skill. Write data/weekly/reports/<KST date>.md and update data/meta.json even on a quiet run. Commit nasal_data.json, index.html and data/, then `git fetch origin main && git rebase origin/main && git push origin HEAD:main`, then `git fetch origin main && git branch -r --contains HEAD` must list origin/main; if not, lead your final summary with that.

Last step, after the push: create a Gmail DRAFT (never send) to dwformulation26@gmail.com with subject 'Intranasal Radar weekly - <KST date>: <headline>' and the report's headline, new products, card updates and news (English, then a short Korean summary). If Gmail fails, say so; the commit is what matters.
```
