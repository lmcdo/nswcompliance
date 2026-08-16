#!/usr/bin/env python3
"""Mark the 17 not-useful no-test provisions as NOT_ACTIONABLE."""
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
''', (no_test_topics,))

provisions = cur.fetchall()

# Patterns that indicate NOT useful
not_useful_patterns = [
    'section 8.7 of the environmental planning',
    'right to appeal',
    'land and environment court',
    'i. section c1',
    'ii. section c',
    'refer to table c11 laneway',
    'masterplan area is located',
    'one of sydney\'s oldest',
    'over the past few years',
    'through the draft',
    'council supported these directions',
    '9.47.1 introduction',
]

# Patterns that indicate USEFUL (override not_useful)
useful_patterns = [
    'shall',
    'must',
    'required',
    'minimum',
    'maximum',
]

not_useful_ids = []
for prov in provisions:
    text = (prov['provision_text'] or '')[:500].lower()

    is_not_useful = any(p in text for p in not_useful_patterns)
    is_useful = any(p in text for p in useful_patterns)

    if is_not_useful and not is_useful:
        not_useful_ids.append(prov['id'])

print(f"Marking {len(not_useful_ids)} as NOT_ACTIONABLE")

if not_useful_ids:
    for pid in not_useful_ids:
        cur.execute(
            "UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s",
            (pid,)
        )
    conn.commit()
    print("Done!")

cur.close()
conn.close()
