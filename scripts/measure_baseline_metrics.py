#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
COMPREHENSIVE BASELINE METRICS MEASUREMENT

Phase 1 of Rule-Based Provision Enrichment Plan.
Measures current state of:
- Topic classification quality
- v2_provision_type coverage
- Cross-reference resolution rates

Usage:
    python scripts/measure_baseline_metrics.py           # Full report
    python scripts/measure_baseline_metrics.py --json    # JSON output
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2


def get_db_url() -> str:
    """Get database URL from environment."""
    # Try multiple env var names
    url = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
    if not url:
        # Build from components
        host = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST')
        port = os.getenv('DATABASE_PORT') or os.getenv('DB_PORT') or '5432'
        name = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME') or 'postgres'
        user = os.getenv('DATABASE_USER') or os.getenv('DB_USER')
        password = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD')
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    return url


class BaselineMetrics:
    """Measure baseline metrics for provision enrichment."""

    def __init__(self):
        self.conn = psycopg2.connect(get_db_url())
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'provision_type': {},
            'cross_references': {},
            'topic_coverage': {},
            'overall_summary': {}
        }

    def close(self):
        self.conn.close()

    def measure_provision_type_coverage(self) -> Dict[str, Any]:
        """Measure v2_provision_type population coverage."""
        cur = self.conn.cursor()

        # Overall provision type distribution
        cur.execute("""
            SELECT
                v2_provision_type,
                COUNT(*) as count
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            GROUP BY v2_provision_type
            ORDER BY count DESC
        """)
        distribution = {row[0] or 'NULL': row[1] for row in cur.fetchall()}

        # Calculate totals
        total = sum(distribution.values())
        null_count = distribution.get('NULL', 0)
        populated_count = total - null_count
        populated_pct = round(100 * populated_count / total, 1) if total else 0

        # Breakdown by council
        cur.execute("""
            SELECT
                CASE
                    WHEN document_id ILIKE '%leichhardt%' THEN 'leichhardt'
                    WHEN document_id ILIKE '%ashfield%' THEN 'ashfield'
                    WHEN document_id ILIKE '%marrickville%' THEN 'marrickville'
                    ELSE 'other'
                END as council,
                v2_provision_type,
                COUNT(*) as count
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            GROUP BY council, v2_provision_type
            ORDER BY council, count DESC
        """)

        by_council = {}
        for council, ptype, count in cur.fetchall():
            if council not in by_council:
                by_council[council] = {}
            by_council[council][ptype or 'NULL'] = count

        cur.close()

        return {
            'total_actionable': total,
            'populated': populated_count,
            'null_count': null_count,
            'populated_pct': populated_pct,
            'distribution': distribution,
            'by_council': by_council,
            'target': 90,  # Target percentage
            'meets_target': populated_pct >= 90
        }

    def measure_cross_reference_resolution(self) -> Dict[str, Any]:
        """Measure cross-reference resolution statistics."""
        cur = self.conn.cursor()

        # Overall resolution stats
        cur.execute("""
            SELECT
                resolution_status,
                COUNT(*) as count,
                ROUND(AVG(resolution_confidence)::numeric, 2) as avg_confidence
            FROM cross_reference_index
            GROUP BY resolution_status
            ORDER BY count DESC
        """)

        by_status = {}
        total = 0
        for status, count, confidence in cur.fetchall():
            by_status[status] = {'count': count, 'avg_confidence': float(confidence) if confidence else None}
            total += count

        # Resolution rate
        resolved = by_status.get('resolved', {}).get('count', 0)
        resolution_rate = round(100 * resolved / total, 1) if total else 0

        # By reference type
        cur.execute("""
            SELECT
                reference_type,
                resolution_status,
                COUNT(*) as count
            FROM cross_reference_index
            GROUP BY reference_type, resolution_status
            ORDER BY reference_type, count DESC
        """)

        by_type = {}
        for ref_type, status, count in cur.fetchall():
            if ref_type not in by_type:
                by_type[ref_type] = {}
            by_type[ref_type][status] = count

        # Mandatory vs optional breakdown
        cur.execute("""
            SELECT
                is_mandatory,
                resolution_status,
                COUNT(*) as count
            FROM cross_reference_index
            GROUP BY is_mandatory, resolution_status
            ORDER BY is_mandatory DESC, count DESC
        """)

        mandatory_stats = {'mandatory': {}, 'optional': {}}
        for is_mandatory, status, count in cur.fetchall():
            key = 'mandatory' if is_mandatory else 'optional'
            mandatory_stats[key][status] = count

        cur.close()

        return {
            'total': total,
            'by_status': by_status,
            'resolution_rate': resolution_rate,
            'by_type': by_type,
            'mandatory_stats': mandatory_stats
        }

    def measure_topic_coverage(self) -> Dict[str, Any]:
        """Measure topic classification coverage."""
        cur = self.conn.cursor()

        # Topic coverage by council
        cur.execute("""
            SELECT
                CASE
                    WHEN document_id ILIKE '%leichhardt%' THEN 'leichhardt'
                    WHEN document_id ILIKE '%ashfield%' THEN 'ashfield'
                    WHEN document_id ILIKE '%marrickville%' THEN 'marrickville'
                    ELSE 'other'
                END as council,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE v2_topic IS NOT NULL AND v2_topic != '' AND v2_topic != 'None') as with_topic,
                COUNT(*) FILTER (WHERE v2_topic IS NULL OR v2_topic = '' OR v2_topic = 'None') as no_topic
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            GROUP BY council
            ORDER BY council
        """)

        by_council = {}
        total_all = 0
        with_topic_all = 0

        for council, total, with_topic, no_topic in cur.fetchall():
            coverage_pct = round(100 * with_topic / total, 1) if total else 0
            by_council[council] = {
                'total': total,
                'with_topic': with_topic,
                'no_topic': no_topic,
                'coverage_pct': coverage_pct
            }
            total_all += total
            with_topic_all += with_topic

        overall_coverage = round(100 * with_topic_all / total_all, 1) if total_all else 0

        # Topic distribution
        cur.execute("""
            SELECT
                LOWER(v2_topic) as topic,
                COUNT(*) as count
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            AND v2_topic IS NOT NULL
            AND v2_topic != ''
            AND v2_topic != 'None'
            GROUP BY LOWER(v2_topic)
            ORDER BY count DESC
            LIMIT 25
        """)

        topic_distribution = {row[0]: row[1] for row in cur.fetchall()}

        cur.close()

        return {
            'overall_coverage_pct': overall_coverage,
            'total_provisions': total_all,
            'with_topic': with_topic_all,
            'no_topic': total_all - with_topic_all,
            'by_council': by_council,
            'topic_distribution': topic_distribution,
            'target': 95,  # Target percentage
            'meets_target': overall_coverage >= 95
        }

    def measure_all(self) -> Dict[str, Any]:
        """Run all measurements and compile results."""
        print("Measuring provision type coverage...")
        self.results['provision_type'] = self.measure_provision_type_coverage()

        print("Measuring cross-reference resolution...")
        self.results['cross_references'] = self.measure_cross_reference_resolution()

        print("Measuring topic coverage...")
        self.results['topic_coverage'] = self.measure_topic_coverage()

        # Compile overall summary
        self.results['overall_summary'] = {
            'provision_type_populated_pct': self.results['provision_type']['populated_pct'],
            'cross_ref_resolution_rate': self.results['cross_references']['resolution_rate'],
            'topic_coverage_pct': self.results['topic_coverage']['overall_coverage_pct'],
            'targets': {
                'provision_type': {'target': 90, 'current': self.results['provision_type']['populated_pct']},
                'topic_coverage': {'target': 95, 'current': self.results['topic_coverage']['overall_coverage_pct']},
                'cross_ref_ui': {'target': 100, 'current': 0}  # UI display not implemented yet
            }
        }

        return self.results

    def print_report(self):
        """Print human-readable report."""
        print("\n" + "=" * 80)
        print("BASELINE METRICS REPORT - Rule-Based Provision Enrichment")
        print(f"Generated: {self.results['timestamp']}")
        print("=" * 80)

        # Provision Type Coverage
        pt = self.results['provision_type']
        print(f"\n{'='*80}")
        print("1. PROVISION TYPE COVERAGE (v2_provision_type)")
        print("=" * 80)
        print(f"Total actionable provisions: {pt['total_actionable']:,}")
        print(f"Populated:                   {pt['populated']:,} ({pt['populated_pct']}%)")
        print(f"NULL/missing:                {pt['null_count']:,}")
        print(f"Target:                      {pt['target']}%")
        print(f"Status:                      {'MEETS TARGET' if pt['meets_target'] else 'NEEDS WORK'}")

        print(f"\nDistribution:")
        for ptype, count in sorted(pt['distribution'].items(), key=lambda x: -x[1]):
            pct = round(100 * count / pt['total_actionable'], 1)
            print(f"  {ptype or 'NULL':<20} {count:>6} ({pct}%)")

        # Cross-Reference Resolution
        xr = self.results['cross_references']
        print(f"\n{'='*80}")
        print("2. CROSS-REFERENCE RESOLUTION")
        print("=" * 80)
        print(f"Total cross-references:  {xr['total']:,}")
        print(f"Resolution rate:         {xr['resolution_rate']}%")

        print(f"\nBy status:")
        for status, data in xr['by_status'].items():
            conf = f" (avg confidence: {data['avg_confidence']})" if data['avg_confidence'] else ""
            print(f"  {status:<15} {data['count']:>6}{conf}")

        print(f"\nBy reference type:")
        for ref_type, statuses in sorted(xr['by_type'].items()):
            total_type = sum(statuses.values())
            resolved = statuses.get('resolved', 0)
            rate = round(100 * resolved / total_type, 1) if total_type else 0
            print(f"  {ref_type:<20} {total_type:>6} total, {rate}% resolved")

        # Topic Coverage
        tc = self.results['topic_coverage']
        print(f"\n{'='*80}")
        print("3. TOPIC CLASSIFICATION COVERAGE")
        print("=" * 80)
        print(f"Overall coverage:        {tc['overall_coverage_pct']}%")
        print(f"With topic:              {tc['with_topic']:,}")
        print(f"No topic:                {tc['no_topic']:,}")
        print(f"Target:                  {tc['target']}%")
        print(f"Status:                  {'MEETS TARGET' if tc['meets_target'] else 'NEEDS WORK'}")

        print(f"\nBy council:")
        for council, data in tc['by_council'].items():
            print(f"  {council:<15} {data['coverage_pct']:>5}% ({data['with_topic']:,}/{data['total']:,})")

        print(f"\nTop topics:")
        for topic, count in list(tc['topic_distribution'].items())[:10]:
            print(f"  {topic:<25} {count:>6}")

        # Summary
        summary = self.results['overall_summary']
        print(f"\n{'='*80}")
        print("SUMMARY - Progress Toward Targets")
        print("=" * 80)
        for metric, data in summary['targets'].items():
            current = data['current']
            target = data['target']
            gap = target - current
            status = 'DONE' if gap <= 0 else f'{gap}% to go'
            print(f"  {metric:<25} {current:>5}% / {target}% target  [{status}]")

    def save_json(self, filepath: str = None) -> str:
        """Save results as JSON."""
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f'scripts/validation_reports/baseline_metrics_{timestamp}.json'

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nJSON report saved to: {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description='Measure baseline metrics for provision enrichment')
    parser.add_argument('--json', action='store_true', help='Output JSON format only')
    parser.add_argument('--save', action='store_true', help='Save report to file')

    args = parser.parse_args()

    metrics = BaselineMetrics()

    try:
        metrics.measure_all()

        if args.json:
            print(json.dumps(metrics.results, indent=2))
        else:
            metrics.print_report()

        if args.save:
            metrics.save_json()

    finally:
        metrics.close()


if __name__ == '__main__':
    main()
