#!/usr/bin/env python3
"""Check existing landscaping data and control types in dcp_setback_controls."""
import os, sys
from dotenv import load_dotenv
from pathlib import Path
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor()

# Check existing landscaping rows
cur.execute("""SELECT control_type, count(*) FROM dcp_setback_controls
    WHERE control_type ILIKE '%landscape%' OR control_type ILIKE '%deep_soil%'
    GROUP BY control_type""")
rows = cur.fetchall()
print("Existing landscaping rows:", rows if rows else "NONE")

# Check what control_types exist
cur.execute("SELECT DISTINCT control_type, count(*) FROM dcp_setback_controls GROUP BY control_type ORDER BY count(*) DESC")
print("\nAll control_types:")
for r in cur.fetchall():
    print(f"  {r[0]:30s} {r[1]}")

# Check which LGAs have parking
cur.execute("SELECT lga, count(*) FROM dcp_setback_controls WHERE control_type='car_parking' AND is_current=TRUE GROUP BY lga ORDER BY lga")
print("\nLGAs with parking:")
for r in cur.fetchall():
    print(f"  {r[0]:25s} {r[1]}")

conn.close()
