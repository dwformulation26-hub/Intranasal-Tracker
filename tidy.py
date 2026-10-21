"""Shorten card labels so cards stay neat: stage <= ~24 chars, product/company names short. Detail stays in 'now'."""
import json
import re

STAGE = {
    "spravato": ("FDA approved", "FDA 승인"), "valtoco": ("FDA approved", "FDA 승인"), "tyrvaya": ("FDA approved", "FDA 승인"),
    "bpl-003": ("Phase 3", "임상 3상"), "fasedienol": ("Phase 3 (failed)", "3상 (실패)"), "itruvone": ("Phase 2a done", "2a상 완료"),
    "cenegermin-naion": ("Phase 3", "임상 3상"), "sls-002": ("Phase 2 · stalled", "2상 · 정체"), "inp105": ("Stopped", "중단"),
    "acp-101": ("Stopped after Phase 3", "3상 후 중단"), "nrl-4-olanzapine": ("Phase 1", "임상 1상"), "tr-012001": ("Phase 2", "임상 2상"),
    "zavzpret": ("FDA approved", "FDA 승인"), "atzumi": ("FDA approved", "FDA 승인"), "cessatech-ct001": ("US hospital supply", "미국 병원 공급"),
    "tnx1900-pain": ("Phase 2", "임상 2상"), "rextovy": ("FDA approved · OTC", "FDA 승인 · OTC"), "kloxxado": ("FDA approved", "FDA 승인"),
    "opvee": ("FDA approved · not promoted", "FDA 승인 · 판촉 중단"), "orexo-izipry": ("NDA resubmitted", "NDA 재제출"),
    "neffy": ("Approved in 7 markets", "7개국 승인"), "bryn-utuly": ("Pivotal PK stage", "허가용 PK 임상"), "orexo-ox640": ("IND accepted", "IND 승인"),
    "baqsimi": ("FDA/EU approved", "FDA·EU 승인"), "flumist-home": ("FDA approved", "FDA 승인"), "incovacc": ("India emergency use", "인도 긴급사용"),
    "pneucolin": ("China emergency use", "중국 긴급사용"), "sputnik-nasal": ("Registered in Russia", "러시아 등록"), "coviliv": ("Stalled", "정체"),
    "bpze1": ("Phase 3 contracted", "3상 계약"), "deltaflu": ("Phase 2 (challenge)", "2상 (인체도전)"), "nons-enovid": ("Marketed ex-US", "미국 외 시판"),
    "azelastine-covid": ("Phase 2 positive", "2상 긍정적"), "neumifil": ("Phase 2 done", "2상 완료"), "xf-73-nasal": ("Phase 2b done", "2b상 완료"),
    "nasodine": ("Marketed (non-drug)", "시판 (비의약품)"), "etripamil-cardamyst": ("FDA & China approved", "FDA·중국 승인"),
    "xhance-eds": ("FDA approved", "FDA 승인"), "ryaltris": ("Approved in 6+ markets", "6개국 이상 승인"), "lyra-lyr210": ("Suspended after Phase 3", "3상 후 중단"),
    "natesto": ("FDA approved", "FDA 승인"), "aptar-glp1-nasal": ("Preclinical", "전임상"), "mgh-oxytocin-obesity": ("Phase 2 (academic)", "2상 (연구자 주도)"),
    "cyrano-cyr064": ("Phase 2 done", "2상 완료"), "bentrio-altamira": ("Marketed (device)", "시판 (의료기기)"), "polyrizon-pl14": ("Device study", "의료기기 임상"),
    "tor582-hht": ("Phase 1", "임상 1상"), "kr-spravato": ("MFDS approved", "식약처 허가"), "kr-flumist": ("MFDS approved", "식약처 허가"),
    "kr-ryaltris": ("MFDS approved", "식약처 허가"), "kr-daewoong-nasal-platform": ("Research", "연구 단계"), "kr-daewoong-noseguard": ("Marketed (device)", "시판 (의료기기)"),
    "kr-koreabnc-jinmedicine": ("Preclinical", "비임상"), "kr-skbio-nasal-binder": ("Preclinical", "비임상"), "jp-spydia": ("Launched", "출시"),
    "jp-neffy-alfresa": ("PMDA approved", "PMDA 허가"), "cn-bcht-laiv": ("Marketed", "시판"), "cn-neffy-pediatrix": ("Marketed", "시판"),
    "cn-huahui-hh120": ("Phase 3 done", "3상 완료"), "trudhesa": ("FDA approved", "FDA 승인"), "pecfent": ("EU approved", "EU 승인"),
    "purity-dexmed": ("NMPA approved", "NMPA 승인"), "kovanaze": ("FDA approved", "FDA 승인"), "bcht-nasal-laiv": ("NMPA approved", "NMPA 승인"),
    "tnx-2900": ("Phase 2 planned", "2상 예정"), "rivive": ("FDA approved · OTC", "FDA 승인 · OTC"), "blb201": ("Phase 1/2a", "임상 1/2a상"),
    "rvx-scpd9": ("Phase 1", "임상 1상"),
}
PRODUCT = {
    "inp105": ("INP105 / INP107", "INP105 / INP107"), "intranasal-insulin-wfu": ("Intranasal insulin", "비강 인슐린"),
    "protollin-ad": ("Nasal Protollin", "비강 Protollin"), "nrl-4-olanzapine": ("NRL-4 (olanzapine)", "NRL-4 (올란자핀)"),
    "cessatech-ct001": ("CT001 (KemSu)", "CT001 (KemSu)"), "pecfent": ("PecFent / Instanyl", "PecFent / Instanyl"),
    "purity-dexmed": ("Temeiding (dexmedetomidine)", "특미정 (덱스메데토미딘)"), "kovanaze": ("Kovanaze", "Kovanaze"), "kloxxado": ("Kloxxado", "Kloxxado"),
    "trudhesa": ("Trudhesa (DHE)", "Trudhesa (DHE)"), "atzumi": ("Atzumi (DHE powder)", "Atzumi (DHE 분말)"), "rextovy": ("Rextovy", "Rextovy"),
    "opvee": ("Opvee (nalmefene)", "Opvee (날메펜)"), "baqsimi": ("Baqsimi (glucagon)", "Baqsimi (글루카곤)"),
    "orexo-izipry": ("IZIPRY (OX124)", "IZIPRY (OX124)"), "neffy": ("neffy / EURneffy", "neffy / EURneffy"), "bryn-utuly": ("Utuly (BRYN-NDS1C)", "Utuly (BRYN-NDS1C)"),
    "orexo-ox640": ("OX640 (epinephrine powder)", "OX640 (에피네프린 분말)"), "nasus-fmxin002": ("FMXIN002 (NS002)", "FMXIN002 (NS002)"),
    "bcht-nasal-laiv": ("Liquid nasal flu LAIV", "액상 비강 독감 생백신"), "cn-bcht-laiv": ("Lyophilized nasal flu LAIV", "동결건조 비강 독감 생백신"),
    "sputnik-nasal": ("Sputnik V nasal", "Sputnik V 비강형"), "nons-enovid": ("Enovid / VirX (NONS)", "Enovid / VirX (NONS)"),
    "azelastine-covid": ("Azelastine (antiviral use)", "아젤라스틴 (항바이러스 용도)"), "xf-73-nasal": ("XF-73 Nasal", "XF-73 Nasal"),
    "nasodine": ("Nasodine", "Nasodine"), "etripamil-cardamyst": ("CARDAMYST (etripamil)", "CARDAMYST (에트리파밀)"),
    "xhance-eds": ("XHANCE (fluticasone)", "XHANCE (플루티카손)"), "ryaltris": ("RYALTRIS", "RYALTRIS"), "lyra-lyr210": ("LYR-210 / LYR-220", "LYR-210 / LYR-220"),
    "natesto": ("NATESTO (testosterone)", "NATESTO (테스토스테론)"), "wl1006-semaglutide-nasal": ("WL1006 (semaglutide)", "WL1006 (세마글루타이드)"),
    "orexo-ox472": ("OX472 (semaglutide powder)", "OX472 (세마글루타이드 분말)"), "metp-semaglutide-n2b": ("Nose-to-brain semaglutide", "뇌 표적 비강 세마글루타이드"),
    "aptar-glp1-nasal": ("Nasal GLP-1 (semaglutide)", "비강 GLP-1 (세마글루타이드)"), "mgh-oxytocin-obesity": ("Intranasal oxytocin", "비강 옥시토신"),
    "bentrio-altamira": ("Bentrio", "Bentrio"), "polyrizon-pl14": ("PL-14 Allergy Blocker", "PL-14 Allergy Blocker"), "tor582-hht": ("TOR-582 (sirolimus)", "TOR-582 (시롤리무스)"),
    "cyrano-cyr064": ("CYR-064", "CYR-064"), "alixer-aldp001": ("ALDP001", "ALDP001"), "vivavision-vvn432": ("VVN432", "VVN432"),
    "pumecitinib-pg011": ("PG-011 (pumecitinib)", "PG-011 (pumecitinib)"), "cenegermin-naion": ("Cenegermin (nasal NGF)", "세네게르민 (비강 NGF)"),
    "chf6467": ("CHF6467 (NGF)", "CHF6467 (NGF)"), "tr-012001": ("TR-012001 (levodopa)", "TR-012001 (레보도파)"),
    "sls-002": ("SLS-002 (ketamine)", "SLS-002 (케타민)"), "acp-101": ("ACP-101 (carbetocin)", "ACP-101 (카베토신)"),
    "prt042-rketamine": ("PRT042 ((R)-ketamine)", "PRT042 ((R)-케타민)"), "tnx1900-pain": ("TNX-1900 (oxytocin)", "TNX-1900 (옥시토신)"),
    "hengrui-dexmed": ("Dexmedetomidine spray", "덱스메데토미딘 스프레이"), "flumist-home": ("FluMist / FluMist Home", "FluMist / FluMist Home"),
    "kr-spravato": ("Spravato (Korea)", "스프라바토 (국내)"), "kr-flumist": ("FluMist (Korea)", "플루미스트 (국내)"), "kr-ryaltris": ("Ryaltris (Korea)", "리알트리스 (국내)"),
    "kr-daewoong-nasal-platform": ("Nasal spray platform (N2B)", "비강 스프레이 플랫폼 (N2B)"), "kr-daewoong-noseguard": ("Noseguard / Noseguard Night", "노즈가드 / 노즈가드 나이트"),
    "kr-koreabnc-jinmedicine": ("Nasal GLP-1/GIP agonist", "비강 GLP-1/GIP 작용제"), "kr-matica-vaxdome": ("Nasal hybrid antiviral vaccine", "비강 하이브리드 항바이러스 백신"),
    "kr-skbio-nasal-binder": ("Nasal antiviral binder protein", "비강 항바이러스 결합단백질"), "kr-caregen-spikedown": ("CG-SpikeDown", "CG-SpikeDown"),
    "kr-bioen-bnin01": ("BNIN01 (nasal insulin)", "BNIN01 (비강 인슐린)"), "jp-neffy-alfresa": ("neffy (Japan)", "neffy (일본)"),
    "jp-spydia": ("Spydia (diazepam)", "스피지아 (디아제팜)"), "jp-esketamine-ph3": ("Esketamine (Japan Ph3)", "에스케타민 (일본 3상)"),
    "cn-neffy-pediatrix": ("neffy (China, 优敏速)", "neffy (중국, 优敏速)"), "cn-huahui-hh120": ("HH-120", "HH-120"), "cn-paloalto-pa9159": ("PA9159", "PA9159"),
    "spravato": ("Spravato", "스프라바토"), "valtoco": ("Valtoco", "발토코"), "tyrvaya": ("Tyrvaya", "티르바야"),
    "narcan": ("Narcan (OTC naloxone)", "Narcan (OTC 날록손)"), "rivive": ("RiVive (OTC naloxone)", "RiVive (OTC 날록손)"),
    "niaid-nasal-covid": ("NIAID nasal COVID candidates", "NIAID 비강 코로나 후보"),
}
COMPANY = {
    "tyrvaya": ("Harrow (from Viatris)", "Harrow (Viatris로부터 인수)"), "bpl-003": ("AtaiBeckley → Eli Lilly", "AtaiBeckley → Eli Lilly"),
    "tr-012001": ("SNLD (SNBL group)", "SNLD (SNBL 계열)"), "intranasal-insulin-wfu": ("Wake Forest University", "Wake Forest 대학"),
    "protollin-ad": ("Brigham and Women's / I-Mab", "Brigham and Women's / I-Mab"), "sls-002": ("Seelos (bankrupt)", "Seelos (파산)"),
    "inp105": ("Impel (liquidated)", "Impel (청산)"), "trudhesa": ("Impel (assets sold 2024)", "Impel (2024년 자산 매각)"), "zavzpret": ("Pfizer", "Pfizer"),
    "atzumi": ("Satsuma (SNBL)", "Satsuma (SNBL)"), "cessatech-ct001": ("Cessatech (Denmark)", "Cessatech (덴마크)"), "tnx1900-pain": ("Yale / Tonix", "Yale / Tonix"),
    "pecfent": ("Grünenthal and others", "Grünenthal 외"), "kloxxado": ("Hikma / Emergent", "Hikma / Emergent"), "opvee": ("Indivior", "Indivior"),
    "baqsimi": ("Amphastar (from Lilly)", "Amphastar (Lilly로부터 인수)"), "neffy": ("ARS Pharmaceuticals", "ARS Pharmaceuticals"),
    "bcht-nasal-laiv": ("Changchun BCHT", "창춘 BCHT"), "cn-bcht-laiv": ("Changchun BCHT", "창춘 BCHT"), "incovacc": ("Bharat Biotech", "Bharat Biotech"),
    "pneucolin": ("Wantai / Xiamen University", "Wantai / 샤먼대학"), "coviliv": ("Codagenix / Serum Institute", "Codagenix / Serum Institute"),
    "deltaflu": ("Vivaldi Biosciences", "Vivaldi Biosciences"), "tb-flu-05e": ("Smorodintsev Institute", "Smorodintsev 연구소"),
    "nons-enovid": ("SaNOtize", "SaNOtize"), "azelastine-covid": ("URSAPHARM", "URSAPHARM"), "xf-73-nasal": ("Moirai (EMV Capital)", "Moirai (EMV Capital)"),
    "hy-133": ("HYpharm", "HYpharm"), "etripamil-cardamyst": ("Milestone (China: Everest)", "Milestone (중국: Everest)"),
    "xhance-eds": ("Paratek (ex-Optinose)", "Paratek (구 Optinose)"), "ryaltris": ("Glenmark", "Glenmark"),
    "wl1006-semaglutide-nasal": ("Shanghai World Leader", "상하이 월드리더"), "mgh-oxytocin-obesity": ("Mass General Hospital", "매사추세츠 종합병원"),
    "alixer-aldp001": ("Alixer Nexgen", "Alixer Nexgen"), "bentrio-altamira": ("Altamira", "Altamira"), "tor582-hht": ("Columbia University", "컬럼비아대"),
    "kr-matica-vaxdome": ("Matica Bio × Vaxdome", "마티카바이오 × 백스돔"), "kr-skbio-nasal-binder": ("SK bioscience", "SK바이오사이언스"),
    "jp-neffy-alfresa": ("Alfresa Pharma", "Alfresa Pharma"), "cn-neffy-pediatrix": ("Pediatrix Therapeutics", "Pediatrix Therapeutics"),
    "jp-spydia": ("Aculys / Viatris", "Aculys / Viatris"), "purity-dexmed": ("Sichuan Purity", "쓰촨 Purity"), "spravato": ("Johnson & Johnson", "Johnson & Johnson"),
    "kr-spravato": ("Janssen Korea", "한국얀센"),
    "prt042-rketamine": ("Sichuan Purity", "쓰촨 Purity"), "prt-064040": ("Sichuan Purity", "쓰촨 Purity"),
    "rivive": ("Harm Reduction Therapeutics", "Harm Reduction Therapeutics"),
}


