#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Leichhardt Layer Assignment

The previous investigation found ALL 21 use_specific provisions are tagged with 'ALL' zones.
This script investigates whether:
1. These provisions are correctly assigned to use_specific layer (should they be generic?)
2. Whether provisions that SHOULD be zone-specific are missing specific zone tags
3. What the overall layer distribution looks like for Leichhardt
"""

import os
import sys
import io
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import RealDictCursor

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Get database connection from environment
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('SUPABASE_DB_URL')
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found in environment")
    sys.exit(1)

# Parse connection URL
url = urlparse(DATABASE_URL)

def connect_db():
    """Connect to database"""
    return psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        database=url.path[1:],
        user=url.username,
        password=url.password,
        cursor_factory=RealDictCursor
    )

def analyze_layer_distribution(conn):
    """Get layer distribution for Leichhardt"""
    print("\n" + "=" * 80)
    print("LEICHHARDT LAYER DISTRIBUTION")
    print("=" * 80)

    cur = conn.cursor()

    query = """
        SELECT
            v2_dcp_layer,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
            AND document_id ILIKE '%Leichhardt%'
            AND is_current = TRUE
        GROUP BY v2_dcp_layer
        ORDER BY count DESC
    """

    cur.execute(query)
    layers = cur.fetchall()

    print("\n Layer Distribution:")
    for layer in layers:
        print(f"   {layer['v2_dcp_layer']:20s} {layer['count']:5d} ({layer['percentage']}%)")

    total = sum(l['count'] for l in layers)
    print(f"   {'TOTAL':20s} {total:5d}")

    return layers

def examine_use_specific_provisions(conn):
    """Examine the 21 use_specific provisions in detail"""
    print("\n" + "=" * 80)
    print("EXAMINING USE_SPECIFIC PROVISIONS (Should these really be use_specific?)")
    print("=" * 80)

    cur = conn.cursor()

    query = """
        SELECT
            id,
            provision_text,
            v2_dcp_part,
            v2_topic,
            v2_marker,
            v2_applicable_zones,
            v2_provision_type,
            pdf_page,
            document_id
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
            AND v2_dcp_layer = 'use_specific'
            AND document_id ILIKE '%Leichhardt%'
            AND is_current = TRUE
        ORDER BY v2_dcp_part, pdf_page, id
        LIMIT 50
    """

    cur.execute(query)
    provisions = cur.fetchall()

    print(f"\n Found {len(provisions)} use_specific provisions")
    print("\n Analyzing content patterns...")

    # Look for patterns that suggest correct/incorrect layer assignment
    patterns = {
        'zone_mentioned': 0,  # Mentions specific zones (R1, R2, B1, etc.)
        'use_mentioned': 0,   # Mentions specific uses (dwelling, retail, etc.)
        'generic_language': 0,  # Generic language (all development, any building)
        'food_related': 0,     # Food/community gardens
    }

    zone_codes = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'IN1', 'IN2']

    for p in provisions:
        text = (p['provision_text'] or '').lower()

        # Check for zone mentions
        if any(code.lower() in text for code in zone_codes):
            patterns['zone_mentioned'] += 1

        # Check for use mentions
        use_terms = ['dwelling', 'residential', 'commercial', 'retail', 'industrial', 'shop', 'office']
        if any(term in text for term in use_terms):
            patterns['use_mentioned'] += 1

        # Check for generic language
        generic_terms = ['all development', 'any development', 'all buildings', 'any property']
        if any(term in text for term in generic_terms):
            patterns['generic_language'] += 1

        # Check food related
        if 'food' in text or 'garden' in text or 'plot' in text:
            patterns['food_related'] += 1

    print(f"\n Content Pattern Analysis:")
    print(f"   Mentions zone codes: {patterns['zone_mentioned']} ({patterns['zone_mentioned']/len(provisions)*100:.1f}%)")
    print(f"   Mentions specific uses: {patterns['use_mentioned']} ({patterns['use_mentioned']/len(provisions)*100:.1f}%)")
    print(f"   Generic language: {patterns['generic_language']} ({patterns['generic_language']/len(provisions)*100:.1f}%)")
    print(f"   Food/garden related: {patterns['food_related']} ({patterns['food_related']/len(provisions)*100:.1f}%)")

    # Show actual examples
    print(f"\n FULL PROVISION DETAILS (all {len(provisions)}):")
    for i, p in enumerate(provisions, 1):
        print(f"\n {i}. ID: {p['id']}")
        print(f"    Part: {p['v2_dcp_part']}, Topic: {p['v2_topic']}, Marker: {p['v2_marker']}")
        print(f"    Zones: {p['v2_applicable_zones']}")
        print(f"    Type: {p['v2_provision_type']}")
        print(f"    Text: {(p['provision_text'] or '')[:200]}...")
        print(f"    Document: {p['document_id']}, Page: {p['pdf_page']}")

    return provisions, patterns

def compare_with_generic_layer(conn):
    """Compare use_specific with generic layer for Leichhardt"""
    print("\n" + "=" * 80)
    print("COMPARISON: GENERIC vs USE_SPECIFIC LAYERS")
    print("=" * 80)

    cur = conn.cursor()

    # Get generic provisions count
    cur.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
            AND v2_dcp_layer = 'generic'
            AND document_id ILIKE '%Leichhardt%'
            AND is_current = TRUE
    """)
    generic_count = cur.fetchone()['count']

    # Get use_specific provisions count
    cur.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
            AND v2_dcp_layer = 'use_specific'
            AND document_id ILIKE '%Leichhardt%'
            AND is_current = TRUE
    """)
    use_specific_count = cur.fetchone()['count']

    print(f"\n Layer Sizes:")
    print(f"   Generic layer: {generic_count} provisions")
    print(f"   Use-specific layer: {use_specific_count} provisions")
    print(f"   Ratio: {generic_count/use_specific_count if use_specific_count > 0 else 0:.1f}:1")

    if use_specific_count < generic_count * 0.1:
        print(f"\n [!] Use-specific layer is very small compared to generic layer")
        print(f"     This suggests most provisions are correctly identified as generic")
        print(f"     BUT the {use_specific_count} use_specific provisions should have zone tags")

def main():
    """Run analysis"""
    conn = connect_db()

    try:
        # Step 1: Overall layer distribution
        layers = analyze_layer_distribution(conn)

        # Step 2: Examine use_specific provisions in detail
        provisions, patterns = examine_use_specific_provisions(conn)

        # Step 3: Compare with generic layer
        compare_with_generic_layer(conn)

        # Step 4: Final assessment
        print("\n" + "=" * 80)
        print("ASSESSMENT")
        print("=" * 80)

        print("\n Key Findings:")
        print(f"   1. All {len(provisions)} use_specific provisions tagged with 'ALL' zones")
        print(f"   2. {patterns['food_related']} provisions ({patterns['food_related']/len(provisions)*100:.1f}%) are food/garden related")
        print(f"   3. {patterns['generic_language']} provisions ({patterns['generic_language']/len(provisions)*100:.1f}%) use generic language")

        print("\n Possible Issues:")
        if patterns['food_related'] == len(provisions):
            print("   [MAJOR] ALL provisions are Part F (Food) - these may be miscategorized")
            print("   [ISSUE] Part F provisions may not be use_specific at all")
            print("   [FIX] These should likely be in 'generic' layer, not 'use_specific'")
        elif patterns['generic_language'] > len(provisions) * 0.5:
            print("   [WARNING] >50% use generic language - should these be in generic layer?")

        if all(p['v2_applicable_zones'] == ['ALL'] for p in provisions):
            print("   [MAJOR] Zero zone-specific tagging in use_specific layer")
            print("   [RESULT] API filter '(zones IS NULL OR zone = ANY(zones) OR 'ALL' = ANY(zones))'")
            print("            will include ALL 21 provisions for EVERY zone query")
            print("   [IMPACT] No zone differentiation happening in Leichhardt")

        print("\n Recommended Actions:")
        print("   1. Review Part F provisions - should they be 'generic' not 'use_specific'?")
        print("   2. If they should be use_specific, identify which zones they apply to")
        print("   3. Re-run enrichment scripts to fix v2_applicable_zones tagging")

        print("\n" + "=" * 80)

    finally:
        conn.close()

if __name__ == '__main__':
    main()
