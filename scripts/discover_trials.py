"""Find intranasal studies registered or updated on ClinicalTrials.gov since the last collection.

Writes data/weekly/trial_leads.json: candidate new products (not yet on any card) and updates that look
related to an existing card (same sponsor or same molecule). The weekly routine decides what each lead means.

Usage: python scripts/discover_trials.py [--since YYYY-MM-DD]
"""
import json
import re
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ctgov import now_kst, search  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA, META = ROOT / "nasal_data.json", ROOT / "data" / "meta.json"
OUT = ROOT / "data" / "weekly" / "trial_leads.json"
TERM = ('intranasal OR "nasal spray" OR "nasal powder" OR "nasal gel" OR "nose-to-brain" OR "nasal vaccine" '
        'OR "intranasally" OR "nasal administration" OR "nasal insert" OR "sinus implant"')
PRODUCT_TYPES = {"DRUG", "BIOLOGICAL", "COMBINATION_PRODUCT", "GENETIC"}
STOP = {"pharma", "pharmaceutical", "pharmaceuticals", "therapeutics", "inc", "ltd", "co", "corp", "university", "hospital",
        "biotech", "bio", "the", "and", "of", "medical", "center", "group", "holdings", "plc", "ag", "sa", "gmbh", "llc", "nasal",
        "spray", "powder", "intranasal", "vaccine", "korea", "japan", "china"}


def words(s):
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-]{2,}", (s or "").lower()) if w not in STOP}


NASAL_ADMIN = re.compile(r"intranasal|nasal (spray|powder|gel|vaccine|administration|insert|drops?)|nose-to-brain|intra-nasal|"
                        r"nasally|live attenuated influenza|LAIV|sinus implant", re.I)
BACKGROUND = re.compile(r"mometasone|fluticasone|budesonide|beclomethasone|triamcinolone|saline|placebo", re.I)
CODE = re.compile(r"[A-Z]{2,6}-?\d{2,6}")


def first_word(s):
    w = [x for x in re.findall(r"[a-z0-9][a-z0-9\-]{3,}", (s or "").lower()) if x not in STOP]
    return w[0] if w else None


