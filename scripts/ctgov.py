"""Small ClinicalTrials.gov API v2 client shared by the weekly scripts (standard library only)."""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://clinicaltrials.gov/api/v2/studies"
KST = timezone(timedelta(hours=9))
PHASE = {"EARLY_PHASE1": "Early Ph1", "PHASE1": "Ph1", "PHASE2": "Ph2", "PHASE3": "Ph3", "PHASE4": "Ph4", "NA": "N/A"}
UA = {"User-Agent": "intranasal-tracker/1.0 (weekly registry sync)"}


def now_kst():
    return datetime.now(KST)


def get_json(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if i == tries - 1:
                raise
        except Exception:
            if i == tries - 1:
                raise
        time.sleep(3 * (i + 1))


def study(nct):
    fields = "protocolSection.identificationModule,protocolSection.statusModule,protocolSection.designModule,hasResults"
    return get_json(f"{API}/{nct}?fields={fields}")


def trial_facts(j):
    p = j["protocolSection"]
    s, dz = p["statusModule"], p.get("designModule", {})
    return {
        "status": s.get("overallStatus"),
        "phase": "/".join(PHASE.get(x, x) for x in dz.get("phases", [])) or None,
        "n": dz.get("enrollmentInfo", {}).get("count"),
        "pcd": s.get("primaryCompletionDateStruct", {}).get("date"),
        "results": bool(j.get("hasResults")),
        "updated": s.get("lastUpdatePostDateStruct", {}).get("date"),
    }


def search(term, since, page_size=100, max_pages=5):
    """All studies matching `term` whose record changed on or after `since` (YYYY-MM-DD)."""
    fields = ",".join([
        "NCTId", "BriefTitle", "OfficialTitle", "OverallStatus", "Phase", "StudyType", "LeadSponsorName", "LeadSponsorClass",
        "InterventionType", "InterventionName", "Condition", "StudyFirstPostDate", "LastUpdatePostDate", "EnrollmentCount",
        "LocationCountry",
    ])
    params = {
        "query.term": term,
        "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{since},MAX]",
        "fields": fields,
        "pageSize": page_size,
    }
    out, token = [], None
    for _ in range(max_pages):
        if token:
            params["pageToken"] = token
        j = get_json(f"{API}?{urllib.parse.urlencode(params)}")
        out += j.get("studies", [])
        token = j.get("nextPageToken")
        if not token:
            break
    return out
