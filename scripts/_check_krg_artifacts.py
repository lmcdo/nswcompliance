#!/usr/bin/env python3
"""Audit reversed OCR artifacts in Ku-ring-gai provisions."""
import os, sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Reversed sidebar labels found in the PDF
REVERSED_PATTERNS = [
    r'NOISIVIDBUS',   # SUBDIVISION
    r'GNIKRAP',       # PARKING
    r'NGISED',        # DESIGN
    r'NOITADILOSNOC', # CONSOLIDATION
    r'SSECCA',        # ACCESS
]

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT id, source_chapter_key, section_header, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ku_ring_gai' AND is_current = true
""")
rows = cur.fetchall()
print(f"Total active KRG provisions: {len(rows)}")

combined_pattern = re.compile('|'.join(REVERSED_PATTERNS))
affected = [(r[0], r[1], r[2], r[3]) for r in rows if combined_pattern.search(r[3] or '')]

print(f"Provisions with reversed OCR sidebar text: {len(affected)}")
print()
for pid, chapter, header, text in affected[:5]:
    print(f"  id={pid} chapter={chapter}")
    print(f"  header={header}")
    # Show just the reversed bits
    matches = combined_pattern.findall(text)
    print(f"  patterns found: {set(matches)}")
    print()

cur.close()
conn.close()
