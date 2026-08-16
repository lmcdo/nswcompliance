#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulate the exact API query logic from route.ts to understand the 834 vs 2,990 discrepancy.

API logic (from route.ts lines 635-862):
1. Query Layer 1 (generic): v2_dcp_layer = 'generic'
2. Query Layer 2 (use_specific): v2_dcp_layer = 'use_specific' + zone filter
3. Query Layer 3 (condition): v2_dcp_layer = 'condition' + heritage/flood filter
4. Query Layer 4 (precinct): v2_dcp_layer = 'precinct' + precinct_id filter
"""

import os, sys, io, psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')
url = urlparse(DATABASE_URL)

conn = psycopg2.connect(
    host=url.hostname, port=url.port or 5432,
    database=url.path[1:], user=url.username, password=url.password
)
cur = conn.cursor()

print("\n" + "=" * 80)
print("SIMULATING API QUERY FOR LEICHHARDT R2")
print("=" * 80)

# Test case: Leichhardt, zone=R2, former_council=leichhardt, no heritage, no flood, no precinct
zone = 'R2'
former_council = 'leichhardt'
heritage = False
flood = False
precinct_id = None

# Base conditions (applied to all queries)
base_where = """
    WHERE v2_is_actionable = true
      AND document_id ILIKE '%Leichhardt%'
      AND is_current = TRUE
"""

# Layer 1: Generic (always include)
print("\n1. LAYER 1: GENERIC")
print("   SQL: v2_dcp_layer = 'generic'")
cur.execute(f"""
    SELECT COUNT(*)
    FROM regulatory_provisions
    {base_where}
      AND v2_dcp_layer = 'generic'
""")
layer1_count = cur.fetchone()[0]
print(f"   Result: {layer1_count:,} provisions")

# Layer 2: Use-specific (zone-filtered)
print("\n2. LAYER 2: USE_SPECIFIC")
print(f"   SQL: v2_dcp_layer = 'use_specific'")
print(f"   Zone filter: (zones IS NULL OR '{zone}' = ANY(zones) OR 'ALL' = ANY(zones))")
print(f"   Heritage filter: NOT heritage (exclude heritage provisions)")

# Check WITHOUT heritage filter first
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id ILIKE %s
      AND is_current = TRUE
      AND v2_dcp_layer = 'use_specific'
      AND (v2_applicable_zones IS NULL OR %s = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))
""", ('%Leichhardt%', zone))
layer2_without_heritage_filter = cur.fetchone()[0]
print(f"   Without heritage filter: {layer2_without_heritage_filter:,}")

# With heritage filter (from line 764-766)
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id ILIKE %s
      AND is_current = TRUE
      AND v2_dcp_layer = 'use_specific'
      AND (v2_applicable_zones IS NULL OR %s = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))
      AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))
""", ('%Leichhardt%', zone))
layer2_count = cur.fetchone()[0]
print(f"   With heritage filter: {layer2_count:,}")

# Layer 3: Condition (heritage/flood filtered)
print("\n3. LAYER 3: CONDITION")
print(f"   Heritage: {heritage}, Flood: {flood}")
if not heritage and not flood:
    print("   Result: 0 (no conditions apply)")
    layer3_count = 0
else:
    cur.execute(f"""
        SELECT COUNT(*)
        FROM regulatory_provisions
        {base_where}
          AND v2_dcp_layer = 'condition'
    """)
    layer3_count = cur.fetchone()[0]
    print(f"   Result: {layer3_count:,} provisions")

# Layer 4: Precinct (location-filtered)
print("\n4. LAYER 4: PRECINCT")
if precinct_id:
    print(f"   Precinct filter: v2_precinct_id = '{precinct_id}'")
    cur.execute(f"""
        SELECT COUNT(*)
        FROM regulatory_provisions
        {base_where}
          AND v2_dcp_layer = 'precinct'
          AND v2_precinct_id = %s
    """, (precinct_id,))
    layer4_count = cur.fetchone()[0]
else:
    print("   No precinct_id provided - excluding ALL precinct provisions")
    print("   SQL: v2_precinct_id IS NULL")
    # API line 815: AND v2_precinct_id IS NULL
    cur.execute(f"""
        SELECT COUNT(*)
        FROM regulatory_provisions
        {base_where}
          AND v2_dcp_layer = 'precinct'
          AND v2_precinct_id IS NULL
    """)
    layer4_count = cur.fetchone()[0]
    # Also applies heritage filter if not heritage (lines 818-820)
    if not heritage:
        cur.execute(f"""
            SELECT COUNT(*)
            FROM regulatory_provisions
            {base_where}
              AND v2_dcp_layer = 'precinct'
              AND v2_precinct_id IS NULL
              AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))
        """)
        layer4_count = cur.fetchone()[0]

print(f"   Result: {layer4_count:,} provisions")

# Total
print("\n" + "=" * 80)
print("TOTAL PROVISIONS")
print("=" * 80)

total = layer1_count + layer2_count + layer3_count + layer4_count
print(f"\n Layer 1 (generic):       {layer1_count:,}")
print(f" Layer 2 (use_specific):  {layer2_count:,}")
print(f" Layer 3 (condition):     {layer3_count:,}")
print(f" Layer 4 (precinct):      {layer4_count:,}")
print(f" " + "-" * 40)
print(f" TOTAL:                   {total:,}")

print(f"\n Database has:            {layer1_count + layer2_without_heritage_filter + 0 + 660:,} (without API filters)")
print(f" API returns:             {total:,} (with API filters)")
print(f" Difference:              {(layer1_count + layer2_without_heritage_filter + 0 + 660) - total:,}")

# Analyze what's being filtered out
print("\n" + "=" * 80)
print("WHAT'S BEING FILTERED OUT?")
print("=" * 80)

# Precinct provisions excluded because no precinct_id
precinct_excluded = 660 - layer4_count
print(f"\n Precinct provisions (no precinct_id):  {precinct_excluded:,}")

# Heritage provisions excluded from use_specific layer
heritage_excluded_layer2 = layer2_without_heritage_filter - layer2_count
print(f" Heritage provisions (use_specific):     {heritage_excluded_layer2:,}")

# Condition layer (heritage/flood) - all excluded
print(f" Condition layer (no heritage/flood):   0")

total_excluded = precinct_excluded + heritage_excluded_layer2
print(f" " + "-" * 50)
print(f" TOTAL EXCLUDED:                         {total_excluded:,}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

print(f"\n The API is correctly filtering provisions based on property attributes:")
print(f" - No precinct_id: Excludes {precinct_excluded:,} precinct-specific provisions")
print(f" - Not heritage: Excludes {heritage_excluded_layer2:,} heritage provisions")
print(f"\n This is CORRECT BEHAVIOR - provisions should only show for relevant properties")

if total < 1000:
    print(f"\n [!] HOWEVER: API returned {total:,} provisions")
    print("   This seems low for a typical property query")
    print("\n   Expected behavior:")
    print("   - Generic layer: Always included (~2,309 provisions)")
    print("   - Use-specific: Zone-filtered (~20 provisions for R2)")
    print("   - Condition: Only if heritage/flood (0 in this case)")
    print("   - Precinct: Only if precinct_id provided (0 in this case)")
    print(f"\n   Expected total: ~2,329 provisions")
    print(f"   Actual total: {total:,} provisions")
    print(f"   MISSING: {2329 - total:,} provisions")

conn.close()
