#!/usr/bin/env python3
# prior-art-checked: no fetch method other than requests exists in scripts/ or hub_scrapers/; this is a
# one-off measurement, not part of the monitor.
"""Measure, FROM RAILWAY, which fetch method gets past each blocked council's firewall.

Runs instead of the monitor only when DCP_PROBE_BLOCKED=1 (run_monitors.monitor_cmd). Read-only: one GET per
method per address, a few seconds apart. Prints a table and a summary; writes nothing.

Same test that passed from GitHub's machines on 2026-10-25: list pages 11/16 (curl_cffi 8, Chrome 11), PDFs
5/5 once Chrome had visited the council's page first. Railway's addresses may be treated differently, so this
decides whether the fallback is worth building.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

TARGETS = json.loads((Path(__file__).parent / "probe_blocked_targets.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/125.0.0.0 Safari/537.36")
LIVERPOOL_PAGE = "https://www.liverpool.nsw.gov.au/development/liverpools-planning-controls/liverpool-development-control-plan"


def is_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


def page_ok(status: int, b: bytes) -> bool:
    return status == 200 and (b".pdf" in b.lower() or b"development control plan" in b.lower())


def main() -> int:
    from curl_cffi import requests as cr
    from playwright.sync_api import sync_playwright

    lists = pdfs = list_ok = pdf_ok = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        for t in TARGETS:
            page_url = t["list_page"] or (LIVERPOOL_PAGE if t["council"] == "liverpool" else None)
            out: dict[str, str] = {}
            if t["list_page"]:
                lists += 1
                try:
                    r = requests.get(page_url, timeout=40, headers={"User-Agent": UA})
                    out["list.plain"] = f"{'OK' if page_ok(r.status_code, r.content) else 'no'}:{r.status_code}"
                except Exception as e:  # noqa: BLE001
                    out["list.plain"] = f"err:{type(e).__name__}"
                time.sleep(3)
                try:
                    r = cr.get(page_url, impersonate="chrome", timeout=40)
                    out["list.cffi"] = f"{'OK' if page_ok(r.status_code, r.content) else 'no'}:{r.status_code}"
                except Exception as e:  # noqa: BLE001
                    out["list.cffi"] = f"err:{type(e).__name__}"
                time.sleep(3)
            ctx = browser.new_context(user_agent=UA, accept_downloads=True, locale="en-AU")
            page = ctx.new_page()
            try:
                r = page.goto(page_url, timeout=60000, wait_until="domcontentloaded") if page_url else None
                page.wait_for_timeout(4000)
                body = page.content().encode("utf-8", "replace") if r else b""
                good = bool(r) and page_ok(r.status, body)
                out["list.chrome"] = f"{'OK' if good else 'no'}:{r.status if r else 0}"
                if t["list_page"] and good:
                    list_ok += 1
                elif t["list_page"] and any(out.get(k, "").startswith("OK") for k in ("list.plain", "list.cffi")):
                    list_ok += 1
            except Exception as e:  # noqa: BLE001
                out["list.chrome"] = f"err:{type(e).__name__}"
            if t["chapter_pdf"]:
                pdfs += 1
                got = False
                time.sleep(3)
                try:
                    with page.expect_download(timeout=90000) as d:
                        page.evaluate("u => { const a = document.createElement('a'); a.href = u; a.download = '';"
                                      " document.body.appendChild(a); a.click(); }", t["chapter_pdf"])
                    b = Path(d.value.path()).read_bytes()
                    out["pdf.download"] = f"{'OK' if is_pdf(b) else 'no'}:{len(b)}"
                    got = got or is_pdf(b)
                except Exception as e:  # noqa: BLE001
                    out["pdf.download"] = f"err:{type(e).__name__}"
                time.sleep(3)
                try:
                    jar = {c["name"]: c["value"] for c in ctx.cookies()}
                    r = cr.get(t["chapter_pdf"], impersonate="chrome", cookies=jar, timeout=90,
                               headers={"Referer": page_url or ""})
                    good = r.status_code == 200 and is_pdf(r.content)
                    out["pdf.cffi+cookies"] = f"{'OK' if good else 'no'}:{r.status_code}"
                    got = got or good
                except Exception as e:  # noqa: BLE001
                    out["pdf.cffi+cookies"] = f"err:{type(e).__name__}"
                pdf_ok += got
            ctx.close()
            print(f"PROBE {t['council']:18} " + "  ".join(f"{k}={v}" for k, v in out.items()), flush=True)
            time.sleep(3)
        browser.close()
    print(f"PROBE SUMMARY list pages read: {list_ok}/{lists}   PDFs downloaded: {pdf_ok}/{pdfs}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
