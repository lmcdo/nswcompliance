#!/usr/bin/env python3
"""
Audit all Leichhardt DCP parts for topic tagging issues

Systematically checks each DCP part for:
- Topic distribution (should each part have only 1 topic?)
- Content matching (do keywords match assigned topics?)
- Structural issues (parts with multiple sections?)

Usage:
    python scripts/audit_leichhardt_topics.py
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from collections import defaultdict
import pathlib

# Load environment variables
script_dir = pathlib.Path(__file__).parent.absolute()
project_root = script_dir.parent
env_file = project_root / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)


def get_db_connection():
    """Get PostgreSQL database connection"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


# Topic-specific keywords for validation
TOPIC_KEYWORDS = {
    'energy': ['energy', 'solar', 'renewable', 'photovoltaic', 'heating', 'cooling', 'thermal', 'electricity', 'power'],
    'waste_management': ['waste', 'recycling', 'recyclable', 'rubbish', 'bin', 'disposal', 'SWMMP', 'resource recovery', 'minimisation'],
    'water': ['water', 'stormwater', 'drainage', 'rainwater', 'tank', 'retention', 'detention', 'WSUD', 'pervious'],
    'heritage': ['heritage', 'conservation', 'HCA', 'significant', 'contributory', 'character', 'historic'],
    'parking': ['parking', 'vehicle', 'car', 'bicycle', 'motorcycle', 'loading', 'garage', 'driveway'],
    'setback': ['setback', 'building line', 'boundary', 'front', 'rear', 'side', 'street alignment'],
    'landscaping': ['landscape', 'planting', 'tree', 'garden', 'vegetation', 'canopy', 'deep soil'],
    'height': ['height', 'storey', 'level', 'floor', 'RL', 'ridge', 'eaves'],
    'density': ['density', 'FSR', 'floor space', 'GFA', 'site coverage', 'building footprint'],
}


def analyze_part_topics(conn, part_id, part_name):
    """Analyze topic distribution and content matching for a DCP part"""

    with conn.cursor() as cur:
        # Get all provisions for this part
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_dcp_part = %s
              AND is_current = TRUE
            ORDER BY pdf_page
        """, ('%Leichhardt%', part_id))

        provisions = cur.fetchall()

        if not provisions:
            return None

        # Count provisions by topic
        topic_counts = defaultdict(int)
        for p in provisions:
            topic = p['v2_topic'] or 'None'
            topic_counts[topic] += 1

        # Analyze content matching
        mismatches = []
        for p in provisions:
            assigned_topic = p['v2_topic']
            if not assigned_topic:
                continue

            text = p['provision_text'].lower()

            # Check if text contains keywords for assigned topic
            assigned_keywords = TOPIC_KEYWORDS.get(assigned_topic, [])
            has_assigned_keywords = any(kw in text for kw in assigned_keywords)

            # Check for keywords from OTHER topics
            other_topic_matches = {}
            for other_topic, keywords in TOPIC_KEYWORDS.items():
                if other_topic != assigned_topic:
                    matches = sum(1 for kw in keywords if kw in text)
                    if matches > 0:
                        other_topic_matches[other_topic] = matches

            # Flag if: no assigned keywords but has strong other topic keywords
            if not has_assigned_keywords and other_topic_matches:
                strongest_other = max(other_topic_matches.items(), key=lambda x: x[1])
                if strongest_other[1] >= 2:  # At least 2 keyword matches
                    mismatches.append({
                        'id': p['id'],
                        'page': p['pdf_page'],
                        'assigned_topic': assigned_topic,
                        'likely_topic': strongest_other[0],
                        'keyword_count': strongest_other[1],
                        'text_sample': p['provision_text'][:100]
                    })

        return {
            'part_id': part_id,
            'part_name': part_name,
            'total_provisions': len(provisions),
            'topic_distribution': dict(topic_counts),
            'has_multiple_topics': len(topic_counts) > 1,
            'mismatches': mismatches,
            'mismatch_rate': len(mismatches) / len(provisions) * 100 if provisions else 0
        }


def main():
    """Main audit function"""
    print("=" * 80)
    print("LEICHHARDT DCP TOPIC TAGGING AUDIT")
    print("=" * 80)

    conn = None
    try:
        conn = get_db_connection()

        # Get all Leichhardt DCP parts
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT v2_dcp_part
                FROM regulatory_provisions
                WHERE document_id ILIKE %s
                  AND v2_dcp_part IS NOT NULL
                  AND is_current = TRUE
                ORDER BY v2_dcp_part
            """, ('%Leichhardt%',))

            parts = [row['v2_dcp_part'] for row in cur.fetchall()]

        print(f"\nFound {len(parts)} Leichhardt DCP parts\n")

        # Known part names from TocSidebar
        part_names = {
            'Part C Section 1': 'General Controls',
            'Part C Section 2': 'Neighbourhood Controls',
            'Part D': 'Energy & Waste',
            'Part E': 'Water Management',
            'Part F': 'Food Premises',
            'Part G Section 1': 'Norton St Precinct',
        }

        issues_found = []

        for part_id in parts:
            part_name = part_names.get(part_id, 'Unknown')
            result = analyze_part_topics(conn, part_id, part_name)

            if not result:
                continue

            print(f"\n{result['part_id']}: {result['part_name']}")
            print(f"  Total provisions: {result['total_provisions']}")
            print(f"  Topic distribution:")
            for topic, count in sorted(result['topic_distribution'].items(), key=lambda x: -x[1]):
                pct = count / result['total_provisions'] * 100
                print(f"    {topic}: {count} ({pct:.1f}%)")

            # Flag issues
            if result['mismatch_rate'] > 10:
                print(f"  [!] HIGH MISMATCH RATE: {result['mismatch_rate']:.1f}% ({len(result['mismatches'])} provisions)")
                issues_found.append(result)

                # Show sample mismatches
                print(f"\n  Sample mismatches:")
                for m in result['mismatches'][:3]:
                    print(f"    ID {m['id']} (page {m['page']}): Assigned '{m['assigned_topic']}' but has {m['keyword_count']} '{m['likely_topic']}' keywords")
                    print(f"      Text: {m['text_sample']}...")

            elif result['has_multiple_topics']:
                topic_list = ', '.join(result['topic_distribution'].keys())
                print(f"  [i] Multiple topics: {topic_list}")
                if result['mismatch_rate'] > 5:
                    print(f"  [!] Moderate mismatch rate: {result['mismatch_rate']:.1f}%")
                    issues_found.append(result)

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        if issues_found:
            print(f"\nFound {len(issues_found)} parts with potential issues:\n")
            for issue in issues_found:
                print(f"  {issue['part_id']}: {issue['part_name']}")
                print(f"    Mismatch rate: {issue['mismatch_rate']:.1f}%")
                print(f"    Topics: {', '.join(issue['topic_distribution'].keys())}")
        else:
            print("\n[OK] No significant topic tagging issues found in other parts.")
            print("Part D was the only problematic part (now fixed).")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
