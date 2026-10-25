"""One-off test, run 2: can a PDF be fetched once a real browser has visited the council's DCP page first?
Per council: Chrome opens the list page, then the PDF is fetched (a) with the same browser session,
(b) as a browser download, (c) with curl_cffi using the browser's cookies. Read-only, a few requests each."""
import json
import time

from curl_cffi import requests as cr
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/125.0.0.0 Safari/537.36")
T = [t for t in json.load(open("probe/targets.json")) if t["chapter_pdf"]]
for t in T:
    if t["council"] == "liverpool" and not t["list_page"]:
        t["list_page"] = ("https://www.liverpool.nsw.gov.au/development/liverpools-planning-controls/"
                          "liverpool-development-control-plan")

pdf = lambda b: b[:5] == b"%PDF-"  # noqa: E731
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for t in T:
        ctx = browser.new_context(user_agent=UA, accept_downloads=True, locale="en-AU")
        page = ctx.new_page()
        out = {}
        try:
            r = page.goto(t["list_page"], timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            out["page"] = r.status if r else 0
        except Exception as e:  # noqa: BLE001
            out["page"] = f"err:{type(e).__name__}"
        try:
            r = ctx.request.get(t["chapter_pdf"], timeout=90000, headers={"Referer": t["list_page"]})
            b = r.body()
            out["session"] = f"{'OK' if r.status == 200 and pdf(b) else 'no'}:{r.status}:{len(b)}"
        except Exception as e:  # noqa: BLE001
            out["session"] = f"err:{type(e).__name__}"
        time.sleep(3)
        try:
            with page.expect_download(timeout=90000) as d:
                page.evaluate("u => { const a = document.createElement('a'); a.href = u; a.download = ''; "
                              "document.body.appendChild(a); a.click(); }", t["chapter_pdf"])
            path = d.value.path()
            b = open(path, "rb").read()
            out["download"] = f"{'OK' if pdf(b) else 'no'}:{len(b)}"
        except Exception as e:  # noqa: BLE001
            out["download"] = f"err:{type(e).__name__}"
        time.sleep(3)
        try:
            jar = {c["name"]: c["value"] for c in ctx.cookies()}
            r = cr.get(t["chapter_pdf"], impersonate="chrome", cookies=jar, timeout=90,
                       headers={"Referer": t["list_page"]})
            out["cffi+cookies"] = f"{'OK' if r.status_code == 200 and pdf(r.content) else 'no'}:{r.status_code}"
        except Exception as e:  # noqa: BLE001
            out["cffi+cookies"] = f"err:{type(e).__name__}"
        out["cookies"] = len(ctx.cookies())
        print(f"{t['council']:18} " + "  ".join(f"{k}={v}" for k, v in out.items()), flush=True)
        ctx.close()
        time.sleep(3)
    browser.close()
