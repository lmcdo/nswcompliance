#!/usr/bin/env python3
"""
Check text quality of Inner West secondary dwelling / setback provisions.
Looks for garbling indicators: spaced characters, reversed text, missing whitespace.
"""
import os, re, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

COUNCILS = ['marrickville', 'ashfield', 'leichhardt']

def garble_score(text: str) -> dict:
    """Return indicators of garbled column-layout PDF text."""
    if not text:
        return {'spaced_chars': 0, 'total_chars': 0, 'spaced_ratio': 0.0, 'verdict': 'empty'}

    # Spaced characters: single letters surrounded by spaces (e.g. "D e v e l o p m e n t")
    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    total = len(text)
    ratio = spaced / total if total > 0 else 0

    # Consecutive single-letter words (stronger signal)
    consecutive = re.findall(r'\b[A-Za-z]\b(?:\s+\b[A-Za-z]\b){3,}', text)

    if ratio > 0.05 or consecutive:
        verdict = 'GARBLED'
    elif ratio > 0.02:
        verdict = 'SUSPECT'
    else:
        verdict = 'clean'

    return {
        'spaced_ratio': round(ratio, 3),
        'spaced_char_count': spaced,
        'consecutive_single_letters': len(consecutive),
        'examples': consecutive[:2],
        'verdict': verdict,
    }

for council in COUNCILS:
    print(f"\n{'='*60}")
    print(f"Council: {council}")
    print(f"{'='*60}")

    # Get tagged secondary dwelling provisions + setback/height/residential topic provisions
    cur.execute("""
        SELECT id, ref_number, source_chapter_key, v2_topic, provision_text,
               v2_applicable_dev_types
        FROM regulatory_provisions
        WHERE source_council = %s
          AND is_current = TRUE
          AND (
              v2_applicable_dev_types @> ARRAY['secondary_dwelling']
              OR v2_topic IN ('setbacks', 'building_form', 'height', 'residential')
          )
        ORDER BY ref_number
        LIMIT 20
    """, (council,))
    rows = cur.fetchall()
    print(f"Checking {len(rows)} provisions")

    garbled_count = 0
    clean_count = 0
    for r in rows:
        score = garble_score(r['provision_text'] or '')
        status = score['verdict']
        if status == 'GARBLED':
            garbled_count += 1
        else:
            clean_count += 1
        print(f"  [{status:8}] {r['ref_number'][-60:]}")
        if status in ('GARBLED', 'SUSPECT'):
            print(f"           ratio={score['spaced_ratio']} consecutive={score['consecutive_single_letters']}")
            if score['examples']:
                print(f"           examples: {score['examples']}")

    print(f"\nSummary: {clean_count} clean, {garbled_count} garbled/suspect out of {len(rows)}")

    # Also show the full text of the most relevant secondary dwelling provision
    cur.execute("""
        SELECT ref_number, provision_text
        FROM regulatory_provisions
        WHERE source_council = %s
          AND is_current = TRUE
          AND v2_applicable_dev_types @> ARRAY['secondary_dwelling']
          AND v2_topic IN ('setbacks', 'building_form', 'residential', 'height')
        LIMIT 1
    """, (council,))
    sample = cur.fetchone()
    if sample:
        print(f"\nSample provision: {sample['ref_number']}")
        print(sample['provision_text'][:600] if sample['provision_text'] else '(empty)')

conn.close()
