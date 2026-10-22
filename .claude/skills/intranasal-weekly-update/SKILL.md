---
name: intranasal-weekly-update
description: Runs the Intranasal Pipeline Radar's weekly update - turns the week's collected leads (ClinicalTrials.gov changes, new intranasal trials, news feeds, Bluesky early-warning posts) into verified, bilingual updates to the competitor cards (page 1) and the news list (page 3), adds new products backed by an official source, runs QC, pushes to main and leaves a Gmail draft summary. Use whenever a scheduled routine or a person asks to "run the intranasal weekly update", "update the intranasal tracker", or "refresh the nasal tracker". Never edits page design, scripts or the Endpoints page.
---

# Intranasal Pipeline Radar - weekly update

This runs unattended from a scheduled cloud routine with no memory of earlier runs. Follow it exactly: the value of a
tracker is that every week applies the same rules, so drift never accumulates. The page is read by a manager who trusts
it, so **an item you could not verify is left out, never guessed**.

## What is already done for you (GitHub Actions, no AI)

| File | Written by | When (KST) | Contents |
|---|---|---|---|
| `data/weekly/news_cache.json` | `scripts/collect_news.py` | every day 06:00 | Rolling 21-day cache of keyword-matched items from ~50 feeds (Google News EN/KO/JA/ZH, FDA, EMA, MFDS, PMDA, DART, wires, trade press, 11 Korean outlets), openFDA nasal submissions, and Bluesky posts (`kind: "social"`). Each item has `status` `new` / `used` / `dismissed`. |
| `data/weekly/trial_changes.json` | `scripts/sync_trials.py` | Monday 06:00 | Every tracked NCT re-read from ClinicalTrials.gov; the API values are **already written** into `nasal_data.json`. `notable: true` = status, results or primary-completion change. |
| `data/weekly/trial_leads.json` | `scripts/discover_trials.py` | Monday 06:00 | Untracked interventional intranasal product studies updated since the last collection, with `relatedCards` guesses and `newRegistration`. |
| `data/meta.json` | both | | `last_collect`, `feed_health`, `last_update_run`, `rotation_cursor`, `source_health`. |

The cloud sandbox blocks direct access to clinicaltrials.gov, so never try to re-run `sync_trials.py` or
`discover_trials.py` here; rely on the files above. If `meta.json.last_collect` is more than 2 days old, run
`python3 scripts/collect_news.py --when 8d` once yourself and say in the report that the daily collector looked stalled.

## Time

Start with `TZ=Asia/Seoul date '+%Y-%m-%dT%H:%M:%S+09:00'` and use that one value as "now". Every date you write
(`checked`, `added`, news `date` is the event date - see below) is a KST calendar date from `TZ=Asia/Seoul date +%F`.
The window for this run starts at `meta.json.last_update_run` (default: 8 days ago).

## Source tiers - the confirmation rule

- **Tier 1 (confirm alone):** company press release / IR page / SEC or DART filing, regulator (FDA, EMA, MFDS, PMDA,
  NMPA, Health Canada, MHRA), ClinicalTrials.gov or another trial registry, the company's own wire release (GlobeNewswire,
  PR Newswire, BusinessWire, Accesswire host the company's own text).
- **Tier 2 (confirm with one Tier 1, or two independent Tier 2):** bylined trade press (Fierce, Endpoints, BioSpace,
  Pharmaceutical Technology, PharmaTimes, NeurologyLive, Korea Biomedical Review, 히트뉴스, 데일리팜, 약업신문, 메디파나뉴스,
  더바이오, 청년의사, 의학신문, 약사공론, 팜뉴스 …). Two outlets rewriting one press release are one source.
- **Tier 3 (discovery only, never cited):** Bluesky and any social post, stock-news aggregators' AI summaries
  (StockTitan "Rhea-AI", quant-hub, secwatch), market-research sites (IndexBox etc.), content farms.

A card update or news item needs **one Tier 1, or two independent Tier 2**, and its `src` must be the best of those
(Tier 1 if you have one). **Social posts are leads only**: tested 2026-10-22, Bluesky caught 8/8 test events the same day
but mostly as bot reposts, and some bot summaries were wrong. Use a social lead to go find the press release; if you
can't find a Tier 1/2 source, drop it.

**Open every source you cite, this run.** Subagents and search snippets have reported dead links as working and invented
plausible URLs. A URL goes into the data only if you fetched it this run and the page states the fact. If WebFetch is
refused (SEC, BusinessWire, StockTitan and fda.gov often refuse scripts), confirm the same fact via search on a page you
*can* open, and cite the page that loads; never cite a URL you could not open. Google News item links are redirects:
search the headline to reach the publisher's URL.

## Run order

Breadth before depth: triage everything once before spending searches on any single item. Budget about 60 web
searches; WebFetch as needed but never retry a host that refused you this run (record it in `meta.json.source_health`).

