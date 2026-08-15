#!/usr/bin/env python3
"""Apply migration 010: create instrument_registry table."""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = False
sql = (Path(__file__).parent.parent / "migrations" / "010_instrument_registry.sql").read_text()
try:
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.execute("SELECT instrument_type, instrument_key, instrument_label FROM instrument_registry ORDER BY instrument_type, instrument_key")
    print("Migration 010 applied. instrument_registry rows:")
    for r in cur.fetchall():
        print(f"  [{r[0]}] {r[1]} — {r[2]}")
    cur.close()
except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
    raise
finally:
    conn.close()
