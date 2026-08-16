#!/usr/bin/env python3
"""Apply migration 011: create instrument_currency table."""
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = False
sql = (Path(__file__).parent.parent / "migrations" / "011_instrument_currency.sql").read_text()
try:
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    cur.execute("SELECT council, instrument_key, instrument_type, verified_at FROM instrument_currency ORDER BY instrument_type, council, instrument_key")
    print("Migration 011 applied. instrument_currency rows:")
    for r in cur.fetchall():
        status = r[3].strftime("%Y-%m-%d") if r[3] else "NULL (not yet verified)"
        print(f"  {r[0] or 'STATE'}/{r[1]} [{r[2]}] verified_at={status}")
    cur.close()
except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")
    raise
finally:
    conn.close()
