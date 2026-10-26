# Where the weekly update gets its information

Tested from Korea on 2026-10-22. The full per-feed list (URLs, user agents, tiers) lives in `config/feeds.json`;
keywords in `config/keywords.json`.

## Why collection is daily but the update is weekly

Most usable feeds only hold 1-3 days of items (PR Newswire ~20 items/day, BusinessWire, GlobeNewswire industry feeds,
Endpoints, BioSpace, FDA "What's New", and every Korean outlet at ~50 items/day). A once-a-week pull would miss most of
the week, so a free GitHub Actions job polls every day at 03:00 KST and keeps a 21-day cache. The Claude routine reads a
full week of it on Monday.

## Sources (by role)

| Role | Sources | Notes |
|---|---|---|
| Trial registry (Tier 1) | ClinicalTrials.gov API v2 | Every tracked NCT re-synced weekly; new intranasal product studies discovered by text search. About 1 in 3 raw matches is a real product signal; the filter keeps industry/NIH sponsors or coded products and drops nasal-polyp antibody trials and academic use of old generics. |
| Regulators (Tier 1) | FDA press releases, FDA What's New (Drugs, Biologics), FDA recalls, openFDA drugsfda (route NASAL), EMA news + what's new, MFDS 보도자료/공지, PMDA, DART 오늘의 공시 | FDA feeds answer only feed-reader user agents. NMPA blocks scripts (412) - China is covered through Google News. |
| Company wires (Tier 1) | GlobeNewswire keyword "intranasal" + Pharma/Biotech industry feeds, PR Newswire (pharma, biotech, FDA approval), BusinessWire home | www.globenewswire.com refuses scripts; the rss.globenewswire.com feeds work. |
| Search aggregation (Tier 2 leads) | Google News RSS: EN (intranasal, nasal spray + pharma terms, nasal powder, nasal vaccine, nose-to-brain, wires, trade press, China approvals), KO (비강 + 제약/임상/허가/개발; 비강 투여/스프레이/분무, 노즈가드), JA (点鼻), ZH (鼻喷) | Best single channel: ~2/3 of "intranasal" items are real product news. Korean yield is low (~1 in 4). Links are Google redirects; the routine searches the headline to reach the publisher. |
| Trade press (Tier 2) | Endpoints, BioSpace, NeurologyLive, ONdrugDelivery, PharmaTimes, PharmTech, Pharmaceutical Technology, Drug Delivery Business News, AJMC, Korea Biomedical Review | Fierce, Accesswire, Healio, RAPS block or retired their feeds. |
| Korean press (Tier 2) | 히트뉴스, 메디파나뉴스, 더바이오, 팜뉴스, 청년의사, 의학신문, 약사공론, 뉴스더보이스, 헬스코리아뉴스, 연합뉴스 건강, 한국경제 | 데일리팜, 약업신문, 바이오스펙테이터, 메디게이트 have no RSS - reached through Google News KO. Naver News API and OpenDART need free keys (not set up). |
| Social (Tier 3, leads only) | Bluesky search API | See below. |

## Social media: availability, consistency, accuracy

Tested against 8 events verified from official sources (Rextovy OTC, PALISADE-3/-4, etripamil China approval,
Lilly-AtaiBeckley close, Nasus NS002 IND, Harrow-Tyrvaya, EURneffy 1 mg).

| Platform | Unattended access | Found | Timeliness | Accuracy / noise | Verdict |
|---|---|---|---|---|---|
| **Bluesky** | Yes - free search API, no login, date filters | 8/8 | 7 same day, 1 a day late, none early | Mostly bots reposting the release; some bot summaries wrong (IND called a "Regulatory Designation", stock drop given as -82.7% and -77%); no post carried the trial numbers | **Early-warning lead source only** (in use) |
| Reddit | RSS only, ~1 call per 45 s | 7/8 | Same day | Duplicates Bluesky; pump/rumour posts after trial failures | Low value - not used |
| X / Twitter | No (login wall, no index, rate-limited embeds) | 0/8 testable | - | - | Not usable |
| LinkedIn | No (login wall; scraping against terms) | - | Undated "1mo" posts | Occasionally early (Nasus NS003 post) | Not usable unattended |
| Naver blog/cafe | Web scrape only; API needs key | 0/5 global events | - | Name clashes, consumer/clinic ads | Not used |
| StockTwits, Telegram | Blocked by the office network filter | untested | - | Mostly price sentiment (secondhand) | Retest off-network if wanted |
| Mastodon, Threads, KakaoTalk | Login/token required or no search | 0 | - | - | Not usable |

**Conclusion:** social media is available only through Bluesky, it is consistent (every test event appeared) and fast
(same day), but it is not accurate enough to cite - it never broke news before the official source, and its summaries
contained errors. The tracker therefore uses it only to raise leads, and every lead must be confirmed by a company,
regulator, registry or bylined trade-press source before it reaches the page.
