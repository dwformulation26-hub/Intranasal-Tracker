"""Merge research JSON files into nasal_data.json and render index.html from template.html.

Usage: python build.py <research_dir>
Edit nasal_data.json by hand afterwards and re-run with --from-data to re-render without re-merging.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
AS_OF = "2026-10-21"
SLICES = ["cns", "pain_emergency", "vaccines", "metabolic_ent", "asia"]
LANES = [
    {"id": "market", "name": {"en": "On market", "ko": "시판"}},
    {"id": "review", "name": {"en": "Regulatory review", "ko": "허가 심사"}},
    {"id": "p3", "name": {"en": "Phase 3", "ko": "임상 3상"}},
    {"id": "p2", "name": {"en": "Phase 2", "ko": "임상 2상"}},
    {"id": "early", "name": {"en": "Phase 1 / preclinical", "ko": "임상 1상 / 전임상"}},
    {"id": "stopped", "name": {"en": "Stopped or dormant", "ko": "중단·휴면"}},
]
AREAS = [
    {"id": "CNS", "en": "CNS & psychiatry", "ko": "중추신경·정신"},
    {"id": "Pain & migraine", "en": "Pain & migraine", "ko": "통증·편두통"},
    {"id": "Emergency & rescue", "en": "Emergency & rescue", "ko": "응급·구조"},
    {"id": "Vaccines & infection", "en": "Vaccines & infection", "ko": "백신·감염"},
    {"id": "Metabolic & endocrine", "en": "Metabolic & endocrine", "ko": "대사·내분비"},
    {"id": "ENT & respiratory", "en": "ENT & respiratory", "ko": "이비인후·호흡기"},
    {"id": "Cardiovascular", "en": "Cardiovascular", "ko": "심혈관"},
    {"id": "Other", "en": "Other", "ko": "기타"},
]
BI = ["company", "product", "api", "indication", "device", "stage", "now"]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def check_card(c, problems):
    cid = c.get("id", "?")
    if c.get("lane") not in {l["id"] for l in LANES}:
        problems.append(f"{cid}: bad lane {c.get('lane')}")
    if c.get("area") not in {a["id"] for a in AREAS}:
        problems.append(f"{cid}: bad area {c.get('area')}")
    for k in BI:
        v = c.get(k)
        if not isinstance(v, dict) or not v.get("en"):
            problems.append(f"{cid}: missing {k}")
            c[k] = {"en": str(v or "—"), "ko": str(v or "—")} if not isinstance(v, dict) else {"en": v.get("en") or "—", "ko": v.get("ko") or v.get("en") or "—"}
        elif not v.get("ko"):
            v["ko"] = v["en"]
    c.setdefault("trials", [])
    c.setdefault("noTrial", None)
    for t in c["trials"]:
        if not re.fullmatch(r"NCT\d{8}", t.get("nct", "")):
            problems.append(f"{cid}: bad NCT {t.get('nct')}")
    if not c.get("src") or not c["src"].get("url"):
        problems.append(f"{cid}: no source")


def merge(research):
    cards, news, notes = [], [], {}
    seen = {}
    for s in SLICES:
        p = research / f"{s}.json"
        if not p.exists():
            print(f"!! missing slice {s}")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        notes[s] = d.get("notes", "")
        for c in d.get("cards", []):
            key = norm(c.get("product", {}).get("en")) + "|" + c.get("region", "")
            if key in seen:
                print(f"   dup card {c.get('id')} ({s}) ~ {seen[key]}")
                continue
            seen[key] = f"{c.get('id')} ({s})"
            c["_slice"] = s
            cards.append(c)
        news += d.get("news", [])
    en = research / "endpoints_news.json"
    endpoints = {}
    if en.exists():
        e = json.loads(en.read_text(encoding="utf-8"))
        news += e.get("news", [])
        notes["endpoints_news"] = e.get("notes", "")
        endpoints = {k: e.get(k, []) for k in ("categories", "guidance", "localSafety", "todo")}
    # de-duplicate news by date + leading words
    out, keys = [], set()
    for n in sorted(news, key=lambda n: n.get("date", ""), reverse=True):
        k = n.get("date", "") + norm(n.get("text", {}).get("en", ""))[:40]
        if k in keys:
            continue
        keys.add(k)
        out.append(n)
    return cards, out, endpoints, notes


def render(data):
    tpl = (HERE / "template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("/*DATA*/null", blob)
    for out in ("index.html", "intranasal_tracker.html"):
        (HERE / out).write_text(html, encoding="utf-8")
    print(f"wrote index.html ({len(html)//1024} KB): {len(data['cards'])} cards, {len(data['news'])} news")


def main():
    data_path = HERE / "nasal_data.json"
    if "--from-data" in sys.argv:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    else:
        cards, news, endpoints, notes = merge(Path(sys.argv[1]))
        endpoints.update(json.loads((HERE / "endpoints_frame.json").read_text(encoding="utf-8")))
        data = {"asOf": AS_OF, "lanes": LANES, "areas": AREAS, "cards": cards, "news": news, "endpoints": endpoints}
        (HERE / "research_notes.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")
    problems = []
    for c in data["cards"]:
        check_card(c, problems)
    for n in data["news"]:
        if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", n.get("date", "")):
            problems.append(f"news bad date {n.get('date')}")
    print("\n".join(problems) or "no problems")
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    render(data)


if __name__ == "__main__":
    main()
