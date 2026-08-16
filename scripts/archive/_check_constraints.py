#!/usr/bin/env python3
"""Check constraints on dcp_setback_controls."""
import os, sys
from dotenv import load_dotenv
from pathlib import Path
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor()

cur.execute("""
    SELECT conname, pg_get_constraintdef(oid) AS def
    FROM pg_constraint
    WHERE conrelid = 'dcp_setback_controls'::regclass
""")
for r in cur.fetchall():
    print(f"{r[0]}: {r[1]}")

conn.close()
