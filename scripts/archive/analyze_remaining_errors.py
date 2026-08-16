#!/usr/bin/env python3
"""
Analyze remaining errors to find fixable patterns.
Goal: Get from 93% to 98-100% accuracy.
"""

import os
import re
import sys
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

# Fix Windows encoding
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback', 'height': r'\bheight', 'parking': r'\bparking',
    'solar': r'\bsolar', 'privacy': r'\bprivacy', 'landscaping': r'\blandscap',
    'heritage': r'\bheritage', 'trees': r'\btree', 'fencing': r'\bfenc',
    'access': r'\baccess', 'stormwater': r'\bstormwater', 'waste': r'\bwaste',
    'signage': r'\bsign', 'building_form': r'\bbulk|scale|massing',
    'building_design': r'\bdesign|facade', 'open_space': r'\bopen\s+space',
    'flooding': r'\bflood', 'contamination': r'\bcontaminat', 'safety': r'\bsafety',
    'residential': r'\bresidential', 'commercial': r'\bcommercial',
    'precinct': r'\bprecinct', 'general': r'\bobjective', 'energy': r'\benergy',
    'water': r'\bwater', 'environmental': r'\benvironmental',
}


def get_keyword_matches(text):
    if not text:
        return {}
    matches = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        if found:
            matches[topic] = len(found)
    return matches


def analyze_council(conn, council_name):
    print("\n" + "=" * 80)
    print(f"{council_name.upper()} - REMAINING ERRORS ANALYSIS")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
        """, (f'%{council_name}%',))
        provisions = cur.fetchall()

    # Categorize
    wrong_topic = []
    no_keywords = []

    for p in provisions:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']
        part = p['v2_dcp_part'] or ''

        # Skip C markers and part defaults
        if re.match(r'^C\d+', text.strip()):
            continue
        if part == 'Chapter E1' and assigned == 'heritage':
            continue

        matches = get_keyword_matches(text)

        if assigned in matches:
            continue  # Keyword match - good
        elif not matches:
            no_keywords.append(p)
        else:
            wrong_topic.append({**p, 'matches': matches})

    # Analyze WRONG TOPIC patterns
    print(f"\n--- WRONG TOPIC: {len(wrong_topic)} provisions ---")

    # Group by assigned topic -> found topics
    transitions = defaultdict(list)
    for p in wrong_topic:
        assigned = p['v2_topic']
        found = list(p['matches'].keys())
        transitions[assigned].append({'prov': p, 'found': found})

    print("\nBy assigned topic (showing fixable):")
    for assigned, items in sorted(transitions.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"\n  {assigned}: {len(items)} provisions")
        # Show top found topics
        found_counts = defaultdict(int)
        for item in items:
            for f in item['found']:
                found_counts[f] += 1
        top_found = sorted(found_counts.items(), key=lambda x: -x[1])[:3]
        print(f"    Top keywords found: {top_found}")

    # Analyze NO KEYWORDS patterns
    print(f"\n--- NO KEYWORDS: {len(no_keywords)} provisions ---")

    # Group by assigned topic
    by_topic = defaultdict(list)
    for p in no_keywords:
        by_topic[p['v2_topic']].append(p)

    print("\nBy assigned topic:")
    for topic, items in sorted(by_topic.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {topic}: {len(items)}")

    # Identify fixable patterns
    print(f"\n--- FIXABLE PATTERNS ---")

    # Pattern 1: Short provisions (likely headers/markers)
    short_no_kw = [p for p in no_keywords if len(p['provision_text'] or '') < 50]
    print(f"\n  Short provisions (<50 chars): {len(short_no_kw)}")

    # Pattern 2: Wrong topic with strong mismatch (3+ keywords for different topic)
    strong_mismatch = []
    for p in wrong_topic:
        max_found = max(p['matches'].values()) if p['matches'] else 0
        if max_found >= 3:
            best = max(p['matches'].items(), key=lambda x: x[1])
            strong_mismatch.append({**p, 'best': best})

    print(f"  Strong mismatches (3+ keywords): {len(strong_mismatch)}")

    # Pattern 3: waste_management vs waste mismatch
    waste_mgmt = [p for p in wrong_topic if p['v2_topic'] == 'waste_management' and 'waste' in p['matches']]
    print(f"  waste_management with 'waste' keyword: {len(waste_mgmt)}")

    return {
        'wrong_topic': wrong_topic,
        'no_keywords': no_keywords,
        'strong_mismatch': strong_mismatch,
        'short_no_kw': short_no_kw,
        'waste_mgmt': waste_mgmt,
    }


def main():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    results = {}
    for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
        results[council] = analyze_council(conn, council)

    # Summary of fixable items
    print("\n" + "=" * 80)
    print("SUMMARY - FIXABLE ITEMS")
    print("=" * 80)

    total_wrong = sum(len(r['wrong_topic']) for r in results.values())
    total_no_kw = sum(len(r['no_keywords']) for r in results.values())
    total_strong = sum(len(r['strong_mismatch']) for r in results.values())
    total_short = sum(len(r['short_no_kw']) for r in results.values())
    total_waste = sum(len(r['waste_mgmt']) for r in results.values())

    print(f"\nTotal wrong topic: {total_wrong}")
    print(f"Total no keywords: {total_no_kw}")
    print(f"---")
    print(f"Strong mismatches (easy auto-fix): {total_strong}")
    print(f"Short provisions (likely headers): {total_short}")
    print(f"waste_management->waste rename: {total_waste}")

    # Calculate potential improvement
    # Strong mismatches: ~90% fixable
    # Short provisions: keep as-is (headers)
    # waste_management: 100% fixable (rename)
    fixable = total_strong * 0.9 + total_waste
    print(f"\nEstimated fixable: ~{int(fixable)} provisions")
    print(f"After fix, estimated errors: ~{352 - int(fixable)}")

    conn.close()


if __name__ == '__main__':
    main()
