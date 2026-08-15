#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep audit: Compare layer breakdown vs assessment scope
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

print("=" * 80)
print("DEEP AUDIT: LAYER BREAKDOWN VS ASSESSMENT SCOPE")
print("=" * 80)

# 1. Raw layer breakdown (all controls, no objectives/descriptives)
print("\n1. RAW LAYER BREAKDOWN (all controls, no hidden):")
cur.execute("""
SELECT
  v2_dcp_layer,
  COUNT(*) as cnt
FROM regulatory_provisions
WHERE source_council = 'marrickville'
  AND v2_provision_type = 'control'
  AND v2_heritage_type IS DISTINCT FROM 'descriptive'
GROUP BY v2_dcp_layer
ORDER BY v2_dcp_layer
""")

layer_breakdown = {}
raw_total = 0
for row in cur.fetchall():
    layer = row['v2_dcp_layer'] or 'NULL'
    count = row['cnt']
    layer_breakdown[layer] = count
    raw_total += count
    print(f"   {layer:<20} {count:>4}")
print(f"   {'='*20} {raw_total:>4}")

# 2. After hiding objectives/descriptives
print("\n2. AFTER HIDING OBJECTIVES/DESCRIPTIVES:")
cur.execute("""
SELECT
  v2_dcp_layer,
  COUNT(*) as cnt
FROM regulatory_provisions
WHERE source_council = 'marrickville'
  AND v2_provision_type = 'control'
  AND v2_heritage_type IS DISTINCT FROM 'descriptive'
  AND v2_provision_type != 'objective'
GROUP BY v2_dcp_layer
ORDER BY v2_dcp_layer
""")

hidden_total = 0
for row in cur.fetchall():
    layer = row['v2_dcp_layer'] or 'NULL'
    count = row['cnt']
    hidden_total += count
    print(f"   {layer:<20} {count:>4}")
print(f"   {'='*20} {hidden_total:>4}")

# 3. Summary
print("\n3. SUMMARY:")
print(f"   Raw total:        {raw_total}")
print(f"   After hiding:     {hidden_total}")
print(f"   UI shows (185):   185")
print(f"   UI shows (363):   363")
print(f"\n   Layer breakdown math (generic + use_specific + condition + precinct):")

generic = layer_breakdown.get('generic', 0)
use_specific = layer_breakdown.get('use_specific', 0)
condition = layer_breakdown.get('condition', 0)
precinct = layer_breakdown.get('precinct', 0)

print(f"   {generic} + {use_specific} + {condition} + {precinct} = {generic + use_specific + condition + precinct}")

print(f"\n   If UI 185 = layer breakdown sum, then:")
print(f"   363 - 185 = {363 - 185} provisions unaccounted for")

cur.close()
conn.close()
