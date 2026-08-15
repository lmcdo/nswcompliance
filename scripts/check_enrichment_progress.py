#!/usr/bin/env python3
import psycopg2, os
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print('Enrichment Progress Check')
print('=' * 60)

# Check layer distribution
cur.execute('SELECT v2_dcp_layer, COUNT(*) FROM regulatory_provisions GROUP BY v2_dcp_layer ORDER BY COUNT(*) DESC')
print('\nLayer distribution:')
for row in cur.fetchall():
    layer = row[0] or 'NULL'
    print(f'  {layer}: {row[1]}')

# Check topic coverage
cur.execute('SELECT COUNT(*) FILTER (WHERE v2_topic IS NOT NULL) as has_topic, COUNT(*) as total FROM regulatory_provisions')
result = cur.fetchone()
print(f'\nTopic: {result[0]} / {result[1]} ({100*result[0]/result[1]:.1f}%)')

# Check zone coverage
cur.execute('SELECT COUNT(*) FILTER (WHERE v2_applicable_zones IS NOT NULL) as has_zones, COUNT(*) as total FROM regulatory_provisions')
result = cur.fetchone()
print(f'Zones: {result[0]} / {result[1]} ({100*result[0]/result[1]:.1f}%)')

# Check dev_type coverage
cur.execute('SELECT COUNT(*) FILTER (WHERE v2_applicable_dev_types IS NOT NULL) as has_dev, COUNT(*) as total FROM regulatory_provisions')
result = cur.fetchone()
print(f'Dev-types: {result[0]} / {result[1]} ({100*result[0]/result[1]:.1f}%)')

conn.close()
