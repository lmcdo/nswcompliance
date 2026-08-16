#!/usr/bin/env python3
"""Diagnostic: detailed marrickville failure analysis + sample URL tests."""
import os
import sys
import time
import psycopg2
import requests
from dotenv import load_dotenv
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Get marrickville chapters with failures
cur.execute("""
    SELECT chapter_key, council_url, check_failures, url_etag, content_hash,
           url_last_checked, url_last_changed, is_spatial, is_inert
    FROM dcp_chapter_registry
    WHERE is_active = TRUE AND council = 'marrickville'
    ORDER BY check_failures DESC, chapter_key
    LIMIT 10
""")
print("=== MARRICKVILLE FAILING CHAPTERS (top 10) ===\n")
sample_urls = []
for row in cur.fetchall():
    key, url, fails, etag, hash_, checked, changed, spatial, inert = row
    flags = []
    if spatial: flags.append("spatial")
    if inert: flags.append("inert")
    flag_str = f" [{','.join(flags)}]" if flags else ""
    print(f"  {key:<45} fails={fails}  etag={'Y' if etag else 'N'}  hash={'Y' if hash_ else 'N'}{flag_str}")
    print(f"    URL: {url[:100]}...")
    if len(sample_urls) < 5:
        sample_urls.append((key, url))

# Also check canterbury_bankstown and liverpool
cur.execute("""
    SELECT council, chapter_key, council_url, check_failures
    FROM dcp_chapter_registry
    WHERE is_active = TRUE AND council IN ('canterbury_bankstown', 'liverpool')
    ORDER BY council, chapter_key
""")
print("\n=== OTHER FAILING COUNCILS ===\n")
for row in cur.fetchall():
    council, key, url, fails = row
    print(f"  {council}/{key}  fails={fails}")
    print(f"    URL: {url}")
    if len(sample_urls) < 8:
        sample_urls.append((f"{council}/{key}", url))

conn.close()

# Test sample URLs from local machine
print("\n=== LOCAL HEAD TESTS (sample URLs) ===\n")
for label, url in sample_urls:
    try:
        resp = requests.head(url, headers=HEADERS, timeout=15, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "?")
        cl = resp.headers.get("Content-Length", "?")
        etag = resp.headers.get("ETag", "none")
        print(f"  {label:<45} HTTP {resp.status_code}  CT={ct[:30]}  CL={cl}  ETag={etag[:30]}")
    except Exception as e:
        print(f"  {label:<45} ERROR: {e}")
    time.sleep(1)

# Test AustLII
print("\n=== AUSTLII TEST ===\n")
for name, url in [
    ("sepp_housing_2021", "https://classic.austlii.edu.au/au/legis/nsw/consol_reg/sepp2021448/"),
    ("sepp_exempt_complying_2008", "https://classic.austlii.edu.au/au/legis/nsw/consol_reg/seppacdc2008721/"),
]:
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; PlotDetect/1.0)", "Accept": "text/html,*/*"}, timeout=15)
        print(f"  {name:<35} HTTP {resp.status_code}  len={len(resp.text)}")
        if resp.status_code == 200 and "As at" in resp.text:
            import re
            m = re.search(r"As at\s+(\d{1,2}\s+\w+\s+\d{4})", resp.text)
            if m:
                print(f"    As at: {m.group(1)}")
    except Exception as e:
        print(f"  {name:<35} ERROR: {e}")
    time.sleep(1)

# Test PCO export endpoint
print("\n=== PCO EXPORT TEST ===\n")
try:
    resp = requests.get(
        "https://legislation.nsw.gov.au/export/week?format=json",
        headers={"User-Agent": "Mozilla/5.0 (compatible; PlotDetect/1.0)", "Accept": "application/json,*/*"},
        timeout=15,
    )
    print(f"  /export/week?format=json  HTTP {resp.status_code}  CT={resp.headers.get('Content-Type', '?')}")
    if resp.status_code == 200:
        data = resp.json() if "json" in resp.headers.get("Content-Type", "") else None
        if data:
            print(f"  Returned {len(data)} items")
            for item in data[:3]:
                print(f"    {item}")
        else:
            print(f"  Response (first 500 chars): {resp.text[:500]}")
    else:
        print(f"  Response: {resp.text[:300]}")
except Exception as e:
    print(f"  ERROR: {e}")
