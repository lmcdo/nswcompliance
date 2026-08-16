#!/usr/bin/env python3
"""
PDF Bookmark Investigation
==========================
Checks whether DCP PDFs from NSW councils have a PDF outline/bookmark tree
that could replace hardcoded page range configs in dcp_extract_changed.py.

Usage:
    python scripts/check_pdf_bookmarks.py
"""
import os
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import requests
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import PDFException

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PlotDetect/1.0; +https://plotdetect.com.au)"
}

# ── Local PDFs already downloaded ───────────────────────────────────────────
LOCAL_PDFS = {
    # Inner West LGAs
    "ashfield/chapter-a-miscellaneous":   r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\ashfield\chapter-a-miscellaneous.pdf",
    "ashfield/chapter-d-precinct-guidelines": r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\ashfield\chapter-d-precinct-guidelines.pdf",
    "ashfield/chapter-e1-heritage":       r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\ashfield\chapter-e1-heritage.pdf",
    "leichhardt/part-g-s1-12":            r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\leichhardt\Leichhardt_DCP_2013_Part_G_Section_1-12_Amdt19_Nov2023.pdf",
    "marrickville/9.1-lewisham":          r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\marrickville_complete\9.1_Lewisham_North_Precinct_1.pdf",
    "marrickville/9.4-newtown":           r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\marrickville_complete\9.4_Newtown_North_and_Camperdown.pdf",
    "ku_ring_gai/part-12-signage":        r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\downloads\ku_ring_gai\part-12-signage.pdf",
    "waverley/full-dcp":                  r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\waverley\DCPpdfimages\Waverley_DCP_2022_Full_Version_Amendment5-1.pdf",
}

# ── Remote PDFs — 10 other Sydney LGAs ──────────────────────────────────────
# One representative DCP chapter PDF per council.
REMOTE_PDFS = {
    "city_of_sydney/dcp2012":        "https://www.cityofsydney.nsw.gov.au/-/media/corporate/files/publications/development-control-plans/schedules-dcp2012_261121.pdf",
    "parramatta/dcp2023":            "https://cityofparramatta.nsw.gov.au/sites/council/files/2024-09/Parramatta_DCP_2023_(Amendment_4)-As_published_18_September_2024-BOOK_VERSION.pdf",
    "ryde/dcp2014":                  "https://www.ryde.nsw.gov.au/files/assets/public/v/1/development/dcp/dcp-2014-1.0-introduction.pdf",
    "lane_cove/dcp2009":             "https://s3-ap-southeast-2.amazonaws.com/shared-drupal-s3fs/master-test/fapub_pdf/_R15/Lane%20Cove%20DCP%202009%20-%20as%20amended%2024%20Feb%202016.pdf",
    "randwick/dcp_vol1":             "https://www.randwick.nsw.gov.au/__data/assets/pdf_file/0020/13736/Randwick-Comprehensive-DCP-Volume-1-Parts-A-C.pdf",
    "northern_beaches/warringah":    "https://www.austlii.edu.au/au/other/nsw/NSWEPIDCP/2020/6.pdf",
    "canterbury_bankstown/dcp2023":  "https://hdp-au-prod-app-cbnks-haveyoursay-files.s3.ap-southeast-2.amazonaws.com/5617/4468/8884/Canterbury-Bankstown_Development_Control_Plan_2023.pdf",
    "georges_river/dcp2021_toc":     "https://www.georgesriver.nsw.gov.au/StGeorge/media/Documents/Development/Strategic%20Planning/GRDCP-2021-Table-of-Contents-Effective-October-2021.PDF",
    "bayside/dcp2022":               "https://www.bayside.nsw.gov.au/sites/default/files/2024-06/bayside_development_control_plan_2022.pdf",
    "sutherland/dcp_ch21":           "https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0021/6690/21-b3-commercial-core-menai-am-6-to-publish-pdf-20210310.pdf",
}


