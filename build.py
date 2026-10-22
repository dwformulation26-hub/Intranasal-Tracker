"""Validate nasal_data.json and render index.html from template.html.

Usage:
  python build.py                  validate + render
  python build.py --as-of 2026-10-27   also set the "Data as of" date first
  python build.py --check          validate only (exit 1 on any problem)

The weekly routine must leave this passing before it commits. A failure is fixed in the data, never here.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "nasal_data.json"
LANES = {"market", "review", "p3", "p2", "early", "stopped"}
NEWS_TYPES = {"Approval", "Filing", "Deal", "Launch", "Trial", "Corporate", "Device", "Regulatory"}
TRIAL_STATUS = {"COMPLETED", "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION",
                "TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN"}
CARD_TEXT = ("company", "product", "api", "indication", "device", "stage", "now")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MONTH = re.compile(r"\d{4}-\d{2}")
HANGUL = re.compile(r"[가-힣]")
# words that describe the pipeline, not the world - never shown on the page
NARRATION = re.compile(r"\b(this run|weekly run|routine|search result|snippet|fetched|EGRESS|UNVERIFIED)\b", re.I)


def bilingual(v):
    return isinstance(v, dict) and isinstance(v.get("en"), str) and v["en"].strip() and isinstance(v.get("ko"), str) and v["ko"].strip()


def validate(d):
    p = []
    areas = {a["id"] for a in d["areas"]}
    ids = set()
    for c in d["cards"]:
        cid = c.get("id", "?")
        if cid in ids:
            p.append(f"card {cid}: duplicate id")
        ids.add(cid)
        if c.get("lane") not in LANES:
            p.append(f"card {cid}: lane {c.get('lane')!r} not in {sorted(LANES)}")
        if c.get("area") not in areas:
            p.append(f"card {cid}: area {c.get('area')!r} not in areas list")
        if not re.fullmatch(r"[A-Z]{2}", c.get("region", "")):
            p.append(f"card {cid}: region must be a 2-letter code")
        for k in CARD_TEXT:
            if not bilingual(c.get(k)):
                p.append(f"card {cid}: {k} needs non-empty en and ko")
            elif NARRATION.search(c[k]["en"]):
                p.append(f"card {cid}: {k} contains pipeline narration")
        for k in ("now", "indication"):
            if bilingual(c.get(k)) and not HANGUL.search(c[k]["ko"]):
                p.append(f"card {cid}: {k}.ko has no Korean text")
        # cards must stay readable at a glance (the page overflowed before labels were capped)
        if bilingual(c.get("stage")) and len(c["stage"]["en"]) > 28:
            p.append(f"card {cid}: stage.en is {len(c['stage']['en'])} chars (max 28) - put detail in now")
        if bilingual(c.get("now")) and len(c["now"]["en"].split()) > 32:
            p.append(f"card {cid}: now.en is {len(c['now']['en'].split())} words (max 32) - keep the latest fact only")
        if bilingual(c.get("product")) and len(c["product"]["en"]) > 40:
            p.append(f"card {cid}: product.en longer than 40 chars")
        if not MONTH.fullmatch(c.get("lastMove", "")):
            p.append(f"card {cid}: lastMove must be YYYY-MM")
        if c.get("checked") is not None and not DATE.fullmatch(c["checked"]):
            p.append(f"card {cid}: checked must be YYYY-MM-DD")
        src = c.get("src") or {}
        if not (src.get("url", "").startswith("http") and src.get("label")):
            p.append(f"card {cid}: src needs label and http(s) url")
        for t in c.get("trials", []):
            if not re.fullmatch(r"NCT\d{8}", t.get("nct", "")):
                p.append(f"card {cid}: bad NCT {t.get('nct')}")
            if t.get("status") not in TRIAL_STATUS:
                p.append(f"card {cid}: {t.get('nct')} status {t.get('status')!r}")
        if not c.get("trials") and not bilingual(c.get("noTrial")):
            p.append(f"card {cid}: no trials and no noTrial text")
    seen = set()
    for n in d["news"]:
        key = n.get("date", "?") + " " + (n.get("text", {}).get("en", "")[:40])
        if not DATE.fullmatch(n.get("date", "")):
            p.append(f"news {key}: date must be YYYY-MM-DD")
        if n.get("region") not in ("KR", "GL"):
            p.append(f"news {key}: region must be KR or GL")
        if n.get("type") not in NEWS_TYPES:
            p.append(f"news {key}: type {n.get('type')!r}")
        if not bilingual(n.get("text")) or not HANGUL.search(n["text"].get("ko", "")):
            p.append(f"news {key}: text needs en and Korean ko")
        elif NARRATION.search(n["text"]["en"]):
            p.append(f"news {key}: text contains pipeline narration")
        src = n.get("src") or {}
        if not src.get("url", "").startswith("http"):
            p.append(f"news {key}: src url missing")
        url = src.get("url")
        if url in seen:
            p.append(f"news {key}: duplicate source url (same story twice?)")
        seen.add(url)
    dates = [n["date"] for n in d["news"]]
    if dates != sorted(dates, reverse=True):
        p.append("news must be sorted newest first")
    if not DATE.fullmatch(d.get("asOf", "")):
        p.append("asOf must be YYYY-MM-DD")
    return p


def render(d):
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("/*DATA*/null", blob)
    (HERE / "index.html").write_text(html, encoding="utf-8")
    print(f"wrote index.html ({len(html) // 1024} KB): {len(d['cards'])} cards, {len(d['news'])} news, as of {d['asOf']}")


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    if "--as-of" in sys.argv:
        d["asOf"] = sys.argv[sys.argv.index("--as-of") + 1]
        DATA.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    problems = validate(d)
    for x in problems:
        print("PROBLEM:", x)
    if problems:
        print(f"{len(problems)} problem(s) - fix the data, then build again")
        sys.exit(1)
    print("validation passed")
    if "--check" not in sys.argv:
        render(d)


if __name__ == "__main__":
    main()