def unv(s, ko=False):
    return re.sub(r"\s*\(?UNVERIFIED\)?", " (미확인)" if ko else " (unconfirmed)", s).replace("  ", " ")


d = json.load(open("nasal_data.json", encoding="utf-8"))
for c in d["cards"]:
    for table, key in ((STAGE, "stage"), (PRODUCT, "product"), (COMPANY, "company")):
        if c["id"] in table:
            en, ko = table[c["id"]]
            c[key] = {"en": en, "ko": ko}
    for key in ("api", "indication", "device", "now", "stage", "company", "product"):
        c[key] = {"en": unv(c[key]["en"]), "ko": unv(c[key]["ko"], True)}
    if c.get("noTrial"):
        c["noTrial"] = {"en": unv(c["noTrial"]["en"]), "ko": unv(c["noTrial"].get("ko") or c["noTrial"]["en"], True)}
for n in d["news"]:
    n["text"] = {"en": unv(n["text"]["en"]), "ko": unv(n["text"]["ko"], True)}
json.dump(d, open("nasal_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("still-long stages:", [(c["id"], c["stage"]["en"]) for c in d["cards"] if len(c["stage"]["en"]) > 26])
print("still-long products:", [(c["id"], c["product"]["en"]) for c in d["cards"] if len(c["product"]["en"]) > 30])
print("still-long companies:", [(c["id"], c["company"]["en"]) for c in d["cards"] if len(c["company"]["en"]) > 34])
