#!/usr/bin/env python3
"""Deactivate garbled OCR provisions from City of Sydney (map/diagram text)."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

spaced_re = re.compile(r'(?<!\d)(\d(?:\s\d){2,})(?!\d)')

cur.execute("""
    SELECT id, source_chapter_key, section_header, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND is_current = true
""")

garbled_ids = []
for row in cur.fetchall():
    pid, chkey, header, text = row
    if not spaced_re.search(text):
        continue
    words = text.split()
    single_char_ratio = sum(1 for w in words if len(w) == 1) / max(len(words), 1)
    if single_char_ratio > 0.20:
        garbled_ids.append(pid)

print(f"Found {len(garbled_ids)} garbled provisions to deactivate")

if garbled_ids:
    cur.execute("""
        UPDATE regulatory_provisions
        SET is_current = false
        WHERE id = ANY(%s)
        RETURNING id
    """, (garbled_ids,))
    deactivated = cur.fetchall()
    conn.commit()
    print(f"Deactivated {len(deactivated)} provisions")

cur.close()
conn.close()
