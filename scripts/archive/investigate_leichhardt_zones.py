#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate Leichhardt Zone Provisions Accuracy

Objective analysis of whether zone filtering is correctly including/excluding
provisions for Leichhardt properties based on v2_applicable_zones tagging.

Questions to answer:
1. How many Leichhardt use_specific provisions exist?
2. How are they tagged with v2_applicable_zones?
3. For a specific zone (e.g., R2), what provisions SHOULD match?
4. What's the error rate (wrong inclusions/exclusions)?
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
    print("Please set DATABASE_URL or SUPABASE_DB_URL in .env file")
    sys.exit(1)

# Parse connection URL
url = urlparse(DATABASE_URL)

def connect_db():
    """Connect to database"""
    return psycopg2.connect(
        host=url.hostname,
        port=url.port or 5432,
        database=url.path[1:],  # Remove leading '/'
        user=url.username,
        password=url.password,
        cursor_factory=RealDictCursor
    )

def analyze_zone_tagging(conn):
    """Analyze zone tagging quality for Leichhardt use_specific provisions"""
    print("\n" + "=" * 80)
    print("LEICHHARDT ZONE PROVISIONS ANALYSIS")
    print("=" * 80)

    cur = conn.cursor()

    # Get all Leichhardt use_specific layer provisions
    query = """
        SELECT
            id,
            provision_text,
            v2_dcp_layer,
            v2_dcp_part,
            v2_topic,
            v2_applicable_zones,
            v2_marker,
            document_id,
            pdf_page
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
            AND v2_dcp_layer = 'use_specific'
            AND document_id ILIKE '%Leichhardt%'
            AND is_current = TRUE
        ORDER BY v2_dcp_part, id
    """

    cur.execute(query)
    provisions = cur.fetchall()

    print(f"\n📊 TOTAL LEICHHARDT USE_SPECIFIC PROVISIONS: {len(provisions)}")

    # Analyze zone tagging
    zone_tagged = [p for p in provisions if p['v2_applicable_zones']]
    zone_null = [p for p in provisions if not p['v2_applicable_zones']]
    has_all = [p for p in provisions if p['v2_applicable_zones'] and 'ALL' in p['v2_applicable_zones']]
    has_specific = [p for p in provisions if p['v2_applicable_zones'] and 'ALL' not in p['v2_applicable_zones']]

    print(f"\n🏷️  ZONE TAGGING BREAKDOWN:")
    print(f"   Tagged (has v2_applicable_zones): {len(zone_tagged)} ({len(zone_tagged)/len(provisions)*100:.1f}%)")
    print(f"   - Tagged with 'ALL': {len(has_all)} ({len(has_all)/len(provisions)*100:.1f}%)")
    print(f"   - Tagged with specific zones: {len(has_specific)} ({len(has_specific)/len(provisions)*100:.1f}%)")
    print(f"   NULL (no zones): {len(zone_null)} ({len(zone_null)/len(provisions)*100:.1f}%)")

    # Show zone distribution for specifically-tagged provisions
    if has_specific:
        zone_counts = {}
        for p in has_specific:
            for zone in p['v2_applicable_zones']:
                zone_counts[zone] = zone_counts.get(zone, 0) + 1

        print(f"\n🗂️  ZONE DISTRIBUTION (specific tags only):")
        for zone, count in sorted(zone_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {zone}: {count} provisions")

    return provisions, zone_tagged, zone_null, has_all, has_specific

def test_zone_filter_logic(provisions, test_zone='R2'):
    """Test what provisions would be included for a specific zone using API logic"""
    print(f"\n" + "=" * 80)
    print(f"ZONE FILTER LOGIC TEST FOR: {test_zone}")
    print("=" * 80)

    # API logic: (v2_applicable_zones IS NULL OR zone = ANY(zones) OR 'ALL' = ANY(zones))
    should_include = []
    should_exclude = []

    for p in provisions:
        zones = p['v2_applicable_zones']

        # Apply API filter logic
        if zones is None:
            # NULL zones = universal inclusion
            should_include.append(('NULL_UNIVERSAL', p))
        elif test_zone in zones:
            # Zone explicitly listed
            should_include.append(('ZONE_MATCH', p))
        elif 'ALL' in zones:
            # ALL tag = universal
            should_include.append(('ALL_TAG', p))
        else:
            # Zone not in list
            should_exclude.append(p)

    print(f"\n📈 FILTER RESULTS FOR ZONE {test_zone}:")
    print(f"   Should INCLUDE: {len(should_include)}")
    print(f"      - NULL (universal): {len([x for x in should_include if x[0] == 'NULL_UNIVERSAL'])}")
    print(f"      - Zone match: {len([x for x in should_include if x[0] == 'ZONE_MATCH'])}")
    print(f"      - ALL tag: {len([x for x in should_include if x[0] == 'ALL_TAG'])}")
    print(f"   Should EXCLUDE: {len(should_exclude)}")

    # Sample provisions that would be included
    print(f"\n📝 SAMPLE INCLUSIONS (first 5):")
    for i, (reason, p) in enumerate(should_include[:5], 1):
        text = p['provision_text'][:100] if p['provision_text'] else 'N/A'
        zones_str = str(p['v2_applicable_zones']) if p['v2_applicable_zones'] else 'NULL'
        print(f"\n   {i}. [{reason}] {text}...")
        print(f"      Zones: {zones_str}")
        print(f"      Part: {p['v2_dcp_part']}, Topic: {p['v2_topic']}")

    # Sample provisions that would be excluded
    if should_exclude:
        print(f"\n🚫 SAMPLE EXCLUSIONS (first 5):")
        for i, p in enumerate(should_exclude[:5], 1):
            text = p['provision_text'][:100] if p['provision_text'] else 'N/A'
            zones_str = str(p['v2_applicable_zones'])
            print(f"\n   {i}. {text}...")
            print(f"      Zones: {zones_str} (does not include {test_zone})")
            print(f"      Part: {p['v2_dcp_part']}, Topic: {p['v2_topic']}")

    return should_include, should_exclude

def identify_potential_errors(provisions, test_zone='R2'):
    """Identify provisions that may be wrongly tagged"""
    print(f"\n" + "=" * 80)
    print(f"POTENTIAL TAGGING ERRORS FOR ZONE {test_zone}")
    print("=" * 80)

    # Look for patterns that suggest wrong tagging
    suspicious = []

    for p in provisions:
        zones = p['v2_applicable_zones']
        text = (p['provision_text'] or '').lower()
        marker = (p['v2_marker'] or '').lower()

        # Heuristic 1: Generic text but specific zones (should be ALL or NULL?)
        generic_patterns = [
            'all development',
            'any development',
            'all buildings',
            'any buildings',
            'all properties',
            'any properties'
        ]

        is_generic_text = any(pattern in text for pattern in generic_patterns)
        has_specific_zones = zones and 'ALL' not in zones and len(zones) > 0

        if is_generic_text and has_specific_zones:
            suspicious.append({
                'issue': 'GENERIC_TEXT_SPECIFIC_ZONES',
                'provision': p,
                'reason': f'Text suggests universal but zones={zones}'
            })

        # Heuristic 2: Residential text but tagged for commercial zones
        residential_patterns = ['dwelling', 'residential', 'housing', 'house']
        commercial_zones = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']

        is_residential_text = any(pattern in text for pattern in residential_patterns)
        has_commercial_zones = zones and any(z in commercial_zones for z in zones)
        has_residential_zones = zones and any(z.startswith('R') for z in zones)

        if is_residential_text and has_commercial_zones and not has_residential_zones:
            suspicious.append({
                'issue': 'RESIDENTIAL_TEXT_COMMERCIAL_ZONES',
                'provision': p,
                'reason': f'Text about residential but zones={zones} (no R zones)'
            })

        # Heuristic 3: Commercial text but only residential zones
        commercial_patterns = ['shop', 'retail', 'commercial', 'business', 'office']

        is_commercial_text = any(pattern in text for pattern in commercial_patterns)
        only_residential_zones = zones and all(z.startswith('R') for z in zones)

        if is_commercial_text and only_residential_zones:
            suspicious.append({
                'issue': 'COMMERCIAL_TEXT_RESIDENTIAL_ZONES',
                'provision': p,
                'reason': f'Text about commercial but zones={zones} (only R zones)'
            })

    print(f"\n⚠️  SUSPICIOUS PROVISIONS: {len(suspicious)}")

    if suspicious:
        # Group by issue type
        by_issue = {}
        for s in suspicious:
            issue = s['issue']
            if issue not in by_issue:
                by_issue[issue] = []
            by_issue[issue].append(s)

        for issue, items in by_issue.items():
            print(f"\n   {issue}: {len(items)} provisions")
            for i, item in enumerate(items[:3], 1):  # Show first 3 of each type
                p = item['provision']
                text = p['provision_text'][:100] if p['provision_text'] else 'N/A'
                print(f"\n      {i}. {text}...")
                print(f"         {item['reason']}")
                print(f"         ID: {p['id']}, Part: {p['v2_dcp_part']}")
    else:
        print("   ✅ No obvious tagging errors detected by heuristics")

    return suspicious

def main():
    """Run investigation"""
    conn = connect_db()

    try:
        # Step 1: Analyze overall zone tagging
        provisions, zone_tagged, zone_null, has_all, has_specific = analyze_zone_tagging(conn)

        # Step 2: Test filter logic for R2 zone
        should_include, should_exclude = test_zone_filter_logic(provisions, 'R2')

        # Step 3: Identify potential errors
        suspicious = identify_potential_errors(provisions, 'R2')

        # Step 4: Calculate objective error rate
        print(f"\n" + "=" * 80)
        print("ERROR RATE ANALYSIS")
        print("=" * 80)

        # NULL zones = problem if they shouldn't be universal
        null_pct = len(zone_null) / len(provisions) * 100

        # Suspicious provisions / total provisions
        error_pct = len(suspicious) / len(provisions) * 100

        print(f"\n📊 QUALITY METRICS:")
        print(f"   NULL zones (universal treatment): {len(zone_null)}/{len(provisions)} ({null_pct:.1f}%)")
        print(f"   Suspicious provisions (heuristic): {len(suspicious)}/{len(provisions)} ({error_pct:.1f}%)")
        print(f"   Specifically zone-tagged: {len(has_specific)}/{len(provisions)} ({len(has_specific)/len(provisions)*100:.1f}%)")

        if null_pct > 50:
            print(f"\n⚠️  HIGH NULL RATE: {null_pct:.1f}% of provisions have NULL zones")
            print("   These provisions will be included for ALL zones (universal)")
            print("   This may be the source of the '70% wrong' issue")

        if error_pct > 10:
            print(f"\n⚠️  HIGH SUSPICIOUS RATE: {error_pct:.1f}% flagged by heuristics")
            print("   These provisions may be incorrectly tagged")

        print(f"\n" + "=" * 80)
        print("INVESTIGATION COMPLETE")
        print("=" * 80)

    finally:
        conn.close()

if __name__ == '__main__':
    main()
