#!/usr/bin/env python3
"""Detailed check of spaced digit artifacts in City of Sydney."""
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
    SELECT id, source_chapter_key, section_header, LENGTH(provision_text), provision_text
    FROM regulatory_provisions
    WHERE source_council = 'city_of_sydney' AND is_current = true
    ORDER BY id
""")

affected = []
for row in cur.fetchall():
    pid, chkey, header, length, text = row
    matches = spaced_re.findall(text)
    if matches:
        # Check if the provision is mostly garbled (high ratio of single chars)
        words = text.split()
        single_char_ratio = sum(1 for w in words if len(w) == 1) / max(len(words), 1)
        affected.append({
            'id': pid, 'chkey': chkey, 'header': header[:60],
            'length': length, 'match_count': len(matches),
            'single_char_ratio': single_char_ratio,
            'sample_matches': matches[:3],
        })

print(f"Total affected: {len(affected)}")
print()

# Categorize: garbled (>20% single chars) vs real provisions with occasional spaced digits
garbled = [a for a in affected if a['single_char_ratio'] > 0.20]
fixable = [a for a in affected if a['single_char_ratio'] <= 0.20]

print(f"Garbled (>20% single chars, likely map/diagram OCR): {len(garbled)}")
for a in garbled[:5]:
    print(f"  ID {a['id']} | {a['chkey']} | {a['header']} | {a['length']} chars | "
          f"single_char={a['single_char_ratio']:.0%} | matches={a['match_count']}")

print(f"\nFixable (real text with spaced digits): {len(fixable)}")
for a in fixable[:5]:
    print(f"  ID {a['id']} | {a['chkey']} | {a['header']} | {a['length']} chars | "
          f"single_char={a['single_char_ratio']:.0%} | matches: {a['sample_matches']}")

cur.close()
conn.close()