### 1. Triage the week's leads (no searches yet)

Read the three weekly files. For each `news_cache` item with `status: "new"` and every trial lead, assign one class:

| Class | Meaning | Goes to |
|---|---|---|
| `card` | Development news about a product already on a card (stage, trial start/readout, filing, approval, launch, deal, discontinuation) | step 2 |
| `new_product` | An intranasal drug/vaccine/biologic not on any card, from an identifiable company/sponsor with a code or brand | step 3 |
| `news` | Nasal-relevant event not tied to one card: device/platform deal, regulator guidance, market event | step 4 |
| `dismiss` | Not an intranasal pharma product (consumer chatter, saline/xylitol sprays, nasal polyp injectables, academic use of an old generic, market-size reports, share-price posts, conference attendance notices, executive share purchases) | mark only |

Out of scope everywhere: share-price moves, analyst notes, sales-only items unless they change a stated fact on a card,
OTC saline/decongestant/old-steroid generics unless new formulation or device, and devices with no drug.

Group items describing the same event (a press release, its wire copy, two trade articles and a Bluesky repost are one
event). Work events, not items.

### 2. Update existing cards

For each `card` event, plus every `trial_changes` entry with `notable: true`:

- Verify per the tier rule above (Tier 1 preferred).
- Rewrite `now` as one sentence, ≤ 25 words, starting with the event month (`Oct 2026: …`), the latest material fact
  only. Korean `now.ko` starts `2026년 10월: …`.
- `lastMove` = event month (`YYYY-MM`). `checked` = today's KST date. `src` = `{label, url}` of the cited source.
- `stage` (short label, ≤ 24 characters) and `lane` change only when the source **explicitly states** the new status:
  - `market` = approved/marketed anywhere; `review` = NDA/BLA/MAA filed or resubmitted and pending; `p3`/`p2`/`early`
    = the most advanced trial actually dosing/enrolling, or completed; `early` also covers IND cleared, preclinical;
    `stopped` = company says discontinued/suspended/terminated, or no activity for 3+ years.
  - Never advance on forward-looking language ("plans", "expects", "aims to", "on track to"). A planned Phase 3 is
    still Phase 2; an IND cleared but not dosing is `early` with stage `IND cleared`.
  - Combined phases (Ph1/2, Ph2/3) sit in the lower lane until the higher part is confirmed active.
  - Demotion to `stopped` needs the same confirmation as an advance.
- New trials for a card's product (from `trial_leads.relatedCards`, confirmed to be the same product) are added to its
  `trials` list using the lead's facts, pivotal/most recent first, at most 3 shown.
- Append to the card's `history` list (create it if missing): `{"date": "<KST date>", "change": "<one line: what changed, old -> new>", "src": "<url>"}`.
- A pure registry refresh (only `updated`/`n`/`phase` moved) needs no card text change.

**Rotation check (catches what feeds miss).** Then take the 25 cards with the oldest `checked` (missing = oldest),
starting after `meta.json.rotation_cursor`, and run **one** search each on the most distinctive name (code or brand
before company) for news since that card's `checked` date. Update only on a Tier 1/2 finding. Set `checked` on every
card you searched even if nothing changed, and store the last card id in `rotation_cursor`. At ~100 cards every card is
re-checked about every four weeks.

### 3. Add new products (auto-add is authorised, with a strict bar)

The admin decided on 2026-10-22 that new products are added automatically. Add a card only when **all** hold:

1. A **Tier 1** source (company release, regulator, or a trial registry record) you opened this run.
2. The product is **explicitly intranasal** (nasal spray / powder / gel / drops / implant / intranasal vaccine) - not
   inferred from the company's platform.
3. It is a **defined product**: a brand or development code, a named active ingredient (or "undisclosed" stated by the
   company), and an identifiable sponsor.
4. It is **not already on a card** under another name (check codes, brands, molecule + company against every card;
   normalise case, hyphens and spaces: `NS-002` = `NS002`).
5. It is a medicine, vaccine or drug-device product - not a drug-free saline/barrier spray unless regulated as a device
   that competes with a tracked product (as Bentrio and Noseguard do).

Fill the card exactly like existing ones (see the schema below), with `"added": "<KST date>"`, `checked` = today, the
area from the controlled list, `device` = what the source says or `"Nasal spray (device maker unconfirmed)"`, and trials
from ClinicalTrials.gov leads (or `noTrial` text). If a candidate fails any condition, list it in the report under
"Watching" with what is missing - do not add it.

### 4. News items (page 3)

Add one item per verified event from steps 2-4 that a competitor-watcher would want to know: approvals, filings,
CRLs, trial starts and readouts, discontinuations, launches, deals/acquisitions, device/platform deals, regulator
guidance on nasal products. Not every card refresh is news.

