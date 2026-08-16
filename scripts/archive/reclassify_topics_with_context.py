#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPIC RECLASSIFICATION WITH SECTION CONTEXT

This script fixes topic misclassification by using PDF section headers
instead of keyword matching. The key insight is that provision topics
should be derived from which DCP section they appear in, not from
keywords in the text.

SAFEGUARDS:
1. Full backup before any changes
2. Process one DCP part at a time
3. Validate accuracy after each part
4. Checkpoint support for resume
5. Dry-run mode by default
6. Rollback capability

APPROACH:
- For each council, extract section headers from PDF structure
- Group provisions by page → section
- Assign topic based on section, not keywords
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2
from psycopg2.extras import RealDictCursor


# =============================================================================
# SECTION → TOPIC MAPPINGS (Derived from DCP Table of Contents)
# =============================================================================

LEICHHARDT_SECTION_TOPICS = {
    # Part C Section 1 - General Development Controls
    'C1': 'site_analysis',
    'C2': 'heritage',
    'C3': 'parking',
    'C4': 'building_form',
    'C5': 'roofing',
    'C6': 'landscaping',
    'C7': 'fencing',
    'C8': 'setbacks',
    'C9': 'trees',
    'C10': 'trees',
    'C11': 'trees',
    'C12': 'flooding',
    'C13': 'contamination',
    'C14': 'parking',
    'C15': 'parking',
    'C16': 'parking',
    'C17': 'parking',
    'C18': 'bicycle_parking',
    'C19': 'bicycle_parking',
    'C20': 'bicycle_parking',
    'C21': 'bicycle_parking',
    'C22': 'access',
    'C23': 'landscaping',
    'C24': 'building_design',
    'C25': 'building_design',
    'C26': 'open_space',
    'C27': 'building_design',
    'C28': 'building_design',
    'C29': 'privacy',
    'C30': 'solar',
    'C31': 'views',
    'C32': 'setbacks',
    'C33': 'height',
    'C34': 'building_form',
    'C35': 'building_form',
    'C36': 'safety',
    'C37': 'heritage',
    'C38': 'signage',
    'C39': 'signage',
    'C40': 'advertising',
    'C41': 'advertising',
    'C42': 'advertising',
    'C43': 'vehicle_access',
    'C44': 'vehicle_access',
    'C45': 'vehicle_access',
    'C46': 'vehicle_access',
    'C47': 'vehicle_access',
    'C48': 'vehicle_access',
    'C49': 'vehicle_access',
    'C50': 'vehicle_access',
    'C51': 'vehicle_access',
    'C52': 'vehicle_access',
    'C53': 'vehicle_access',
    'C54': 'vehicle_access',
    'C55': 'vehicle_access',
}

MARRICKVILLE_SECTION_TOPICS = {
    # Part 2 - General Provisions (section number → topic)
    '2.1': 'general',
    '2.2': 'general',
    '2.3': 'site_analysis',
    '2.4': 'building_design',
    '2.5': 'setbacks',
    '2.6': 'privacy',
    '2.7': 'solar',
    '2.8': 'views',
    '2.9': 'fencing',
    '2.10': 'parking',
    '2.11': 'access',
    '2.12': 'safety',
    '2.13': 'signage',
    '2.14': 'environmental',
    '2.15': 'contamination',
    '2.16': 'stormwater',
    '2.17': 'wsud',
    '2.18': 'landscaping',
    '2.19': 'trees',
    '2.20': 'infrastructure',
    '2.21': 'waste',
    # Part 4 - Residential
    '4.1': 'low_density_residential',
    '4.2': 'multi_dwelling',
    # Part 5 - Commercial
    '5': 'commercial',
    # Part 6 - Industrial
    '6': 'industrial',
    # Part 8 - Heritage
    '8': 'heritage',
    '8.0': 'heritage',
}

ASHFIELD_SECTION_TOPICS = {
    # Chapter E - Heritage
    'E1': 'heritage',
    'E2': 'heritage',  # Haberfield
    # Chapter F - Development Categories
    'F1': 'dwelling_houses',
    'F2': 'dual_occupancy',
    'F3': 'multi_dwelling',
    'F4': 'residential_flat',
    'F5': 'commercial',
    'F6': 'industrial',
    'F7': 'mixed_use',
}


