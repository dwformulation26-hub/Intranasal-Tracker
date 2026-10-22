"""Daily news collector: poll config/feeds.json, keep items about intranasal products, append to a rolling cache.

No judgment happens here - the weekly routine reads data/weekly/news_cache.json, opens each source and decides.
Standard library only, so it runs on GitHub Actions without installs.

Usage: python scripts/collect_news.py [--when 3d] [--keep-days 21]
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ctgov import KST, now_kst  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "weekly" / "news_cache.json"
META = ROOT / "data" / "meta.json"
# FDA and some publishers answer browser/python user agents with 403/404 but serve feed readers
UA = {"User-Agent": "curl/8.5.0", "Accept": "application/rss+xml, application/xml, text/xml, */*"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
              "Accept": "application/rss+xml, application/xml, text/xml, */*"}
GENERIC = {"dexmedetomidine", "naloxone", "nasal", "spray", "intranasal", "oxytocin", "insulin", "liquid", "lyophilized",
           "esketamine", "nasodine", "sputnik", "azelastine", "the", "flu", "neffy"}


def fetch(url, timeout=30, browser=False):
    req = urllib.request.Request(url, headers=BROWSER_UA if browser else UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def text(el, *names):
    for n in names:
        x = el.find(n)
        if x is not None and (x.text or "").strip():
            return x.text.strip()
        if x is not None and x.get("href"):
            return x.get("href")
    return ""


def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=KST)
    return d.astimezone(KST).isoformat(timespec="minutes")


def parse_feed(raw):
    root = ET.fromstring(raw)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    out = []
    for it in items:
        if it.tag.endswith("entry"):
            title = text(it, "{http://www.w3.org/2005/Atom}title")
            link_el = it.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href") if link_el is not None else ""
            date = text(it, "{http://www.w3.org/2005/Atom}updated", "{http://www.w3.org/2005/Atom}published")
            desc = text(it, "{http://www.w3.org/2005/Atom}summary")
            source = ""
        else:
            title, link = text(it, "title"), text(it, "link")
            date = text(it, "pubDate", "{http://purl.org/dc/elements/1.1/}date")
            desc = text(it, "description")
            src = it.find("source")
            source = (src.text or "").strip() if src is not None else ""
        title = re.sub(r"<!\[CDATA\[|\]\]>", "", title)
        out.append({"title": re.sub(r"\s+", " ", title).strip(), "link": link.strip(), "published": parse_date(date),
                    "summary": re.sub(r"<[^>]+>|\s+", " ", desc or "")[:400].strip(), "publisher": source})
    return out


def load_keywords():
    k = json.loads((ROOT / "config" / "keywords.json").read_text(encoding="utf-8"))
    d = json.loads((ROOT / "nasal_data.json").read_text(encoding="utf-8"))
    brands = set()
    for c in d["cards"]:  # brand-like first token of each tracked product, e.g. "Cardamyst", "Spydia"
        tok = re.split(r"[\s(/,]", c["product"]["en"])[0]
        if len(tok) >= 5 and tok.lower() not in GENERIC:
            brands.add(tok)
    plain = [w for lang in ("en", "ko", "ja", "zh") for w in k[lang]] + sorted(brands)
    # Latin terms must match whole words ("Fluenz" must not hit "influenza"); CJK terms match anywhere
    alts = [(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])") if w.isascii() else re.escape(w)
            for w in sorted(set(plain), key=len, reverse=True)]
    rx = re.compile("|".join(alts), re.I)
    gated = k["ko_gated"]
    return rx, gated, [e.lower() for e in k["exclude"]], {w.lower() for w in brands} | {w.lower() for w in k["en"] if w[:1].isupper()}


def match(item, rx, gated, exclude, strong):
    hay = f"{item['title']} {item['summary']}"
    hits = {m.group(0) for m in rx.finditer(hay)}
    if not hits and gated["term"] in hay and any(t in hay for t in gated["co_terms"]):
        hits = {gated["term"]}
    if hits and any(e in hay.lower() for e in exclude) and not any(h.lower() in strong for h in hits):
        return []  # e.g. a nasal-polyps or 비강암 story with only generic matches
    return sorted(hits)


def bluesky(queries, since):
    out = []
    for q in queries:
        url = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?" + urllib.parse.urlencode(
            {"q": q, "since": since + "T00:00:00Z", "limit": 50, "sort": "latest"})
        try:
            posts = json.loads(fetch(url)).get("posts", [])
        except Exception as e:
            out.append({"error": f"bluesky {q}: {e}"})
            continue
        for p in posts:
            rec = p.get("record", {})
            handle = p.get("author", {}).get("handle", "")
            rkey = p.get("uri", "").rsplit("/", 1)[-1]
            ext = (p.get("embed", {}) or {}).get("external", {}) or {}
            out.append({"title": rec.get("text", "")[:280].replace("\n", " "),
                        "link": ext.get("uri") or f"https://bsky.app/profile/{handle}/post/{rkey}",
                        "published": parse_date(rec.get("createdAt")), "summary": ext.get("title", ""),
                        "publisher": f"Bluesky @{handle}", "post": f"https://bsky.app/profile/{handle}/post/{rkey}"})
        time.sleep(1)
    return out


def openfda_nasal(days=14):
    start = (now_kst() - timedelta(days=days)).strftime("%Y%m%d")
    q = f'products.route:"NASAL" AND submissions.submission_status_date:[{start} TO {now_kst():%Y%m%d}]'
    url = "https://api.fda.gov/drug/drugsfda.json?" + urllib.parse.urlencode({"search": q, "limit": 100})
    try:
        res = json.loads(fetch(url)).get("results", [])
    except urllib.error.HTTPError as e:
        return [] if e.code == 404 else [{"error": f"openFDA {e.code}"}]
    out = []
    for r in res:
        names = sorted({p.get("brand_name", "") for p in r.get("products", [])})
        for s in r.get("submissions", []):
            if s.get("submission_status_date", "") >= start:
                out.append({"title": f"FDA {s.get('submission_type')} {s.get('submission_number')} "
                                     f"({s.get('submission_class_code_description') or s.get('submission_class_code') or ''}) "
                                     f"{s.get('submission_status')} for {', '.join(names)} - {r.get('sponsor_name')} ({r.get('application_number')})",
                            "link": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={r.get('application_number', '')[3:]}",
                            "published": parse_date(s["submission_status_date"][:4] + "-" + s["submission_status_date"][4:6] + "-" + s["submission_status_date"][6:]),
                            "summary": "openFDA drugsfda record (route NASAL)", "publisher": "FDA (openFDA)"})
    return out


def key(item):
    link = re.sub(r"[?#].*$", "", item.get("link", "")).rstrip("/").lower()
    title = re.sub(r"[^a-z0-9가-힣]", "", item.get("title", "").lower())[:80]
    return hashlib.sha1((title or link).encode()).hexdigest()[:16]


def main():
    when = sys.argv[sys.argv.index("--when") + 1] if "--when" in sys.argv else "3d"
    keep_days = int(sys.argv[sys.argv.index("--keep-days") + 1]) if "--keep-days" in sys.argv else 21
    cfg = json.loads((ROOT / "config" / "feeds.json").read_text(encoding="utf-8"))
    rx, gated, exclude, strong = load_keywords()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {"items": []}
    known = {i["id"] for i in cache["items"]}
    tracked = {n["src"]["url"].rstrip("/").lower() for n in json.loads((ROOT / "nasal_data.json").read_text(encoding="utf-8"))["news"]}
    now = now_kst().isoformat(timespec="minutes")
    health, added = {}, 0
    oldest = (now_kst() - timedelta(days=keep_days)).isoformat()

    def add(item, feed_name, kind, tier, hits):
        nonlocal added
        item.update({"id": key(item), "feed": feed_name, "kind": kind, "tier": tier, "matched": hits, "fetched": now, "status": "new"})
        if item["id"] in known or item["link"].rstrip("/").lower() in tracked:
            return
        known.add(item["id"])
        cache["items"].append(item)
        added += 1

    for f in cfg["feeds"]:
        url = f["url"].replace("{WHEN}", when)
        try:
            items = parse_feed(fetch(url, browser=f.get("ua") == "browser"))
            kept = 0
            for it in items:
                if it["published"] and it["published"] < oldest:
                    continue  # some feeds (e.g. GlobeNewswire keyword) return a year of history
                hits = match(it, rx, gated, exclude, strong)
                if f["filter"] == "none" or hits:
                    add(it, f["name"], f["kind"], f["tier"], hits)
                    kept += 1
            health[f["name"]] = {"status": "ok", "items": len(items), "kept": kept}
        except Exception as e:
            health[f["name"]] = {"status": "error", "error": f"{type(e).__name__}: {str(e)[:120]}"}
        time.sleep(0.5)

    since = (now_kst() - timedelta(days=int(re.sub(r"\D", "", when) or 3))).date().isoformat()
    bs = cfg["apis"]["bluesky"]
    posts = bluesky(bs["queries"], since)
    errs = [p for p in posts if "error" in p]
    for p in posts:
        if "error" in p or not p["title"]:
            continue
        hits = match(p, rx, gated, exclude, strong)
        # social is noisy (consumer chatter): keep only posts naming a tracked brand/company or linking to an article
        if hits and (any(h.lower() in strong for h in hits) or "bsky.app" not in p["link"]):
            add(p, "Bluesky search", "social", bs["tier"], hits)
    health["Bluesky search"] = {"status": "error" if errs and len(errs) == len(bs["queries"]) else "ok", "items": len(posts) - len(errs),
                                "errors": [e["error"] for e in errs][:3]}
    fda = openfda_nasal()
    for r in fda:
        if "error" not in r:
            add(r, "openFDA drugsfda (nasal)", "regulator", 1, ["route NASAL"])
    health["openFDA drugsfda (nasal)"] = {"status": "error" if any("error" in r for r in fda) else "ok", "items": len(fda)}

    cutoff = (now_kst() - timedelta(days=keep_days)).isoformat()
    cache["items"] = [i for i in cache["items"] if i["fetched"] >= cutoff]
    cache["updated"] = now
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    meta = json.loads(META.read_text(encoding="utf-8")) if META.exists() else {}
    meta["last_collect"] = now
    meta["feed_health"] = health
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    bad = [n for n, h in health.items() if h["status"] != "ok"]
    print(f"{added} new items (cache {len(cache['items'])}); {len(health) - len(bad)}/{len(health)} sources ok"
          + (f"; failing: {', '.join(bad)}" if bad else ""))


if __name__ == "__main__":
    main()
