"""Refresh every tracked trial on the product cards from ClinicalTrials.gov (deterministic, no judgment).

Writes the API values into nasal_data.json and lists what changed in data/weekly/trial_changes.json,
so the weekly routine can turn meaningful changes (status, results posted) into card updates.

Usage: python scripts/sync_trials.py [--dry-run]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ctgov import now_kst, study, trial_facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "nasal_data.json"
OUT = ROOT / "data" / "weekly" / "trial_changes.json"
FIELDS = ("status", "phase", "n", "pcd", "results", "updated")
# changes worth a human-readable card update; the rest are bookkeeping
NOTABLE = {"status", "results", "pcd"}


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    changes, errors, cache = [], [], {}
    for c in d["cards"]:
        for t in c["trials"]:
            nct = t["nct"]
            if nct not in cache:
                try:
                    j = study(nct)
                    cache[nct] = trial_facts(j) if j else None
                except Exception as e:  # network trouble is reported, never fatal
                    cache[nct] = "ERROR"
                    errors.append({"nct": nct, "error": str(e)[:200]})
            a = cache[nct]
            if a in (None, "ERROR"):
                if a is None:
                    errors.append({"nct": nct, "card": c["id"], "error": "not found on ClinicalTrials.gov"})
                continue
            for k in FIELDS:
                if str(t.get(k)) != str(a[k]):
                    changes.append({"card": c["id"], "product": c["product"]["en"], "nct": nct, "field": k,
                                    "old": t.get(k), "new": a[k], "notable": k in NOTABLE})
                    t[k] = a[k]
    report = {"generated": now_kst().isoformat(timespec="seconds"), "trials_checked": len(cache),
              "changes": changes, "errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if "--dry-run" not in sys.argv:
        DATA.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    notable = sum(x["notable"] for x in changes)
    print(f"{len(cache)} trials checked: {len(changes)} field changes ({notable} notable), {len(errors)} errors")


if __name__ == "__main__":
    main()
