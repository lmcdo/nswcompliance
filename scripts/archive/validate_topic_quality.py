#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SYSTEMATIC TOPIC QUALITY VALIDATION

Run this script at any time to check topic classification quality.
Outputs a comprehensive report suitable for tracking progress.

Usage:
    python scripts/validate_topic_quality.py           # Full report
    python scripts/validate_topic_quality.py --brief   # Summary only
    python scripts/validate_topic_quality.py --json    # JSON output for automation
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

# =============================================================================
# VALIDATION KEYWORDS (topic → keywords that SHOULD appear)
# =============================================================================

TOPIC_KEYWORDS = {
    'setbacks': ['setback', 'set back', 'boundary clearance', 'building line', 'front yard', 'rear yard', 'side yard'],
    'parking': ['parking', 'car space', 'garage', 'carport', 'vehicle parking', 'driveway'],
    'height': ['height', 'storey', 'storeys', 'floor level', 'maximum height', 'building height'],
    'heritage': ['heritage', 'conservation', 'historic', 'character', 'hca', 'heritage item', 'contributory'],
    'landscaping': ['landscap', 'planting', 'garden', 'vegetation', 'green'],
    'privacy': ['privacy', 'overlooking', 'window separation', 'screening'],
    'solar': ['solar', 'overshadow', 'sunlight', 'daylight', 'shadow'],
    'trees': ['tree', 'canopy', 'vegetation removal', 'arborist'],
    'fencing': ['fence', 'fencing', 'front boundary'],
    'access': ['access', 'entry', 'pedestrian'],
    'building_form': ['bulk', 'scale', 'massing', 'form', 'articulation'],
    'building_design': ['design', 'facade', 'materials', 'finishes'],
    'flooding': ['flood', 'inundation', 'stormwater'],
    'contamination': ['contaminat', 'remediat', 'hazard'],
    'safety': ['safety', 'crime', 'cpted', 'surveillance'],
    'signage': ['sign', 'signage', 'advertising'],
    'vehicle_access': ['crossover', 'driveway', 'vehicle crossing', 'kerb'],
    'open_space': ['open space', 'courtyard', 'private open'],
    'roofing': ['roof', 'roofing', 'pitched', 'parapet'],
    'site_analysis': ['site analysis', 'context', 'streetscape'],
    'bicycle_parking': ['bicycle', 'bike', 'cycle'],
    'stormwater': ['stormwater', 'drainage', 'runoff', 'detention'],
    'waste': ['waste', 'garbage', 'recycling', 'bin'],
    'water': ['water', 'rainwater', 'greywater'],
    'energy': ['energy', 'basix', 'thermal', 'insulation'],
}

# Accuracy thresholds
THRESHOLD_GOOD = 70
THRESHOLD_ACCEPTABLE = 50