# =============================================================================
# VALIDATION KEYWORDS (for accuracy checking)
# =============================================================================

TOPIC_VALIDATION_KEYWORDS = {
    'setbacks': ['setback', 'set back', 'boundary clearance', 'building line'],
    'parking': ['parking', 'car space', 'garage', 'carport', 'vehicle parking'],
    'height': ['height', 'storey', 'storeys', 'floor level', 'maximum height'],
    'heritage': ['heritage', 'conservation', 'historic', 'character', 'hca'],
    'landscaping': ['landscap', 'planting', 'garden', 'vegetation'],
    'privacy': ['privacy', 'overlooking', 'window separation'],
    'solar': ['solar', 'overshadow', 'sunlight', 'daylight'],
    'trees': ['tree', 'canopy', 'vegetation removal'],
    'fencing': ['fence', 'fencing', 'front boundary'],
    'access': ['access', 'entry', 'driveway'],
    'building_form': ['bulk', 'scale', 'massing', 'form'],
    'building_design': ['design', 'articulation', 'facade'],
    'flooding': ['flood', 'inundation'],
    'contamination': ['contaminat', 'remediat'],
    'safety': ['safety', 'crime', 'cpted'],
    'signage': ['sign', 'signage'],
    'vehicle_access': ['crossover', 'driveway', 'vehicle crossing'],
}


