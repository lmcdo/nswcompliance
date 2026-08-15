#!/usr/bin/env python3
"""Diagnostic: query DCP + instrument registry state."""
import os
import sys
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# DCP chapter registry state
cur.execute("""
    SELECT council, COUNT(*) as total,
           COUNT(*) FILTER (WHERE check_failures >= 3) as failing_3plus,
           COUNT(*) FILTER (WHERE check_failures >= 1) as failing_1plus,
           COUNT(*) FILTER (WHERE needs_extraction = TRUE) as pending_extract,
           MAX(url_last_checked) as last_check,
           MAX(check_failures) as max_failures
    FROM dcp_chapter_registry WHERE is_active = TRUE
    GROUP BY council ORDER BY council
""")
print("=== DCP CHAPTER REGISTRY STATE ===\n")
for row in cur.fetchall():
    council, total, f3, f1, pend, last_check, max_f = row
    print(f"  {council:<20} total={total:<4} fail3+={f3:<4} fail1+={f1:<4} pending={pend:<4} max_fail={max_f:<4} last_check={last_check}")

# Instrument registry state
cur.execute("""
    SELECT instrument_key, instrument_type, current_version, last_checked, check_failures, needs_review
    FROM instrument_registry WHERE is_active = TRUE
    ORDER BY instrument_type, instrument_key
""")
print("\n=== INSTRUMENT REGISTRY STATE ===\n")
for row in cur.fetchall():
    key, itype, ver, checked, fails, review = row
    print(f"  {key:<35} type={itype:<5} version={str(ver):<45} failures={fails or 0}  review={review}  checked={checked}")

cur.execute("SELECT COUNT(*) FROM dcp_chapter_registry WHERE is_active = TRUE")
total = cur.fetchone()[0]
print(f"\nTotal active DCP chapters: {total}")

# ETag state — how many have stored ETags?
cur.execute("""
    SELECT council,
           COUNT(*) as total,
           COUNT(*) FILTER (WHERE url_etag IS NOT NULL) as has_etag,
           COUNT(*) FILTER (WHERE content_hash IS NOT NULL) as has_hash
    FROM dcp_chapter_registry WHERE is_active = TRUE
    GROUP BY council ORDER BY council
""")
print("\n=== ETAG / HASH COVERAGE ===\n")
for row in cur.fetchall():
    council, total, etag, hashc = row
    print(f"  {council:<20} total={total:<4} has_etag={etag:<4} has_hash={hashc:<4}")

conn.close()
