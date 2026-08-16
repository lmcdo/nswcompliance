#!/usr/bin/env python3
"""Review all 413 no-test provisions to see if they're useful or should be NOT_ACTIONABLE."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

no_test_topics = ['general', 'precinct', 'site_specific', 'biodiversity', 'environmental', 'social_impact', 'sustainability']

cur.execute('''
    SELECT id, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    AND v2_topic = ANY(%s)
    ORDER BY v2_topic, id
''', (no_test_topics,))

provisions = cur.fetchall()
print(f"Total no-test provisions: {len(provisions)}")

# Categorize
useful = []  # Actual controls
not_useful = []  # Cross-refs, descriptions, appeals, etc.

for prov in provisions:
    text = (prov['provision_text'] or '')[:500].lower()
    topic = prov['v2_topic']

    # Patterns that indicate NOT useful
    not_useful_patterns = [
        'section 8.7 of the environmental planning',  # Appeal rights
        'right to appeal',
        'land and environment court',
        'section c1',  # Cross-references
        'section c2',
        'section c3',
        'section c4',
        'within this development control plan',
        'refer to',
        'see also',
        'this section of the dcp',
        'masterplan area is located',
        'one of sydney\'s oldest',  # Historical description
        'over the past few years',
        'through the draft',
        'council supported these directions',
    ]

    # Patterns that indicate USEFUL
    useful_patterns = [
        'shall',
        'must',
        'required',
        'minimum',
        'maximum',
        'is to be',
        'are to be',
        'should be designed',
        'maintain a gap',
        'development should',
        'new development',
    ]

    is_not_useful = any(p in text for p in not_useful_patterns)
    is_useful = any(p in text for p in useful_patterns)

    if is_not_useful and not is_useful:
        not_useful.append(prov)
    else:
        useful.append(prov)

print(f"\nUSEFUL (actual controls): {len(useful)}")
print(f"NOT USEFUL (cross-refs, descriptions): {len(not_useful)}")

# Show samples
print("\n" + "="*60)
print("SAMPLE NOT USEFUL:")
for prov in not_useful[:10]:
    text = (prov['provision_text'] or '').replace('\n', ' ')[:150]
    print(f"  ID {prov['id']} ({prov['v2_topic']}): {text}...")

print("\n" + "="*60)
print("SAMPLE USEFUL:")
for prov in useful[:10]:
    text = (prov['provision_text'] or '').replace('\n', ' ')[:150]
    print(f"  ID {prov['id']} ({prov['v2_topic']}): {text}...")

# By topic
print("\n" + "="*60)
print("BY TOPIC:")
from collections import defaultdict
useful_by_topic = defaultdict(int)
not_useful_by_topic = defaultdict(int)
for p in useful:
    useful_by_topic[p['v2_topic']] += 1
for p in not_useful:
    not_useful_by_topic[p['v2_topic']] += 1

for topic in no_test_topics:
    u = useful_by_topic.get(topic, 0)
    nu = not_useful_by_topic.get(topic, 0)
    print(f"  {topic}: {u} useful, {nu} not useful")

cur.close()
conn.close()
