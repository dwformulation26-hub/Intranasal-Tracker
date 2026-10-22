"""Request every source URL in nasal_data.json and record the HTTP outcome in data/weekly/link_check.json.

SEC, BusinessWire, StockTitan and fda.gov answer scripts with 403/404 even when the page exists; treat those
as "check in a browser", not as broken. A SOFT404 (page title says not found) is always a real problem.
"""
import json
import re
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
d = json.load(open(ROOT / "nasal_data.json", encoding="utf-8"))
links = [("card", c["id"], c["src"]["url"]) for c in d["cards"]]
links += [("news", f"{n['date']} {n['text']['en'][:50]}", n["src"]["url"]) for n in d["news"] if n.get("src")]
links += [("guidance", g["title"][:60], g["url"]) for g in d["endpoints"]["guidance"] if g.get("url")]


def check(item):
    kind, ref, url = item
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as r:
            head = r.read(60000).decode("utf-8", "ignore").lower()
            m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S)
            title = (m.group(1).strip() if m else "")[:120]
            soft404 = any(s in title for s in ("not found", "404", "page unavailable", "error"))
            return [kind, ref, url, "SOFT404" if soft404 else r.status, title]
    except urllib.error.HTTPError as e:
        return [kind, ref, url, e.code, None]
    except Exception as e:
        return [kind, ref, url, type(e).__name__, None]


with ThreadPoolExecutor(12) as ex:
    res = list(ex.map(check, links))
json.dump(res, open(ROOT / "data" / "weekly" / "link_check.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok = [r for r in res if r[3] == 200]
print(f"{len(res)} links: {len(ok)} OK")
for r in res:
    if r[3] != 200:
        print(f"  {r[3]} | {r[0]} | {r[1][:45]} | {r[2][:110]}")
