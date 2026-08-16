#!/usr/bin/env python3
"""
TOPIC COVERAGE AUDIT

For EVERY actionable provision, determine:
1. Can we derive the topic from structure? (marker, document_id, part)
2. If not, WHY not?

Target: 100% coverage with deterministic rules, NO keyword guessing.
"""
import os
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

# =============================================================================
# TOPIC DERIVATION RULES
# =============================================================================

LEICHHARDT_MARKER_TOPICS = {
    'C1': 'site_analysis', 'C2': 'heritage', 'C3': 'parking', 'C4': 'building_form',
    'C5': 'roofing', 'C6': 'landscaping', 'C7': 'fencing', 'C8': 'setbacks',
    'C9': 'trees', 'C10': 'trees', 'C11': 'trees', 'C12': 'flooding',
    'C13': 'contamination', 'C14': 'parking', 'C15': 'parking', 'C16': 'parking',
    'C17': 'parking', 'C18': 'bicycle_parking', 'C19': 'bicycle_parking',
    'C20': 'bicycle_parking', 'C21': 'bicycle_parking', 'C22': 'access',
    'C23': 'landscaping', 'C24': 'building_design', 'C25': 'building_design',
    'C26': 'open_space', 'C27': 'building_design', 'C28': 'building_design',
    'C29': 'privacy', 'C30': 'solar', 'C31': 'views', 'C32': 'setbacks',
    'C33': 'height', 'C34': 'building_form', 'C35': 'building_form',
    'C36': 'safety', 'C37': 'heritage', 'C38': 'signage', 'C39': 'signage',
    'C40': 'advertising', 'C41': 'advertising', 'C42': 'advertising',
    'C43': 'vehicle_access', 'C44': 'vehicle_access', 'C45': 'vehicle_access',
    'C46': 'vehicle_access', 'C47': 'vehicle_access', 'C48': 'vehicle_access',
    'C49': 'vehicle_access', 'C50': 'vehicle_access', 'C51': 'vehicle_access',
    'C52': 'vehicle_access', 'C53': 'vehicle_access', 'C54': 'vehicle_access',
    'C55': 'vehicle_access',
}

MARRICKVILLE_SECTION_TOPICS = {
    '1': 'urban_design', '3': 'site_analysis', '5': 'access', '6': 'privacy',
    '7': 'solar', '8': 'social_impact', '9': 'safety', '10': 'parking',
    '11': 'fencing', '12': 'signage', '13': 'biodiversity', '14': 'environmental',
    '16': 'energy', '17': 'wsud', '18': 'landscaping', '25': 'stormwater',
}


def derive_topic_leichhardt(marker, dcp_part, document_id):
    """Derive topic for Leichhardt provision."""
    # Rule 1: Marker lookup (most reliable)
    if marker:
        m = re.match(r'^(C\d+)', marker.strip().upper())
        if m and m.group(1) in LEICHHARDT_MARKER_TOPICS:
            return LEICHHARDT_MARKER_TOPICS[m.group(1)], 'marker'

    # Rule 2: Part-based defaults
    if dcp_part == 'Part D':
        return 'energy', 'part'
    if dcp_part == 'Part E':
        return 'water', 'part'
    if dcp_part == 'Part F':
        return 'food_premises', 'part'
    if dcp_part == 'Part G':
        return 'site_specific', 'part'
    if dcp_part == 'Part C Section 2':
        return 'neighbourhood', 'part'

    # Rule 3: Part A is intro (should not be actionable)
    if dcp_part == 'unknown' or 'Part A' in (document_id or ''):
        return None, 'intro_garbage'

    # Rule 4: Part C Section 1 without marker - PROBLEM
    if dcp_part == 'Part C Section 1':
        return None, 'missing_marker'

    return None, 'unknown'


def derive_topic_marrickville(marker, dcp_part, document_id):
    """Derive topic for Marrickville provision."""
    # Rule 1: Part 8 = heritage
    if dcp_part == 'Part 8':
        return 'heritage', 'part'

    # Rule 2: Part 9 = precinct
    if dcp_part == 'Part 9':
        return 'precinct', 'part'

    # Rule 3: Part 4.1/4.2 = residential types
    if dcp_part == 'Part 4.1':
        return 'low_density_residential', 'part'
    if dcp_part == 'Part 4.2':
        return 'multi_dwelling', 'part'

    # Rule 4: Part 5/6 = commercial/industrial
    if dcp_part == 'Part 5':
        return 'commercial', 'part'
    if dcp_part == 'Part 6':
        return 'industrial', 'part'

    # Rule 5: Part 2 - extract section from document_id
    if dcp_part == 'Part 2' and document_id:
        # Pattern: __2__10__ or __2__18__
        m = re.search(r'__2__(\d+)__', document_id)
        if m:
            section = m.group(1)
            if section in MARRICKVILLE_SECTION_TOPICS:
                return MARRICKVILLE_SECTION_TOPICS[section], 'document_id'
        return None, 'part2_no_section'

    if dcp_part == 'unknown':
        return None, 'unknown_part'

    return None, 'unknown'


