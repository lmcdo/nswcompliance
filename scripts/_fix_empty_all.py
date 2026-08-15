#!/usr/bin/env python3
"""Deactivate all empty/near-empty 'Document Information' provisions across all councils."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Deactivate all "Document Information" provisions under 50 chars — they're cover page preamble
cur.execute("""
    UPDATE regulatory_provisions
    SET is_current = false
    WHERE is_current = true
      AND source_council IS NOT NULL
      AND section_header = 'Document Information'
      AND LENGTH(provision_text) < 50
    RETURNING source_council, id
""")
deactivated = cur.fetchall()

from collections import Counter
by_council = Counter(r[0] for r in deactivated)
print(f"Deactivated {len(deactivated)} empty preamble provisions:")
for council, count in sorted(by_council.items()):
    print(f"  {council}: {count}")

conn.commit()
cur.close()
conn.close()