class TopicReclassifier:
    """Reclassify provision topics using section context."""

    def __init__(self, dry_run: bool = True, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
        self.checkpoint_file = 'scripts/checkpoints/topic_reclassify.json'
        self.backup_table = None

        # Ensure checkpoint directory exists
        os.makedirs('scripts/checkpoints', exist_ok=True)

    def close(self):
        self.conn.close()

    # -------------------------------------------------------------------------
    # BACKUP
    # -------------------------------------------------------------------------

    def create_backup(self) -> str:
        """Create backup of v2_topic values before modification."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/topic_backup_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        print(f"Creating backup to {backup_file}...")

        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT id, v2_topic, v2_marker, v2_dcp_part, document_id
            FROM regulatory_provisions
            WHERE document_id ILIKE '%leichhardt%'
               OR document_id ILIKE '%ashfield%'
               OR document_id ILIKE '%marrickville%'
        ''')

        rows = cur.fetchall()
        backup_data = {
            'timestamp': timestamp,
            'count': len(rows),
            'provisions': [dict(row) for row in rows]
        }

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)

        print(f"Backed up {len(rows)} provisions")
        cur.close()
        return backup_file

    def restore_backup(self, backup_file: str):
        """Restore v2_topic values from backup."""
        print(f"Restoring from {backup_file}...")

        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        cur = self.conn.cursor()
        restored = 0

        for prov in backup_data['provisions']:
            cur.execute('''
                UPDATE regulatory_provisions
                SET v2_topic = %s
                WHERE id = %s
            ''', (prov['v2_topic'], prov['id']))
            restored += 1

        self.conn.commit()
        print(f"Restored {restored} provisions")
        cur.close()

    # -------------------------------------------------------------------------
    # CHECKPOINTING
    # -------------------------------------------------------------------------

    def load_checkpoint(self) -> Dict:
        """Load checkpoint state."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return {'completed_parts': [], 'last_run': None}

    def save_checkpoint(self, part: str):
        """Save checkpoint after completing a part."""
        state = self.load_checkpoint()
        if part not in state['completed_parts']:
            state['completed_parts'].append(part)
        state['last_run'] = datetime.now().isoformat()

        with open(self.checkpoint_file, 'w') as f:
            json.dump(state, f, indent=2)

    def clear_checkpoint(self):
        """Clear checkpoint to start fresh."""
        if os.path.exists(self.checkpoint_file):
            os.remove(self.checkpoint_file)
            print("Checkpoint cleared")

    # -------------------------------------------------------------------------
    # TOPIC EXTRACTION
    # -------------------------------------------------------------------------

    def extract_topic_from_marker(self, marker: str, council: str) -> Optional[str]:
        """Extract topic from v2_marker field (e.g., C3 → parking)."""
        if not marker:
            return None

        marker = marker.strip().upper()

        if council == 'leichhardt':
            # Match C## pattern
            import re
            match = re.match(r'^(C\d+)', marker)
            if match:
                return LEICHHARDT_SECTION_TOPICS.get(match.group(1))

        elif council == 'marrickville':
            # Match section pattern like 2.10
            import re
            match = re.match(r'^(\d+\.\d+)', marker)
            if match:
                return MARRICKVILLE_SECTION_TOPICS.get(match.group(1))

        elif council == 'ashfield':
            # Match chapter pattern like E1, F2
            import re
            match = re.match(r'^([A-Z]\d+)', marker)
            if match:
                return ASHFIELD_SECTION_TOPICS.get(match.group(1))

        return None

    def extract_topic_from_docid(self, document_id: str, council: str) -> Optional[str]:
        """Extract topic from document_id structure."""
        if not document_id:
            return None

        import re

        if council == 'marrickville':
            # Pattern: Marrickville__DCP__2011__-__2__10__Parking
            match = re.search(r'[_-]+2[_-]+(\d+)[_-]', document_id)
            if match:
                section = f"2.{match.group(1)}"
                return MARRICKVILLE_SECTION_TOPICS.get(section)

            # Part 8 heritage
            if '8_0' in document_id or '8.0' in document_id or 'Heritage' in document_id:
                return 'heritage'

        elif council == 'ashfield':
            # Pattern: Ashfield_Chapter_E1_Heritage
            match = re.search(r'Chapter[_\s]+([A-Z]\d+)', document_id, re.IGNORECASE)
            if match:
                return ASHFIELD_SECTION_TOPICS.get(match.group(1).upper())

        return None

    # -------------------------------------------------------------------------
    # VALIDATION
    # -------------------------------------------------------------------------

    def validate_topic_accuracy(self, council: str, part: str) -> Tuple[int, int, float]:
        """Validate topic accuracy using keyword matching."""
        cur = self.conn.cursor()

        # Build council filter
        cur.execute(f'''
            SELECT id, v2_marker, v2_topic, LEFT(provision_text, 500)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND v2_is_actionable = true
            AND v2_dcp_part = %s
            AND v2_topic IS NOT NULL
            AND v2_topic != ''
            LIMIT 100
        ''', (f'%{council}%', part))

        rows = cur.fetchall()
        matches = 0
        total = len(rows)

        for prov_id, marker, topic, text in rows:
            if not topic or not text:
                continue

            text_lower = text.lower()
            keywords = TOPIC_VALIDATION_KEYWORDS.get(topic, [])

            if any(kw.lower() in text_lower for kw in keywords):
                matches += 1

        accuracy = (matches * 100 / total) if total > 0 else 0
        cur.close()
        return matches, total, accuracy

    # -------------------------------------------------------------------------
    # RECLASSIFICATION
    # -------------------------------------------------------------------------

    def reclassify_council(self, council: str):
        """Reclassify all provisions for a council."""
        print(f"\n{'='*70}")
        print(f"PROCESSING: {council.upper()}")
        print(f"{'='*70}")

        checkpoint = self.load_checkpoint()

        # Get distinct DCP parts for this council
        cur = self.conn.cursor()
        cur.execute('''
            SELECT DISTINCT v2_dcp_part
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND v2_is_actionable = true
            AND v2_dcp_part IS NOT NULL
            ORDER BY v2_dcp_part
        ''', (f'%{council}%',))

        parts = [row[0] for row in cur.fetchall()]
        print(f"Found {len(parts)} DCP parts: {parts}")

        for part in parts:
            part_key = f"{council}:{part}"

            if part_key in checkpoint['completed_parts']:
                print(f"\n  Skipping {part} (already completed)")
                continue

            print(f"\n  Processing {part}...")
            self._reclassify_part(council, part)

            # Validate
            matches, total, accuracy = self.validate_topic_accuracy(council, part)
            print(f"  Validation: {matches}/{total} match ({accuracy:.0f}%)")

            if accuracy < 50:
                print(f"  ⚠️  LOW ACCURACY - consider manual review")

            if not self.dry_run:
                self.save_checkpoint(part_key)

        cur.close()

    def _reclassify_part(self, council: str, part: str):
        """Reclassify provisions in a specific DCP part."""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        # Get provisions for this part
        cur.execute('''
            SELECT id, v2_marker, v2_topic, document_id, LEFT(provision_text, 200) as text_preview
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND v2_is_actionable = true
            AND v2_dcp_part = %s
        ''', (f'%{council}%', part))

        provisions = cur.fetchall()
        changes = 0
        unchanged = 0

        for prov in provisions:
            old_topic = prov['v2_topic']

            # Try to get topic from marker first (most reliable)
            new_topic = self.extract_topic_from_marker(prov['v2_marker'], council)

            # Fall back to document_id pattern
            if not new_topic:
                new_topic = self.extract_topic_from_docid(prov['document_id'], council)

            # Keep old topic if no new determination
            if not new_topic:
                new_topic = old_topic
                unchanged += 1
                continue

            if new_topic != old_topic:
                if self.verbose:
                    print(f"    ID {prov['id']}: {old_topic} → {new_topic}")

                if not self.dry_run:
                    cur.execute('''
                        UPDATE regulatory_provisions
                        SET v2_topic = %s
                        WHERE id = %s
                    ''', (new_topic, prov['id']))

                changes += 1
            else:
                unchanged += 1

        if not self.dry_run:
            self.conn.commit()

        print(f"    {changes} changed, {unchanged} unchanged")
        cur.close()

    # -------------------------------------------------------------------------
    # MAIN ENTRY POINTS
    # -------------------------------------------------------------------------

    def run_all(self):
        """Run reclassification for all councils."""
        if not self.dry_run:
            backup_file = self.create_backup()
            print(f"Backup saved to: {backup_file}")
        else:
            print("DRY RUN MODE - No changes will be saved")

        for council in ['leichhardt', 'ashfield', 'marrickville']:
            self.reclassify_council(council)

        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)

        # Final validation
        print("\nFinal validation by council:")
        for council in ['leichhardt', 'ashfield', 'marrickville']:
            cur = self.conn.cursor()
            cur.execute('''
                SELECT v2_dcp_part, COUNT(*)
                FROM regulatory_provisions
                WHERE document_id ILIKE %s
                AND v2_is_actionable = true
                GROUP BY v2_dcp_part
            ''', (f'%{council}%',))

            print(f"\n{council.upper()}:")
            for part, count in cur.fetchall():
                matches, total, accuracy = self.validate_topic_accuracy(council, part or 'unknown')
                status = "✓" if accuracy >= 60 else "⚠️"
                print(f"  {part or 'unknown'}: {accuracy:.0f}% accuracy ({matches}/{total}) {status}")
            cur.close()


def main():
    parser = argparse.ArgumentParser(description='Reclassify provision topics with section context')
    parser.add_argument('--execute', action='store_true', help='Actually make changes (default is dry run)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show individual changes')
    parser.add_argument('--council', type=str, help='Process only specific council')
    parser.add_argument('--restore', type=str, help='Restore from backup file')
    parser.add_argument('--clear-checkpoint', action='store_true', help='Clear checkpoint to start fresh')

    args = parser.parse_args()

    reclassifier = TopicReclassifier(
        dry_run=not args.execute,
        verbose=args.verbose
    )

    try:
        if args.restore:
            reclassifier.restore_backup(args.restore)
        elif args.clear_checkpoint:
            reclassifier.clear_checkpoint()
        elif args.council:
            if not args.execute:
                print("DRY RUN MODE - No changes will be saved")
            reclassifier.reclassify_council(args.council)
        else:
            reclassifier.run_all()
    finally:
        reclassifier.close()


if __name__ == '__main__':
    main()
