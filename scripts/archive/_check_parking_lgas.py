#!/usr/bin/env python3
"""Quick check: which LGAs have parking data."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor()
cur.execute("""
    SELECT lga, count(*)
    FROM dcp_setback_controls
    WHERE control_type = 'car_parking' AND is_current = TRUE
    GROUP BY lga ORDER BY lga
""")
rows = cur.fetchall()
print(f"\n{len(rows)} LGAs with parking data ({sum(r[1] for r in rows)} total rows):\n")
for lga, cnt in rows:
    print(f"  {lga}: {cnt} rows")

# Check Inner West (Leichhardt, Ashfield, Marrickville)
cur.execute("""
    SELECT lga, count(*)
    FROM dcp_setback_controls
    WHERE control_type = 'car_parking' AND is_current = TRUE
    AND lga IN ('inner_west', 'leichhardt', 'ashfield', 'marrickville')
    GROUP BY lga
""")
iw = cur.fetchall()
if iw:
    print(f"\nInner West sub-councils: {iw}")
else:
    print("\nNo Inner West parking rows yet")

conn.close()
