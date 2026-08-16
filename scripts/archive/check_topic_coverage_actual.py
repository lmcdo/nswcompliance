#!/usr/bin/env python3
"""Check actual topic coverage - how many provisions HAVE topics assigned."""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*70)
print("ACTUAL TOPIC COVERAGE - How many provisions have topics assigned?")
print("="*70)

# Count provisions WITH topics vs WITHOUT
cur.execute('''
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE v2_topic IS NOT NULL AND v2_topic != '' AND v2_topic != 'None') as has_topic,
        COUNT(*) FILTER (WHERE v2_topic IS NULL OR v2_topic = '' OR v2_topic = 'None') as no_topic
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
''')
total, has_topic, no_topic = cur.fetchone()
print(f'\nTotal actionable: {total}')
print(f'Has topic: {has_topic} ({100*has_topic//total}%)')
print(f'No topic: {no_topic} ({100*no_topic//total}%)')

# By council
print("\nBy council:")
for council in ['leichhardt', 'ashfield', 'marrickville']:
    cur.execute(f'''
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE v2_topic IS NOT NULL AND v2_topic != '' AND v2_topic != 'None') as has_topic
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND document_id ILIKE '%{council}%'
    ''')
    t, h = cur.fetchone()
    pct = 100*h//t if t else 0
    status = "✓" if pct == 100 else f"missing {t-h}"
    print(f'  {council}: {h}/{t} ({pct}%) {status}')

# Show provisions WITHOUT topics
print("\n" + "="*70)
print("PROVISIONS WITHOUT TOPICS")
print("="*70)

cur.execute('''
    SELECT id, document_id, v2_dcp_part, LEFT(provision_text, 80)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
    AND (v2_topic IS NULL OR v2_topic = '' OR v2_topic = 'None')
    LIMIT 20
''')

rows = cur.fetchall()
print(f"\nShowing first 20 of {no_topic}:")
for prov_id, doc_id, part, text in rows:
    council = 'L' if 'leichhardt' in (doc_id or '').lower() else ('A' if 'ashfield' in (doc_id or '').lower() else 'M')
    print(f"  [{council}] ID {prov_id} | {part or 'unknown':<20} | {text[:40]}...")

conn.close()
