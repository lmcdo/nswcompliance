#!/usr/bin/env python3
"""Check marker patterns in oversized Ashfield provisions."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Get the biggest Ashfield provisions
cur.execute('''
    SELECT id, section_header, source_chapter_key,
           LENGTH(provision_text) as chars, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ashfield' AND is_current = true
    ORDER BY LENGTH(provision_text) DESC
    LIMIT 8
''')

for row in cur.fetchall():
    pid, header, chkey, chars, text = row
    print(f"ID={pid} | chapter={chkey} | header={header[:60]} | {chars:,} chars")

    # Find marker patterns at start of lines
    pc_markers = re.findall(r'(?m)^(PC\s*\d+(?:\.\d+)?)\b', text)
    ds_markers = re.findall(r'(?m)^(DS\s*\d+(?:\.\d+)?)\b', text)
    o_markers = re.findall(r'(?m)^(O\d+)\b', text)
    c_markers = re.findall(r'(?m)^(C\d+)\b', text)

    print(f"  PC: {len(pc_markers)} — {pc_markers[:5]}")
    print(f"  DS: {len(ds_markers)} — {ds_markers[:5]}")
    print(f"  O:  {len(o_markers)} — {o_markers[:5]}")
    print(f"  C:  {len(c_markers)} — {c_markers[:5]}")

    # Show a sample of actual marker lines (first 3)
    all_markers = re.findall(r'(?m)^((?:PC|DS|O|C)\s*\d+(?:\.\d+)?)\s+(.{0,80})', text)
    for m in all_markers[:4]:
        print(f"  >> {m[0]}: {m[1]}")
    print()

cur.close()
conn.close()
