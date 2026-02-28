#!/usr/bin/env python3
"""Run migration 007: dcp_chapter_registry table creation."""
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

sql_path = Path(__file__).parent.parent / "migrations" / "007_dcp_chapter_registry.sql"
sql = sql_path.read_text(encoding="utf-8")

print(f"Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    cur.execute(sql)
    conn.commit()
    print("Migration 007 applied successfully.")
    print("Table dcp_chapter_registry created (or already exists).")
except Exception as e:
    conn.rollback()
    print(f"ERROR: {e}")
    sys.exit(1)
finally:
    cur.close()
    conn.close()
