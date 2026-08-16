#!/usr/bin/env python3
"""Deactivate all 58 empty 'Document Information' provisions from Marrickville."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# All 58 are empty "Document Information" preamble — 0 chars, no value
cur.execute("""
    UPDATE regulatory_provisions
    SET is_current = false
    WHERE is_current = true
      AND source_council = 'marrickville'
      AND section_header = 'Document Information'
      AND LENGTH(provision_text) = 0
    RETURNING id
""")
deactivated = cur.fetchall()
print(f"Deactivated {len(deactivated)} empty 'Document Information' provisions")

# Verify
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE is_current = true AND source_council = 'marrickville'
""")
remaining = cur.fetchone()[0]
print(f"Marrickville now has {remaining} active provisions")

conn.commit()
cur.close()
conn.close()
