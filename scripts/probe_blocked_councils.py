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
import re
import sys
import time
from pathlib import Path

import requests

# The 17 councils that answered 403 to Railway in the latest finished run (read 2026-10-25).
TARGETS = [
 {
  "council": "blacktown",
  "list_page": "https://www.blacktown.nsw.gov.au/Plan-build/Stage-2-plans-and-guidelines/Blacktown-planning-controls/Blacktown-Development-Control-Plan-2015",
  "chapter_pdf": None
 },
 {
  "council": "burwood",
  "list_page": "https://www.burwood.nsw.gov.au/Planning-and-Development/Planning-Controls/Development-Control-Plans",
  "chapter_pdf": None
 },
 {
  "council": "campbelltown",
  "list_page": "https://www.campbelltown.nsw.gov.au/Build-and-Develop/Planning-Policies-and-Controls-1/Development-Control-Plans/Campbelltown-Sustainable-City-Development-Control-Plan-2015",
  "chapter_pdf": None
 },
 {
  "council": "fairfield",
  "list_page": "https://www.fairfieldcity.nsw.gov.au/Development/Development-Controls/Development-Control-Plan",
  "chapter_pdf": None
 },
 {
  "council": "hornsby",
  "list_page": "https://www.hornsby.nsw.gov.au/council/noticeboard/hornsby-development-control-plan",
  "chapter_pdf": None
 },
 {
  "council": "ku_ring_gai",
  "list_page": "https://www.krg.nsw.gov.au/Planning-and-development/Planning-policies-and-guidelines/Ku-ring-gai-Development-Control-Plan",
  "chapter_pdf": None
 },
 {
  "council": "liverpool",
  "list_page": None,
  "chapter_pdf": "https://www.liverpool.nsw.gov.au/__data/assets/pdf_file/0015/111822/Part-8-Dwelling-houses-and-class-10-structures-on-lots-greater-than-300m2-but-less-than-900m2-in-the-R1-R2-R3-zones-PDF-copy-linked-to-webpage-23-January-2017.pdf"  # noqa: zone-codes (a council file name)
 },
 {
  "council": "parramatta",
  "list_page": "https://www.cityofparramatta.nsw.gov.au/development/plans-and-strategies/development-control-plans",
  "chapter_pdf": None
 },
 {
  "council": "randwick",
  "list_page": "https://www.randwick.nsw.gov.au/planning-and-building/planning-strategies-and-control/development-control-plan-dcp",
  "chapter_pdf": "https://www.randwick.nsw.gov.au/__data/assets/pdf_file/0018/442251/C1-Low-Density-Residential-Randwick-DCP-Stage-2_Final.pdf"
 },
 {
  "council": "ryde",
  "list_page": "https://www.ryde.nsw.gov.au/development/planning-controls/development-control-plan",
  "chapter_pdf": None
 },
 {
  "council": "strathfield",
  "list_page": "https://www.strathfield.nsw.gov.au/Develop/Planning-Policies",
  "chapter_pdf": None
 },
 {
  "council": "sutherland_shire",
  "list_page": "https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp",
  "chapter_pdf": "https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0027/119259/Chapter-36-Vehicular-Access,-Traffic,-Parking-and-Bicycles-May-2026.pdf"
 },
 {
  "council": "the_hills",
  "list_page": "https://www.thehills.nsw.gov.au/Building-and-Development/Development-Controls/Development-Control-Plans",
  "chapter_pdf": None
 },
 {
  "council": "the_hills_shire",
  "list_page": "https://www.thehills.nsw.gov.au/Building-and-Development/Development-Controls/Development-Control-Plans",
  "chapter_pdf": None
 },
 {
  "council": "waverley",
  "list_page": "https://www.waverley.nsw.gov.au/planning/development_applications/development_control_plan_2022",
  "chapter_pdf": "https://www.waverley.nsw.gov.au/media/documents/building_and_development/dcp/WDCP_2022_updated.pdf"
 },
 {
  "council": "wingecarribee",
  "list_page": "https://www.wsc.nsw.gov.au/Plan-and-Build/Development-Control-Plans",
  "chapter_pdf": None
 },
 {
  "council": "wollongong",
  "list_page": "https://www.wollongong.nsw.gov.au/plan-and-build/development-planning-rules/development-control-plans",
  "chapter_pdf": "https://www.wollongong.nsw.gov.au/__data/assets/pdf_file/0025/8926/Chapter-A1-Introduction-In-Force-5-March-25.pdf"
 }
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/125.0.0.0 Safari/537.36")
LIVERPOOL_PAGE = "https://www.liverpool.nsw.gov.au/development/liverpools-planning-controls/liverpool-development-control-plan"


def is_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


_PDF_LINK = re.compile(rb"href=[\"'][^\"']+\.pdf", re.IGNORECASE)


def page_ok(status: int, b: bytes) -> bool:
    """A real DCP list page: HTTP 200 and at least 3 links to PDFs (a challenge page echoing the URL has none)."""
    return status == 200 and len(_PDF_LINK.findall(b)) >= 3


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
                    # A PDF that opens in the browser instead of downloading (Sol): navigate to it.
                    try:
                        r = page.goto(t["chapter_pdf"], timeout=90000)
                        b = r.body() if r else b""
                        out["pdf.open"] = f"{'OK' if is_pdf(b) else 'no'}:{r.status if r else 0}"
                        got = got or is_pdf(b)
                    except Exception as e2:  # noqa: BLE001
                        out["pdf.open"] = f"err:{type(e2).__name__}"
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
    # Always a failure exit (Sol): the DCP sweep did NOT run, so a switch left on must page someone.
    print("DCP_PROBE_BLOCKED is set: the DCP monitor did not run. Remove the variable.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