`{"date": "YYYY-MM-DD", "region": "KR"|"GL", "type": one of Approval|Filing|Deal|Launch|Trial|Corporate|Device|Regulatory,
"text": {"en", "ko"}, "src": {"label", "url"}}`

- `date` is the **event date as the source states it** (the announcement's dateline), never the run date or a URL ID.
- `region` is `KR` when the company or market is Korean, else `GL`. `type: "Device"` for delivery-system/platform news.
- One sentence, ≤ 30 words, facts only, every number copied exactly. Insert keeping the list sorted newest first.
- Never add a second item for an event already in the list (check by company + event, not just URL).

Mark every cache item you handled: `status: "used"` or `"dismissed"`, plus `"note"` (≤ 12 words: card id / reason).

### 5. Korean copy

Every text field you write gets its Korean (`ko`) in the same edit. Write the English first, check it against the
source, then translate the English (never translate directly from a Korean source - English is the source of truth).
Keep drug, company and device names in English unless a Korean company/brand (대웅제약, 노즈가드); copy every number,
date, dose and code exactly; use 임상 1상/2상/3상, 허가 신청, 승인/허가, 출시, 중단, 식약처. Same facts and hedges as the
English - no more, no less.

### 6. QC (must pass before commit)

1. Tier 0 self-check: for each item you wrote this run, re-read it against the source text you fetched - names,
   numbers, dates, stage.
2. `python3 build.py --as-of <KST date>` - validates the whole file (lanes, areas, bilingual fields, Korean present,
   dates, no duplicate news URLs, sort order, no pipeline wording) and renders `index.html`. A failure is fixed in the
   **data**, never in `build.py`, `template.html`, `scripts/` or `config/`.
3. Link check on what you added: every new `src.url` was opened this run (rule above). `python3 scripts/verify_links.py`
   may be run for a full report; hosts that refuse scripts (sec.gov, businesswire.com, stocktitan.net, fda.gov) are not
   failures, a `SOFT404` is.

### 7. Write the report, update meta, commit to main

- Write `data/weekly/reports/<KST date>.md`: headline sentence; **New products added**; **Card updates** (card, old ->
  new, source); **News added**; **Watching** (failed the bar, with what's missing); **Dismissed** count by reason;
  **Source health** (feeds failing in `feed_health`, hosts refused this run); coverage (cards rotation-checked, leads
  triaged).
- `data/meta.json`: set `last_update_run` (the "now" value), `rotation_cursor`, `source_health`, and
  `last_update_counts` `{cards_updated, cards_added, news_added, leads_triaged, rotation_checked}` - even on a quiet
  run; a missing update is indistinguishable from a failed run.
- Commit only `nasal_data.json`, `index.html`, `data/`. Message like `Weekly update 2026-10-27: 4 card updates, 1 new
  product (LMN-1001), 6 news`. Then publish to main and confirm:

```bash
git fetch origin main && git rebase origin/main
git push origin HEAD:main
git fetch origin main && git branch -r --contains HEAD   # must list origin/main
```

If the commit is not on `main`, say so at the top of the summary: the deployed page will not change.

### 8. Gmail draft (last step, after the push)

Create a Gmail **draft** (never send) to `dwformulation26@gmail.com`, subject `Intranasal Radar weekly - <KST date>:
<headline>`, body = the report's headline, new products, card updates and news (English, then a short Korean summary),
plus a link to the repo commit. If Gmail fails, say so; the commit is what matters.

## Data schema (nasal_data.json)

Card: `id` (kebab-case, unique; Korean products `kr-…`, Japan `jp-…`, China `cn-…`), `lane`, `region` (2-letter HQ/main
market), `area` (one of the `areas[].id` values: CNS, Pain & migraine, Emergency & rescue, Vaccines & infection,
Metabolic & endocrine, ENT & respiratory, Cardiovascular, Other), `company`, `product`, `api`, `indication`, `device`,
`stage`, `now` (all `{en, ko}`), `lastMove` (YYYY-MM), `checked` (YYYY-MM-DD), `trials`
(`[{nct, phase, status, pcd, n, results, updated}]`, ClinicalTrials.gov values), `noTrial` (`{en, ko}` or null),
`src` (`{label, url}`), optional `added`, `history`. Keep product names short (brand or code + molecule), company ≤ 30
characters, stage ≤ 24 characters.

## Hard boundaries

- Never cite a social post or a Tier 3 source; never cite a URL you did not open this run.
- Never advance a lane on plans or expectations; never guess a date, number or stage.
- Never delete a card (move it to `stopped`); never delete a news item unless it is a duplicate you introduced.
- Never edit `template.html`, `build.py`, `scripts/`, `config/`, `.github/`, the Endpoints content (`endpoints` in the
  data) or this skill. If the page seems to need a design or code change, propose it in the report.
- Never send email; draft only.
- Never spawn sub-agents; do the whole run in this session.
