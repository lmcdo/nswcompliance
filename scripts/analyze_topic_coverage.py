#!/usr/bin/env python3
"""Analyze why topic coverage is 44.8% vs 100% for other enrichment fields"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print('\n' + '=' * 70)
print('TOPIC COVERAGE ANALYSIS')
print('=' * 70)

print('\n1. Actionable vs Non-Actionable:')
cur.execute('SELECT v2_is_actionable, COUNT(*) FROM regulatory_provisions GROUP BY v2_is_actionable ORDER BY v2_is_actionable')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]:,}')

print('\n2. Topic Coverage by Actionable Status:')
cur.execute('''
    SELECT v2_is_actionable,
           COUNT(*) FILTER (WHERE v2_topic IS NOT NULL) as with_topic,
           COUNT(*) FILTER (WHERE v2_topic IS NULL) as without_topic,
           COUNT(*) as total
    FROM regulatory_provisions
    GROUP BY v2_is_actionable
    ORDER BY v2_is_actionable
''')
for row in cur.fetchall():
    actionable = row[0]
    with_topic = row[1]
    without_topic = row[2]
    total = row[3]
    pct = (with_topic / total * 100) if total > 0 else 0
    print(f'  {actionable}: {with_topic:,} with topic ({pct:.1f}%), {without_topic:,} without')

print('\n3. Topic Coverage by Layer:')
cur.execute('''
    SELECT v2_dcp_layer,
           COUNT(*) FILTER (WHERE v2_topic IS NOT NULL) as with_topic,
           COUNT(*) FILTER (WHERE v2_topic IS NULL) as without_topic,
           COUNT(*) as total
    FROM regulatory_provisions
    GROUP BY v2_dcp_layer
    ORDER BY total DESC
''')
for row in cur.fetchall():
    layer = row[0]
    with_topic = row[1]
    without_topic = row[2]
    total = row[3]
    pct = (with_topic / total * 100) if total > 0 else 0
    print(f'  {layer}: {with_topic:,} with topic ({pct:.1f}%), {without_topic:,} without')

print('\n4. Sample provisions WITHOUT topics (first 5):')
cur.execute('''
    SELECT provision_text, v2_is_actionable, v2_dcp_layer
    FROM regulatory_provisions
    WHERE v2_topic IS NULL
    LIMIT 5
''')
for row in cur.fetchall():
    text = row[0][:150] if row[0] else 'None'
    print(f'\n  Actionable={row[1]}, Layer={row[2]}:')
    print(f'    "{text}..."')

print('\n5. Sample provisions WITH topics (first 5):')
cur.execute('''
    SELECT provision_text, v2_topic, v2_dcp_layer
    FROM regulatory_provisions
    WHERE v2_topic IS NOT NULL
    LIMIT 5
''')
for row in cur.fetchall():
    text = row[0][:150] if row[0] else 'None'
    print(f'\n  Topic={row[1]}, Layer={row[2]}:')
    print(f'    "{text}..."')

print('\n6. Most Common Topics:')
cur.execute('''
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_topic IS NOT NULL
    GROUP BY v2_topic
    ORDER BY count DESC
    LIMIT 10
''')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]:,}')

conn.close()
