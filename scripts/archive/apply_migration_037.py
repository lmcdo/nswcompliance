#!/usr/bin/env python3
"""Apply migration 037: add change-tracking columns to dcp_setback_controls."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL or SUPABASE_DB_URL not set")
    sys.exit(1)

migration_path = Path(__file__).parent.parent / "migrations" / "037_dcp_controls_change_tracking.sql"
sql = migration_path.read_text(encoding="utf-8")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
try:
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("Migration 037 applied successfully.")

    # Verify columns exist
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'dcp_setback_controls'
          AND column_name IN ('source_chapter_key', 'needs_review', 'review_reason', 'reviewed_at')
        ORDER BY column_name
    """)
    cols = [r[0] for r in cur.fetchall()]
    print(f"Verified columns: {cols}")
    if len(cols) != 4:
        print("WARNING: expected 4 new columns, got", len(cols))
    cur.close()
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    conn.close()
