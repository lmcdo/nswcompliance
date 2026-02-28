#!/usr/bin/env python3
"""Run migration 008: extraction pipeline columns."""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

sql_path = Path(__file__).parent.parent / "migrations" / "008_extraction_columns.sql"
sql = sql_path.read_text(encoding="utf-8")

print("Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    cur.execute(sql)
    conn.commit()
    print("Migration 008 applied successfully.")
    print("New columns: regulatory_provisions.source_chapter_key, source_council, is_current")
    print("New columns: dcp_chapter_registry.last_extracted_at, last_extracted_version")
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    cur.close()
    conn.close()
