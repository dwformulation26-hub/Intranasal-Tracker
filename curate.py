"""Hand curation applied after build.py merges the research slices: drop cross-slice duplicates, fix areas."""
import json

DROP_CARDS = {"spydia-jp", "jp-snbl-atzumi", "cn-primegene-pg011"}
AREA_FIX = {"etripamil-cardamyst": "Cardiovascular", "jp-spydia": "CNS"}
# duplicate news: (date, start of English text) of the copy to drop
DROP_NEWS = [
    ("2026-05-11", "SNBL decides"), ("2025-12-17", "PALISADE-3 Phase 3"), ("2025-12-12", "FDA approves Cardamyst"),
    ("2025-10-16", "Viatris acquired Aculys"), ("2025-09-29", "Indivior stops"), ("2025-09-24", "Acadia's intranasal carbetocin failed"),
    ("2025-05-21", "Paratek completes"), ("2025-04-30", "FDA approved Satsuma"), ("2025-04-30", "FDA approved SNBL"),
    ("2025-04-16", "FDA expands Valtoco"),
]

d = json.load(open("nasal_data.json", encoding="utf-8"))
d["cards"] = [c for c in d["cards"] if c["id"] not in DROP_CARDS]
for c in d["cards"]:
    c["area"] = AREA_FIX.get(c["id"], c["area"])
    c.pop("_slice", None)
d["news"] = [n for n in d["news"] if not any(n["date"] == dt and n["text"]["en"].startswith(p) for dt, p in DROP_NEWS)]
json.dump(d, open("nasal_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(d["cards"]), "cards,", len(d["news"]), "news")
