#!/usr/bin/env python3
"""Apply migration 009: add hub_expected_count to dcp_chapter_registry."""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent.parent / ".env")

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = False

sql = (Path(__file__).parent.parent / "migrations" / "009_hub_expected_count.sql").read_text()

try:
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()

    cur.execute("SELECT council, hub_expected_count FROM dcp_chapter_registry WHERE hub_expected_count IS NOT NULL ORDER BY council")
    print("Migration 009 applied. hub_expected_count values:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")
    cur.close()
except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
    raise
finally:
    conn.close()
