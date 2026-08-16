#!/usr/bin/env python3
"""
Analyze document_id patterns to understand section structure.
The document_id often contains section info we can use for topic mapping.
"""
import os
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*70)
print("ANALYZING DOCUMENT_ID PATTERNS FOR TOPIC EXTRACTION")
print("="*70)

# Leichhardt analysis
print("\n\nLEICHHARDT DOCUMENT_ID PATTERNS:")
print("-"*70)

cur.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    ORDER BY document_id
    LIMIT 50
""")

leichhardt_patterns = defaultdict(int)
for (doc_id,) in cur.fetchall():
    # Extract C# pattern
    c_match = re.search(r'_C(\d+)_', doc_id)
    section_match = re.search(r'Section_(\d+)', doc_id)

    if c_match:
        leichhardt_patterns[f'C{c_match.group(1)}'] += 1
    elif section_match:
        leichhardt_patterns[f'Section_{section_match.group(1)}'] += 1
    else:
        leichhardt_patterns['other'] += 1

    print(f"  {doc_id[:80]}")

print(f"\nPatterns found: {dict(leichhardt_patterns)}")

# Check how many have C# in document_id vs marker
print("\n\nLEICHHARDT: C# EXTRACTION FROM DOCUMENT_ID")
print("-"*70)

cur.execute("""
    SELECT
        document_id,
        v2_marker,
        v2_topic
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND (v2_marker IS NULL OR v2_marker = '')
    LIMIT 20
""")

print("Provisions WITHOUT v2_marker - can we extract from document_id?")
for doc_id, marker, topic in cur.fetchall():
    c_match = re.search(r'_C(\d+)_', doc_id or '')
    extracted = f"C{c_match.group(1)}" if c_match else "NO MATCH"
    print(f"  {extracted:10} | topic={topic:20} | {doc_id[:60] if doc_id else 'None'}...")

# Marrickville analysis
print("\n\nMARRICKVILLE DOCUMENT_ID PATTERNS:")
print("-"*70)

cur.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id ILIKE '%marrickville%'
    AND v2_is_actionable = true
    ORDER BY document_id
    LIMIT 30
""")

for (doc_id,) in cur.fetchall():
    # Extract section pattern like 2_10
    section_match = re.search(r'[_-]+2[_-]+(\d+)[_-]', doc_id or '')
    if section_match:
        section = f"2.{section_match.group(1)}"
    else:
        section = "?"
    print(f"  {section:6} | {doc_id[:70]}")

conn.close()
