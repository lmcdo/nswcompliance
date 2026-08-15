#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POPULATE v2_provision_type USING REGEX PATTERNS

Phase 2 of Rule-Based Provision Enrichment Plan.
Classifies provisions as: objective, control, definition, note, standard

Patterns applied in priority order:
1. Text-based regex patterns (most reliable)
2. Section header signals
3. Marker-based inference (C=control, O=objective)

Usage:
    python scripts/populate_provision_types.py --dry-run   # Preview changes
    python scripts/populate_provision_types.py             # Apply changes
    python scripts/populate_provision_types.py --council leichhardt  # Single council
"""
import os
import sys
import re
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

# =============================================================================
# PROVISION TYPE PATTERNS (priority order)
# =============================================================================

TYPE_PATTERNS: Dict[str, List[str]] = {
    'objective': [
        r'^Objectives?[:\s]',
        r'^O\d+[:\.\s]',  # O1, O2, etc.
        r'^The objectives? (of|for)',
        r'^To ensure\b',
        r'^To provide\b',
        r'^To maintain\b',
        r'^To protect\b',
        r'^To promote\b',
        r'^To encourage\b',
        r'^To facilitate\b',
        r'^To minimise\b',
        r'^To achieve\b',
        r'^Objective[:\s]',
    ],
    'control': [
        r'^Controls?[:\s]',
        r'^C\d+[:\.\s]',  # Control 1, Control 2 - DCP clause markers, not zone codes  # noqa: zone-codes
        r'^Development (must|shall|should|is to)\b',
        r'^The (minimum|maximum)\b',
        r'^A minimum\b',
        r'^Buildings? (must|shall|should|are to)\b',
        r'^All development (must|shall|should)\b',
        r'^Development is (not permitted|prohibited)\b',
        r'^The following (requirements|controls)\b',
        r'^Setback[s]? (must|shall|should|are to)\b',
        r'^Height (must|shall|should|is to)\b',
        r'^Parking (must|shall|should|is to)\b',
        r'^\d+\.\d+\s+(Must|Shall|Should|Is to)\b',
    ],
    'definition': [
        r'^Definition[s]?[:\s]',
        r'^.{1,40}\s+means\s+',  # "X means ..."
        r'^In this (Part|section|clause)',
        r'^For the purposes of this',
        r'^The following terms are defined',
        r'^Interpretation[:\s]',
    ],
    'note': [
        r'^Note[:\s]',
        r'^Notes?[:\s]',
        r'^Advisory[:\s]',
        r'^See also[:\s]',
        r'^Refer to[:\s]',
        r'^For further information',
        r'^Editor.s note',
        r'^\[Note:',
        r'^NB[:\s]',
    ],
    'standard': [
        r'^\d+(\.\d+)+\s+[A-Z]',  # Numbered standards like "4.1.2 Building..."
        r'^Table \d+',
        r'^Standard[s]?[:\s]',
        r'^Performance (standard|requirement)',
    ],
}

# Section header keywords that indicate type
SECTION_HEADER_SIGNALS: Dict[str, str] = {
    'objective': 'objective',
    'objectives': 'objective',
    'control': 'control',
    'controls': 'control',
    'requirement': 'control',
    'requirements': 'control',
    'standard': 'standard',
    'standards': 'standard',
    'definition': 'definition',
    'definitions': 'definition',
    'note': 'note',
    'notes': 'note',
}

# Marker-based defaults (used as fallback)
MARKER_TYPE_MAP = {
    'O': 'objective',  # O1, O2, etc.
    'C': 'control',    # Control 1, Control 2 - DCP clause markers, not zone codes  # noqa: zone-codes
}


def get_db_url() -> str:
    """Get database URL from environment."""
    url = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
    if not url:
        host = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST')
        port = os.getenv('DATABASE_PORT') or os.getenv('DB_PORT') or '5432'
        name = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME') or 'postgres'
        user = os.getenv('DATABASE_USER') or os.getenv('DB_USER')
        password = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD')
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    return url


def classify_provision_type(
    text: str,
    section_header: Optional[str] = None,
    marker: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Classify provision type using regex patterns.

    Returns:
        Tuple of (provision_type, method) where method describes how classification was made.
    """
    if not text:
        return None, 'no_text'

    # Clean text for matching
    text_clean = text.strip()

    # Priority 1: Text-based regex patterns
    for ptype, patterns in TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, text_clean, re.IGNORECASE):
                return ptype, f'pattern:{pattern[:20]}'

    # Priority 2: Section header signals
    if section_header:
        header_lower = section_header.lower()
        for keyword, ptype in SECTION_HEADER_SIGNALS.items():
            if keyword in header_lower:
                return ptype, f'header:{keyword}'

    # Priority 3: Marker-based inference
    if marker:
        marker_clean = marker.strip().upper()
        if marker_clean:
            first_char = marker_clean[0]
            if first_char in MARKER_TYPE_MAP:
                return MARKER_TYPE_MAP[first_char], f'marker:{first_char}'

    # Could not classify
    return None, 'unclassified'


