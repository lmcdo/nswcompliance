#!/usr/bin/env python3
"""Check if Ashfield provisions contain PC/DS control markers that should be split on."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check the large Ashfield provisions for PC/DS markers
cur.execute("""
    SELECT id, section_header, LENGTH(provision_text) as chars, provision_text
    FROM regulatory_provisions
    WHERE is_current = true AND source_council = 'ashfield'
      AND LENGTH(provision_text) > 10000
    ORDER BY LENGTH(provision_text) DESC
    LIMIT 5
""")

for r in cur.fetchall():
    text = r[3]
    pc_matches = re.findall(r'(?m)^(PC\d+)', text)
    ds_matches = re.findall(r'(?m)^(DS\d+(?:\.\d+)?)', text)
    numbered = re.findall(r'(?m)^(\d+\.\d+)\s+([A-Z])', text)

    print(f"ID {r[0]} ({r[1]}, {r[2]} chars):")
    print(f"  PC markers: {len(pc_matches)} — {pc_matches[:10]}")
    print(f"  DS markers: {len(ds_matches)} — {ds_matches[:10]}")
    print(f"  Numbered sections: {len(numbered)} — {[n[0]+' '+n[1] for n in numbered[:5]]}")

    # What does the text structure actually look like?
    # Show lines that look like control headings
    control_lines = []
    for line in text.split('\n'):
        line = line.strip()
        if re.match(r'^(PC|DS|C|O)\d', line) or re.match(r'^\d+\.\d+\s+[A-Z]', line):
            control_lines.append(line[:80])

    print(f"  Control-like lines: {len(control_lines)}")
    for cl in control_lines[:8]:
        print(f"    {cl}")
    print()

cur.close()
conn.close()
