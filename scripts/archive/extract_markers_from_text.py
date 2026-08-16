#!/usr/bin/env python3
"""
Extract C# markers from provision_text for Leichhardt provisions.
Many provisions have the marker at the start (e.g., "C3 Parking shall...")
but it wasn't captured in v2_marker.
"""
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*70)
print("EXTRACTING C# MARKERS FROM PROVISION TEXT")
print("="*70)

# Get Leichhardt provisions without markers
cur.execute("""
    SELECT id, LEFT(provision_text, 200), v2_topic
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND (v2_marker IS NULL OR v2_marker = '')
    LIMIT 50
""")

found = 0
not_found = 0
samples = []

for prov_id, text, current_topic in cur.fetchall():
    if not text:
        not_found += 1
        continue

    # Try to find C## pattern at start of text
    # Patterns: "C3", "C3.", "C3 ", "C3:", "C3-"
    match = re.match(r'^(C\d+)\s*[\.\:\-\s]', text.strip())

    if match:
        marker = match.group(1)
        found += 1
        samples.append((prov_id, marker, current_topic, text[:80]))
    else:
        not_found += 1

print(f"\nResults from 50 provisions without markers:")
print(f"  Found marker in text: {found}")
print(f"  No marker found: {not_found}")

print(f"\nSample extractions:")
for prov_id, marker, topic, text in samples[:15]:
    print(f"  ID {prov_id}: {marker:4} | topic={topic or 'None':20} | {text[:50]}...")

# Now check ALL provisions without markers
print("\n" + "="*70)
print("FULL ANALYSIS - ALL LEICHHARDT PROVISIONS WITHOUT MARKERS")
print("="*70)

cur.execute("""
    SELECT id, LEFT(provision_text, 200), v2_topic
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND (v2_marker IS NULL OR v2_marker = '')
""")

total = 0
extractable = 0
marker_counts = {}

for prov_id, text, topic in cur.fetchall():
    total += 1
    if not text:
        continue

    match = re.match(r'^(C\d+)\s*[\.\:\-\s]', text.strip())
    if match:
        extractable += 1
        marker = match.group(1)
        marker_counts[marker] = marker_counts.get(marker, 0) + 1

print(f"\nTotal without markers: {total}")
print(f"Can extract from text: {extractable} ({100*extractable//total if total else 0}%)")
print(f"Still missing: {total - extractable}")

print(f"\nMarker distribution (extracted from text):")
for marker, count in sorted(marker_counts.items(), key=lambda x: int(x[0][1:])):
    print(f"  {marker}: {count}")

conn.close()
