"""One-off test: which way of fetching gets past each blocked council's firewall from a data-centre machine.
Read-only GETs, one per method per URL, 3 s apart. Prints a table. Not part of the monitor."""
import json, time, sys
import requests

T = json.load(open("probe/targets.json"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/125.0.0.0 Safari/537.36")
BROWSER = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "en-AU,en;q=0.9", "Upgrade-Insecure-Requests": "1"}


def plain(u):
    r = requests.get(u, timeout=40, headers={"User-Agent": "Mozilla/5.0 (compatible; PlotDetect-DCP-Monitor/1.0)"})
    return r.status_code, r.content


def headers(u):
    r = requests.get(u, timeout=40, headers=BROWSER)
    return r.status_code, r.content


def cffi(u):
    from curl_cffi import requests as cr
    r = cr.get(u, timeout=40, impersonate="chrome")
    return r.status_code, r.content


_pw = None


def chrome(u):
    global _pw
    from playwright.sync_api import sync_playwright
    if _pw is None:
        p = sync_playwright().start()
        _pw = p.chromium.launch(headless=True).new_context(user_agent=UA, accept_downloads=True)
    page = _pw.new_page()
    try:
        resp = page.request.get(u, timeout=60000) if u.lower().endswith(".pdf") else page.goto(u, timeout=60000)
        status = resp.status if resp else 0
        body = resp.body() if resp else b""
        return status, body
    finally:
        page.close()


def ok(status, body, pdf):
    if status != 200:
        return False
    return body[:5] == b"%PDF-" if pdf else (b".pdf" in body.lower() or b"development control plan" in body.lower())


METHODS = [("plain", plain), ("headers", headers), ("curl_cffi", cffi), ("chrome", chrome)]
rows = []
for t in T:
    for kind, url in (("list", t["list_page"]), ("pdf", t["chapter_pdf"])):
        if not url:
            continue
        res = {}
        for name, fn in METHODS:
            try:
                s, b = fn(url)
                res[name] = f"{'OK' if ok(s, b, kind == 'pdf') else 'no'}:{s}"
            except Exception as e:  # noqa: BLE001
                res[name] = f"err:{type(e).__name__}"
            time.sleep(3)
        rows.append((t["council"], kind, res))
        print(f"{t['council']:18} {kind:4} " + "  ".join(f"{k}={v}" for k, v in res.items()), flush=True)

print("\nSUMMARY (targets got through / tried):")
for name, _ in METHODS:
    print(f"  {name:10} {sum(r[2][name].startswith('OK') for r in rows)}/{len(rows)}")
print("  any method", sum(any(v.startswith('OK') for v in r[2].values()) for r in rows), "/", len(rows))