class ProvisionTypePopulator:
    """Populate v2_provision_type for provisions."""

    def __init__(self, dry_run: bool = False):
        self.conn = psycopg2.connect(get_db_url())
        self.dry_run = dry_run
        self.stats = {
            'total': 0,
            'already_classified': 0,
            'newly_classified': 0,
            'unclassified': 0,
            'by_type': {},
            'by_method': {},
        }

    def close(self):
        self.conn.close()

    def process_council(self, council: str, batch_size: int = 500) -> Dict:
        """Process provisions for a single council."""
        cur = self.conn.cursor()

        # Get provisions needing classification
        cur.execute("""
            SELECT id, provision_text, section_header, v2_marker, v2_provision_type
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND v2_is_actionable = true
        """, (f'%{council}%',))

        provisions = cur.fetchall()
        total = len(provisions)
        self.stats['total'] += total

        updates = []
        council_stats = {
            'total': total,
            'already_classified': 0,
            'newly_classified': 0,
            'unclassified': 0,
            'by_type': {},
            'by_method': {},
        }

        for prov_id, text, section_header, marker, existing_type in provisions:
            # Skip if already has a valid type
            if existing_type and existing_type not in ('', 'None', 'null', 'unknown'):
                council_stats['already_classified'] += 1
                self.stats['already_classified'] += 1
                continue

            # Classify
            ptype, method = classify_provision_type(text, section_header, marker)

            if ptype:
                updates.append((ptype, prov_id))
                council_stats['newly_classified'] += 1
                self.stats['newly_classified'] += 1

                # Track by type
                council_stats['by_type'][ptype] = council_stats['by_type'].get(ptype, 0) + 1
                self.stats['by_type'][ptype] = self.stats['by_type'].get(ptype, 0) + 1

                # Track by method
                method_key = method.split(':')[0]  # Just use first part
                council_stats['by_method'][method_key] = council_stats['by_method'].get(method_key, 0) + 1
                self.stats['by_method'][method_key] = self.stats['by_method'].get(method_key, 0) + 1
            else:
                council_stats['unclassified'] += 1
                self.stats['unclassified'] += 1

        # Apply updates in batches
        if updates and not self.dry_run:
            print(f"  Applying {len(updates)} updates in batches of {batch_size}...")
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                cur.executemany("""
                    UPDATE regulatory_provisions
                    SET v2_provision_type = %s
                    WHERE id = %s
                """, batch)
                self.conn.commit()
                print(f"    Batch {i // batch_size + 1}: {len(batch)} updates applied")

        cur.close()
        return council_stats

    def process_all(self) -> Dict:
        """Process all councils."""
        councils = ['leichhardt', 'ashfield', 'marrickville']
        results = {}

        for council in councils:
            print(f"\nProcessing {council.upper()}...")
            results[council] = self.process_council(council)

            cs = results[council]
            print(f"  Total: {cs['total']}")
            print(f"  Already classified: {cs['already_classified']}")
            print(f"  Newly classified: {cs['newly_classified']}")
            print(f"  Unclassified: {cs['unclassified']}")

            if cs['by_type']:
                print(f"  By type:")
                for ptype, count in sorted(cs['by_type'].items(), key=lambda x: -x[1]):
                    print(f"    {ptype}: {count}")

        return results

    def sample_unclassified(self, limit: int = 10) -> List[Dict]:
        """Get sample of unclassified provisions for review."""
        cur = self.conn.cursor()

        cur.execute("""
            SELECT id, LEFT(provision_text, 200), v2_marker, section_header, document_id
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            AND (v2_provision_type IS NULL OR v2_provision_type = '' OR v2_provision_type = 'None')
            ORDER BY RANDOM()
            LIMIT %s
        """, (limit,))

        samples = []
        for row in cur.fetchall():
            samples.append({
                'id': row[0],
                'text_preview': row[1],
                'marker': row[2],
                'section_header': row[3],
                'document_id': row[4],
            })

        cur.close()
        return samples

    def print_summary(self):
        """Print processing summary."""
        print("\n" + "=" * 80)
        print("PROVISION TYPE POPULATION SUMMARY")
        print("=" * 80)

        mode = "DRY RUN" if self.dry_run else "APPLIED"
        print(f"Mode: {mode}")
        print(f"Timestamp: {datetime.now().isoformat()}")

        print(f"\nOverall Statistics:")
        print(f"  Total provisions processed: {self.stats['total']:,}")
        print(f"  Already classified:         {self.stats['already_classified']:,}")
        print(f"  Newly classified:           {self.stats['newly_classified']:,}")
        print(f"  Still unclassified:         {self.stats['unclassified']:,}")

        if self.stats['total'] > 0:
            final_classified = self.stats['already_classified'] + self.stats['newly_classified']
            coverage = round(100 * final_classified / self.stats['total'], 1)
            print(f"\n  Final coverage: {coverage}%")

        if self.stats['by_type']:
            print(f"\nNewly classified by type:")
            for ptype, count in sorted(self.stats['by_type'].items(), key=lambda x: -x[1]):
                print(f"  {ptype:<15} {count:>6}")

        if self.stats['by_method']:
            print(f"\nClassification methods used:")
            for method, count in sorted(self.stats['by_method'].items(), key=lambda x: -x[1]):
                print(f"  {method:<15} {count:>6}")


def main():
    parser = argparse.ArgumentParser(description='Populate v2_provision_type using regex patterns')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    parser.add_argument('--council', type=str, help='Process single council only')
    parser.add_argument('--sample', action='store_true', help='Show sample of unclassified provisions')
    parser.add_argument('--sample-count', type=int, default=10, help='Number of samples to show')

    args = parser.parse_args()

    populator = ProvisionTypePopulator(dry_run=args.dry_run)

    try:
        if args.sample:
            print("Sample of unclassified provisions:")
            print("=" * 80)
            samples = populator.sample_unclassified(args.sample_count)
            for s in samples:
                print(f"\nID: {s['id']}")
                print(f"Marker: {s['marker']}")
                print(f"Section: {s['section_header']}")
                print(f"Text: {s['text_preview']}...")
                print("-" * 40)
            return

        if args.council:
            print(f"Processing {args.council.upper()}...")
            populator.process_council(args.council)
        else:
            populator.process_all()

        populator.print_summary()

        if args.dry_run:
            print("\n[DRY RUN] No changes were made. Run without --dry-run to apply.")

    finally:
        populator.close()


if __name__ == '__main__':
    main()