def derive_topic_ashfield(marker, dcp_part, document_id):
    """Derive topic for Ashfield provision."""
    # Rule 1: Chapter E1 = heritage
    if dcp_part == 'Chapter E1':
        return 'heritage', 'part'

    # Rule 2: Chapter D = precinct
    if dcp_part == 'Chapter D':
        return 'precinct', 'part'

    # Rule 3: Chapter C = sustainability
    if dcp_part == 'Chapter C':
        return 'sustainability', 'part'

    # Rule 4: Chapter A = miscellaneous
    if dcp_part == 'Chapter A':
        return 'miscellaneous', 'part'

    # Rule 5: Chapter F parts
    if dcp_part and 'Chapter F' in dcp_part:
        return 'development_category', 'part'

    if dcp_part == 'unknown':
        return None, 'unknown_part'

    return None, 'unknown'


def main():
    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*80)
    print("TOPIC COVERAGE AUDIT - Can we derive topic for EVERY provision?")
    print("="*80)

    grand_total = 0
    grand_covered = 0
    grand_problems = defaultdict(int)

    for council in ['leichhardt', 'ashfield', 'marrickville']:
        print(f"\n\n{'#'*80}")
        print(f"# {council.upper()}")
        print(f"{'#'*80}")

        cur.execute(f"""
            SELECT id, v2_marker, v2_dcp_part, document_id, LEFT(provision_text, 100)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%{council}%'
            AND v2_is_actionable = true
        """)

        provisions = cur.fetchall()
        total = len(provisions)
        grand_total += total

        covered = 0
        problems = defaultdict(list)

        for prov_id, marker, dcp_part, doc_id, text_preview in provisions:
            if council == 'leichhardt':
                topic, method = derive_topic_leichhardt(marker, dcp_part, doc_id)
            elif council == 'marrickville':
                topic, method = derive_topic_marrickville(marker, dcp_part, doc_id)
            else:
                topic, method = derive_topic_ashfield(marker, dcp_part, doc_id)

            if topic:
                covered += 1
            else:
                problems[method].append((prov_id, dcp_part, text_preview[:50] if text_preview else ''))
                grand_problems[f"{council}:{method}"] += 1

        grand_covered += covered
        coverage_pct = 100 * covered // total if total else 0

        print(f"\nTotal actionable: {total}")
        print(f"Can derive topic: {covered} ({coverage_pct}%)")
        print(f"CANNOT derive:    {total - covered} ({100 - coverage_pct}%)")

        if problems:
            print(f"\n## Problems by category:")
            for category, items in sorted(problems.items(), key=lambda x: -len(x[1])):
                print(f"\n  {category}: {len(items)} provisions")
                for prov_id, part, preview in items[:3]:
                    print(f"    ID {prov_id} | {part} | {preview}...")
                if len(items) > 3:
                    print(f"    ... and {len(items) - 3} more")

    # Grand summary
    print(f"\n\n{'='*80}")
    print("GRAND SUMMARY")
    print("="*80)
    print(f"\nTotal actionable provisions: {grand_total}")
    print(f"Can derive topic (100% certain): {grand_covered} ({100*grand_covered//grand_total}%)")
    print(f"CANNOT derive (problems): {grand_total - grand_covered}")

    print(f"\n## Problem breakdown:")
    for key, count in sorted(grand_problems.items(), key=lambda x: -x[1]):
        print(f"  {key}: {count}")

    print(f"\n## Required actions to reach 100%:")
    if grand_problems:
        for key in grand_problems:
            council, problem = key.split(':')
            count = grand_problems[key]
            if problem == 'missing_marker':
                print(f"  - {council}: {count} Part C Section 1 provisions need marker extraction from text")
            elif problem == 'intro_garbage':
                print(f"  - {council}: {count} intro/TOC provisions should be marked v2_is_actionable=false")
            elif problem == 'part2_no_section':
                print(f"  - {council}: {count} Part 2 provisions need section extraction from document_id")
            elif problem == 'unknown_part':
                print(f"  - {council}: {count} provisions have unknown DCP part - need classification")
            else:
                print(f"  - {council}: {count} provisions: {problem}")

    conn.close()


if __name__ == '__main__':
    main()