class TopicValidator:
    """Validate topic classification quality."""

    def __init__(self):
        self.conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
        self.results = {}

    def close(self):
        self.conn.close()

    def validate_topic(self, council: str, topic: str, limit: int = 50) -> Dict:
        """Validate a single topic for a council."""
        cur = self.conn.cursor()

        keywords = TOPIC_KEYWORDS.get(topic, [])
        if not keywords:
            return {'topic': topic, 'total': 0, 'matches': 0, 'accuracy': 0, 'status': 'NO_KEYWORDS'}

        cur.execute('''
            SELECT id, v2_marker, LEFT(provision_text, 400)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND v2_is_actionable = true
            AND LOWER(v2_topic) = LOWER(%s)
            LIMIT %s
        ''', (f'%{council}%', topic, limit))

        rows = cur.fetchall()
        total = len(rows)
        matches = 0

        for prov_id, marker, text in rows:
            if not text:
                continue
            text_lower = text.lower()
            if any(kw.lower() in text_lower for kw in keywords):
                matches += 1

        accuracy = (matches * 100 // total) if total > 0 else 0

        if accuracy >= THRESHOLD_GOOD:
            status = 'GOOD'
        elif accuracy >= THRESHOLD_ACCEPTABLE:
            status = 'ACCEPTABLE'
        else:
            status = 'POOR'

        cur.close()
        return {
            'topic': topic,
            'total': total,
            'matches': matches,
            'accuracy': accuracy,
            'status': status
        }

    def validate_council(self, council: str) -> Dict:
        """Validate all topics for a council."""
        cur = self.conn.cursor()

        # Get all topics used by this council
        cur.execute('''
            SELECT DISTINCT LOWER(v2_topic) as topic, COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND v2_is_actionable = true
            AND v2_topic IS NOT NULL
            AND v2_topic != ''
            AND v2_topic != 'None'
            GROUP BY LOWER(v2_topic)
            ORDER BY count DESC
        ''', (f'%{council}%',))

        topics = [(row[0], row[1]) for row in cur.fetchall()]
        cur.close()

        results = []
        for topic, count in topics:
            result = self.validate_topic(council, topic)
            result['provision_count'] = count
            results.append(result)

        # Calculate overall stats
        total_provisions = sum(r['provision_count'] for r in results)
        good_count = sum(r['provision_count'] for r in results if r['status'] == 'GOOD')
        acceptable_count = sum(r['provision_count'] for r in results if r['status'] == 'ACCEPTABLE')
        poor_count = sum(r['provision_count'] for r in results if r['status'] == 'POOR')

        return {
            'council': council,
            'total_provisions': total_provisions,
            'topics': results,
            'summary': {
                'good': good_count,
                'acceptable': acceptable_count,
                'poor': poor_count,
                'good_pct': (good_count * 100 // total_provisions) if total_provisions else 0,
                'acceptable_pct': (acceptable_count * 100 // total_provisions) if total_provisions else 0,
                'poor_pct': (poor_count * 100 // total_provisions) if total_provisions else 0,
            }
        }

    def validate_all(self) -> Dict:
        """Validate all councils."""
        timestamp = datetime.now().isoformat()
        results = {
            'timestamp': timestamp,
            'thresholds': {
                'good': THRESHOLD_GOOD,
                'acceptable': THRESHOLD_ACCEPTABLE
            },
            'councils': {}
        }

        for council in ['leichhardt', 'ashfield', 'marrickville']:
            results['councils'][council] = self.validate_council(council)

        # Overall summary
        total_good = sum(r['summary']['good'] for r in results['councils'].values())
        total_acceptable = sum(r['summary']['acceptable'] for r in results['councils'].values())
        total_poor = sum(r['summary']['poor'] for r in results['councils'].values())
        total_all = total_good + total_acceptable + total_poor

        results['overall'] = {
            'total_provisions': total_all,
            'good': total_good,
            'acceptable': total_acceptable,
            'poor': total_poor,
            'good_pct': (total_good * 100 // total_all) if total_all else 0,
            'quality_score': ((total_good * 100 + total_acceptable * 50) // total_all) if total_all else 0
        }

        return results

    def print_report(self, results: Dict, brief: bool = False):
        """Print human-readable report."""
        print("=" * 70)
        print("TOPIC CLASSIFICATION QUALITY REPORT")
        print(f"Generated: {results['timestamp']}")
        print(f"Thresholds: GOOD >= {results['thresholds']['good']}%, ACCEPTABLE >= {results['thresholds']['acceptable']}%")
        print("=" * 70)

        # Overall summary
        overall = results['overall']
        print(f"\nOVERALL QUALITY SCORE: {overall['quality_score']}%")
        print(f"Total provisions with topics: {overall['total_provisions']}")
        print(f"  GOOD:       {overall['good']:5} ({overall['good_pct']}%)")
        print(f"  ACCEPTABLE: {overall['acceptable']:5}")
        print(f"  POOR:       {overall['poor']:5}")

        for council_name, council_data in results['councils'].items():
            print(f"\n{'='*70}")
            print(f"{council_name.upper()}")
            print(f"{'='*70}")

            summary = council_data['summary']
            print(f"Provisions: {council_data['total_provisions']}")
            print(f"Quality: GOOD {summary['good_pct']}% | ACCEPTABLE {summary['acceptable_pct']}% | POOR {summary['poor_pct']}%")

            if not brief:
                print(f"\n{'Topic':<20} {'Count':>8} {'Sampled':>8} {'Match':>8} {'Accuracy':>10} {'Status':>10}")
                print("-" * 66)

                for topic in sorted(council_data['topics'], key=lambda x: -x['provision_count']):
                    status_icon = '✓' if topic['status'] == 'GOOD' else ('~' if topic['status'] == 'ACCEPTABLE' else '✗')
                    print(f"{topic['topic']:<20} {topic['provision_count']:>8} {topic['total']:>8} {topic['matches']:>8} {topic['accuracy']:>9}% {status_icon:>10}")

        # Problems summary
        print(f"\n{'='*70}")
        print("TOPICS NEEDING ATTENTION (POOR quality)")
        print("=" * 70)

        for council_name, council_data in results['councils'].items():
            poor_topics = [t for t in council_data['topics'] if t['status'] == 'POOR' and t['total'] > 0]
            if poor_topics:
                print(f"\n{council_name.upper()}:")
                for topic in sorted(poor_topics, key=lambda x: x['accuracy']):
                    print(f"  {topic['topic']:<20} {topic['accuracy']:>3}% accuracy ({topic['provision_count']} provisions)")

    def save_json(self, results: Dict, filepath: str = None):
        """Save results as JSON."""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f'scripts/validation_reports/topic_quality_{timestamp}.json'

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        print(f"\nJSON report saved to: {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description='Validate topic classification quality')
    parser.add_argument('--brief', action='store_true', help='Show summary only')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--save', action='store_true', help='Save report to file')
    parser.add_argument('--council', type=str, help='Validate single council only')

    args = parser.parse_args()

    validator = TopicValidator()

    try:
        if args.council:
            results = {
                'timestamp': datetime.now().isoformat(),
                'thresholds': {'good': THRESHOLD_GOOD, 'acceptable': THRESHOLD_ACCEPTABLE},
                'councils': {args.council: validator.validate_council(args.council)},
                'overall': {}
            }
        else:
            results = validator.validate_all()

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            validator.print_report(results, brief=args.brief)

        if args.save:
            validator.save_json(results)

    finally:
        validator.close()


if __name__ == '__main__':
    main()
