#!/usr/bin/env python3
"""Check why specific provisions were excluded."""
import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Get the suspicious false negatives
cur.execute("""
    SELECT id, document_id, provision_text FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND id IN (50998, 84069, 83966, 51781, 8767)
""")
rows = cur.fetchall()

# Boilerplate patterns from the classifier
BOILERPLATE_PATTERNS = [
    r'Parliamentary Counsel',
    r'compiled and maintained',
    r'NSW legislation website',
    r'Interpretation Act',
    r'section 45C',
    r'certified as the form',
    r'usually updated within \d+ working days',
    r'Historical versions',
    r'currency of this information',
    r'^[\s\.\-_]+$',
    r'^Page \d+',
    r'^\d+$',
    r'^Table of Contents?$',
    r'^Contents$',
    r'^Index$',
    r'This Policy is State Environmental Planning Policy',
    r'This Plan is .+ Local Environmental Plan',
    r'made under the Environmental Planning and Assessment Act',
    r'published on the NSW legislation website',
    r'published in .+ Gazette',
    r'^Figure \d+',
    r'^Map \d+',
    r'^Diagram',
    r'^\[Image\]',
    r'^Source:',
]

compiled = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in BOILERPLATE_PATTERNS]

print('=== CHECKING WHY THESE WERE EXCLUDED ===')
for id, doc_id, text in rows:
    print(f'\n{"="*60}')
    print(f'[{id}] {doc_id}')
    print(f'Text: {text[:300]}...')
    print(f'\nBoilerplate pattern matches:')
    matched = False
    for i, pattern in enumerate(compiled):
        if pattern.search(text):
            print(f'  - Pattern {i}: {BOILERPLATE_PATTERNS[i]}')
            matched = True
    if not matched:
        print('  - NO BOILERPLATE MATCH')
        print('  - Must have been excluded for another reason (too short? no actionable patterns?)')
        print(f'  - Text length: {len(text)} chars')

conn.close()
