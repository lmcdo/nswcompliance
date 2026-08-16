#!/usr/bin/env python3
"""Reset stale check_failures from the blind period (Apr-May 2026).
Also reset instrument_registry failures from AustLII 403s."""
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

# Reset DCP chapter failures (accumulated during blind period)
cur.execute("""
    UPDATE dcp_chapter_registry
    SET check_failures = 0
    WHERE is_active = TRUE AND check_failures > 0
    RETURNING council, chapter_key, check_failures
""")
reset_dcp = cur.fetchall()
print(f"Reset {len(reset_dcp)} DCP chapter failure counters:")
for council, key, old_fails in reset_dcp:
    print(f"  {council}/{key}: {old_fails} → 0")

# Reset instrument_registry failures (AustLII 403 period)
# Keep needs_review=TRUE for SEPPs — they do need review
cur.execute("""
    UPDATE instrument_registry
    SET check_failures = 0
    WHERE is_active = TRUE AND check_failures > 0
    RETURNING instrument_key, check_failures
""")
reset_inst = cur.fetchall()
print(f"\nReset {len(reset_inst)} instrument failure counters:")
for key, old_fails in reset_inst:
    print(f"  {key}: {old_fails} → 0")

conn.commit()
conn.close()
print("\nDone.")
