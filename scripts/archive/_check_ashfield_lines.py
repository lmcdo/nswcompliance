#!/usr/bin/env python3
"""Check actual line structure around markers in Ashfield provisions."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check Parking (PC/DS pattern) and Heritage (O/C pattern)
for pid, label in [(91928, "Parking"), (91988, "Heritage-Objectives"), (91961, "Hurlstone Park")]:
    cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (pid,))
    text = cur.fetchone()[0]
    lines = text.split('\n')

    print(f"=== {label} (ID {pid}) — {len(lines)} lines ===")
    # Show lines around first few markers
    marker_re = re.compile(r'^((?:PC|DS|O|C)\d+(?:\.\d+)?)\b')
    shown = 0
    for i, line in enumerate(lines):
        m = marker_re.match(line)
        if m and shown < 6:
            # Show this line and next 2
            print(f"  L{i}: {line[:120]}")
            if i+1 < len(lines):
                print(f"  L{i+1}: {lines[i+1][:120]}")
            print()
            shown += 1
    print()

cur.close()
conn.close()