def check_bookmarks(source: str) -> dict:
    """
    Returns dict with:
      has_bookmarks: bool
      count: int
      depth: int (max nesting level)
      sample: list of (level, title) for first 10 entries
      pages: int (total pages)
      error: str | None
    """
    result = {"has_bookmarks": False, "count": 0, "depth": 0, "sample": [], "pages": 0, "error": None}

    try:
        with open(source, "rb") as f:
            parser = PDFParser(f)
            doc = PDFDocument(parser)

            # Page count
            try:
                import pdfplumber
                with pdfplumber.open(source) as pdf:
                    result["pages"] = len(pdf.pages)
            except Exception:
                pass

            # Bookmarks / outline
            try:
                outlines = list(doc.get_outlines())
                result["has_bookmarks"] = len(outlines) > 0
                result["count"] = len(outlines)
                result["depth"] = max((level for level, *_ in outlines), default=0) if outlines else 0
                result["sample"] = [(level, title) for level, title, *_ in outlines[:12]]
            except Exception as e:
                result["error"] = f"outline error: {e}"

    except Exception as e:
        result["error"] = str(e)

    return result


def fetch_and_check(name: str, url: str) -> dict:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        if resp.status_code != 200:
            return {"has_bookmarks": False, "count": 0, "depth": 0, "sample": [], "pages": 0,
                    "error": f"HTTP {resp.status_code}"}
        # Download first 5MB — enough to get the cross-reference table and outline
        content = b""
        for chunk in resp.iter_content(65536):
            content += chunk
            if len(content) >= 5 * 1024 * 1024:
                break

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = check_bookmarks(tmp_path)
        os.unlink(tmp_path)
        return result
    except Exception as e:
        return {"has_bookmarks": False, "count": 0, "depth": 0, "sample": [], "pages": 0, "error": str(e)}


def main():
    print("=" * 70)
    print("PDF BOOKMARK INVESTIGATION")
    print("Checking for PDF outline/TOC that could replace hardcoded page ranges")
    print("=" * 70)

    all_results = {}

    print("\n── LOCAL PDFs (Inner West LGAs + KRG + Waverley) ──────────────────────")
    for name, path in LOCAL_PDFS.items():
        if not Path(path).exists():
            print(f"  {name:<45} MISSING: {path}")
            continue
        r = check_bookmarks(path)
        all_results[name] = r
        status = f"YES — {r['count']} entries, depth {r['depth']}" if r["has_bookmarks"] else "NO bookmarks"
        if r["error"] and not r["has_bookmarks"]:
            status = f"ERROR: {r['error']}"
        print(f"  {name:<45} {r['pages']:>4}pp  {status}")
        if r["has_bookmarks"] and r["sample"]:
            for level, title in r["sample"][:5]:
                print(f"    {'  ' * (level-1)}[{level}] {title}")

    print("\n── REMOTE PDFs (10 other Sydney LGAs) ──────────────────────────────────")
    for name, url in REMOTE_PDFS.items():
        print(f"  Fetching {name}...", end=" ", flush=True)
        r = fetch_and_check(name, url)
        all_results[name] = r
        status = f"YES — {r['count']} entries, depth {r['depth']}" if r["has_bookmarks"] else "NO bookmarks"
        if r["error"] and not r["has_bookmarks"]:
            status = f"ERROR/UNREACHABLE: {r['error']}"
        print(f"{r['pages']:>4}pp  {status}")
        if r["has_bookmarks"] and r["sample"]:
            for level, title in r["sample"][:5]:
                print(f"    {'  ' * (level-1)}[{level}] {title}")

    # Summary
    with_bookmarks = [k for k, v in all_results.items() if v["has_bookmarks"]]
    without = [k for k, v in all_results.items() if not v["has_bookmarks"] and not v["error"]]
    errors = [k for k, v in all_results.items() if v["error"] and not v["has_bookmarks"]]

    print("\n── SUMMARY ──────────────────────────────────────────────────────────────")
    print(f"  Have bookmarks:    {len(with_bookmarks)}")
    print(f"  No bookmarks:      {len(without)}")
    print(f"  Error/unreachable: {len(errors)}")
    print()
    if with_bookmarks:
        print("  With bookmarks (page ranges auto-derivable):")
        for k in with_bookmarks:
            r = all_results[k]
            print(f"    {k} — {r['count']} entries, depth {r['depth']}")
    if without:
        print("  Without bookmarks (still need hardcoded configs):")
        for k in without:
            print(f"    {k}")


if __name__ == "__main__":
    main()