def card_index(cards):
    """Distinctive identifiers per card: sponsor's first distinctive word, product brand/code, molecule."""
    idx = []
    for c in cards:
        sponsor = first_word(c["company"]["en"])
        drug = {first_word(c["product"]["en"]), first_word(c["api"]["en"])} - {None}
        idx.append((c["id"], sponsor, drug))
    return idx


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    if "--since" in sys.argv:
        since = sys.argv[sys.argv.index("--since") + 1]
    else:  # overlap one day with the previous collection so nothing falls between runs
        last = (meta.get("last_collect") or "")[:10]
        since = last or (now_kst() - timedelta(days=10)).date().isoformat()
        if last:
            since = (now_kst().fromisoformat(meta["last_collect"]) - timedelta(days=1)).date().isoformat()
    tracked = {t["nct"] for c in d["cards"] for t in c["trials"]}
    idx = card_index(d["cards"])
    leads = []
    for s in search(TERM, since):
        p = s["protocolSection"]
        ident, st, dz = p["identificationModule"], p["statusModule"], p.get("designModule", {})
        nct = ident["nctId"]
        if nct in tracked or dz.get("studyType") != "INTERVENTIONAL":
            continue
        ints = p.get("armsInterventionsModule", {}).get("interventions", [])
        types = {i.get("type") for i in ints}
        sponsor = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
        # background steroid/saline sprays in e.g. nasal-polyp antibody trials are not the product under study
        study_ints = [i for i in ints if not BACKGROUND.search(i.get("name", ""))]
        title_text = " ".join([ident.get("briefTitle", ""), ident.get("officialTitle", "")] + [i.get("name", "") for i in study_ints])
        if not NASAL_ADMIN.search(title_text):
            continue  # matched on a condition word only (e.g. nasal polyps), not a nasal product
        if not types & PRODUCT_TYPES:
            continue  # device-only / behavioural studies
        industry = sponsor.get("class") in ("INDUSTRY", "NIH", "FED")
        if not industry and not CODE.search(title_text):
            continue  # academic use of an old generic (e.g. nasal dexmedetomidine for sedation) is noise
        sw = words(sponsor.get("name"))
        iw = words(" ".join(i.get("name", "") for i in ints) + " " + ident.get("briefTitle", ""))
        related = [cid for cid, sp, drug in idx if (sp and sp in sw) or (drug & iw)]
        first = st.get("studyFirstPostDateStruct", {}).get("date", "")
        leads.append({
            "nct": nct,
            "title": ident.get("briefTitle"),
            "sponsor": sponsor.get("name"),
            "sponsorClass": sponsor.get("class"),
            "phase": "/".join(dz.get("phases", [])) or None,
            "status": st.get("overallStatus"),
            "enrollment": dz.get("enrollmentInfo", {}).get("count"),
            "interventions": [f"{i.get('type')}: {i.get('name')}" for i in ints][:6],
            "conditions": p.get("conditionsModule", {}).get("conditions", [])[:5],
            "countries": sorted({loc.get("country") for loc in p.get("contactsLocationsModule", {}).get("locations", []) if loc.get("country")})[:8],
            "firstPosted": first,
            "lastUpdate": st.get("lastUpdatePostDateStruct", {}).get("date"),
            "newRegistration": first >= since,
            "relatedCards": related[:5],
            "url": f"https://clinicaltrials.gov/study/{nct}",
        })
    # Cards without any registry record (often products the weekly routine just added - it cannot reach
    # ClinicalTrials.gov from the cloud): look the product up by its code/brand, any date.
    for c in d["cards"]:
        if c["trials"] or not c.get("added"):
            continue  # only products the routine added; older trial-less cards were checked by hand
        code = CODE.search(c["product"]["en"])
        q = code.group(0) if code else re.split(r"[\s(/,]", c["product"]["en"])[0]
        if len(q) < 5 or q.lower() in STOP:
            continue
        try:  # intervention-name field only: a free-text search matches any study that mentions the word
            hits = search(f'AREA[InterventionName]"{q}"', "2000-01-01", page_size=10, max_pages=1)
        except Exception:
            continue
        for s in hits:
            p = s["protocolSection"]
            ident, st, dz = p["identificationModule"], p["statusModule"], p.get("designModule", {})
            ints = p.get("armsInterventionsModule", {}).get("interventions", [])
            text = " ".join([ident.get("briefTitle", ""), ident.get("officialTitle", "")] + [i.get("name", "") for i in ints])
            if ident["nctId"] in tracked or dz.get("studyType") != "INTERVENTIONAL" or not NASAL_ADMIN.search(text):
                continue  # a generic molecule name (e.g. epinephrine) matches injectable studies too
            leads.append({
                "nct": ident["nctId"], "title": ident.get("briefTitle"),
                "sponsor": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
                "sponsorClass": p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class"),
                "phase": "/".join(dz.get("phases", [])) or None, "status": st.get("overallStatus"),
                "enrollment": dz.get("enrollmentInfo", {}).get("count"), "interventions": [], "conditions": [],
                "countries": [], "firstPosted": st.get("studyFirstPostDateStruct", {}).get("date", ""),
                "lastUpdate": st.get("lastUpdatePostDateStruct", {}).get("date"), "newRegistration": False,
                "relatedCards": [c["id"]], "cardLookup": f'card has no trials; registry search for "{q}"',
                "url": f"https://clinicaltrials.gov/study/{ident['nctId']}",
            })
    # industry-sponsored product studies first, then newest
    leads.sort(key=lambda x: (x["sponsorClass"] != "INDUSTRY", not x["relatedCards"], x["lastUpdate"] or ""), reverse=False)
    out = {"generated": now_kst().isoformat(timespec="seconds"), "since": since, "term": TERM, "leads": leads}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ind = sum(x["sponsorClass"] == "INDUSTRY" for x in leads)
    print(f"since {since}: {len(leads)} untracked intranasal product studies ({ind} industry, "
          f"{sum(bool(x['relatedCards']) for x in leads)} related to existing cards)")


if __name__ == "__main__":
    main()
