"""Re-check every NCT in nasal_data.json against the ClinicalTrials.gov v2 API.

Writes verify_trials_report.json; with --fix, overwrites trial fields with the API values.
"""
import json
import sys
import time
import urllib.request

API = "https://clinicaltrials.gov/api/v2/studies/{}?fields=protocolSection.identificationModule,protocolSection.statusModule,protocolSection.designModule,protocolSection.sponsorCollaboratorsModule,hasResults"
PH = {"EARLY_PHASE1": "Early Ph1", "PHASE1": "Ph1", "PHASE2": "Ph2", "PHASE3": "Ph3", "PHASE4": "Ph4", "NA": "N/A"}


def fetch(nct):
    for _ in range(3):
        try:
            with urllib.request.urlopen(API.format(nct), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            time.sleep(2)
    return "ERROR"


def facts(j):
    p = j["protocolSection"]
    s, dz = p["statusModule"], p.get("designModule", {})
    return {
        "title": p["identificationModule"].get("briefTitle"),
        "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
        "status": s.get("overallStatus"),
        "phase": "/".join(PH.get(x, x) for x in dz.get("phases", [])) or None,
        "n": dz.get("enrollmentInfo", {}).get("count"),
        "pcd": s.get("primaryCompletionDateStruct", {}).get("date"),
        "results": bool(j.get("hasResults")),
        "updated": s.get("lastUpdatePostDateStruct", {}).get("date"),
    }


d = json.load(open("nasal_data.json", encoding="utf-8"))
ncts = {t["nct"] for c in d["cards"] for t in c["trials"]}
ncts |= {n for cat in d["endpoints"]["categories"] for p in cat["products"] for n in p.get("ncts", [])}
api = {}
for n in sorted(ncts):
    j = fetch(n)
    api[n] = j if j in (None, "ERROR") else facts(j)

report = {"missing": [], "error": [], "diffs": [], "api": api}
for c in d["cards"]:
    for t in c["trials"]:
        a = api[t["nct"]]
        if a is None:
            report["missing"].append([c["id"], t["nct"]])
            continue
        if a == "ERROR":
            report["error"].append([c["id"], t["nct"]])
            continue
        diff = {k: [t.get(k), a[k]] for k in ("status", "n", "pcd", "results", "updated") if str(t.get(k)) != str(a[k])}
        if diff:
            report["diffs"].append([c["id"], t["nct"], diff])
        if "--fix" in sys.argv:
            t.update({k: a[k] for k in ("status", "phase", "n", "pcd", "results", "updated")})
for cat in d["endpoints"]["categories"]:
    for p in cat["products"]:
        for n in p.get("ncts", []):
            if api[n] in (None, "ERROR"):
                report["missing"].append(["endpoints:" + p["product"], n])

json.dump(report, open("verify_trials_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if "--fix" in sys.argv:
    json.dump(d, open("nasal_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(ncts)} NCTs checked; missing {len(report['missing'])}, errors {len(report['error'])}, cards with diffs {len(report['diffs'])}")
for m in report["missing"] + report["error"]:
    print("  !!", m)
for cid, nct, diff in report["diffs"]:
    print(f"  {cid} {nct}: " + "; ".join(f"{k} {v[0]} -> {v[1]}" for k, v in diff.items()))
