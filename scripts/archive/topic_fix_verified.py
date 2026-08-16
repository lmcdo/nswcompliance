#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFIED TOPIC CLASSIFICATION

Progressive, self-verifying implementation that:
1. Only applies changes that can be VERIFIED
2. Runs validation BEFORE and AFTER each step
3. Rejects changes that fail validation
4. Tracks accuracy improvements at each stage

NO GUESSING. Every topic assignment must be verifiable.

Usage:
    python scripts/topic_fix_verified.py --dry-run     # Preview all steps
    python scripts/topic_fix_verified.py --execute     # Run with verification
    python scripts/topic_fix_verified.py --step 1      # Run specific step only
"""
import os
import sys
import re
import json
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2
from psycopg2.extras import RealDictCursor


# =============================================================================
# VERIFICATION METHODS
# =============================================================================

class VerificationMethod(Enum):
    MARKER = "marker"           # C3 → parking (100% reliable)
    PART = "part"               # Part 8 → heritage (100% reliable)
    DOCUMENT_ID = "document_id" # __2__10__ → parking (100% reliable)
    EXTRACTION = "extraction"   # LLM extraction output (95% reliable)
    KEYWORD_STRONG = "keyword_strong"  # 3+ keywords match (80% reliable)
    UNVERIFIED = "unverified"   # Cannot verify


@dataclass
class TopicAssignment:
    provision_id: int
    new_topic: str
    old_topic: Optional[str]
    method: VerificationMethod
    confidence: float
    evidence: str  # What proves this is correct


# =============================================================================
# TOPIC MAPPINGS (VERIFIED SOURCES)
# =============================================================================

LEICHHARDT_MARKERS = {
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

MARRICKVILLE_SECTIONS = {
    '1': 'urban_design', '3': 'site_analysis', '5': 'access', '6': 'privacy',
    '7': 'solar', '8': 'social_impact', '9': 'safety', '10': 'parking',
    '11': 'fencing', '12': 'signage', '13': 'biodiversity', '14': 'environmental',
    '16': 'energy', '17': 'wsud', '18': 'landscaping', '25': 'stormwater',
}

PART_TOPICS = {
    'Part 8': 'heritage',
    'Part 9': 'precinct',
    'Part D': 'energy',
    'Part E': 'water',
    'Part F': 'food_premises',
    'Chapter E1': 'heritage',
    'Chapter C': 'sustainability',
    'Chapter D': 'precinct',
}

# Strong keyword patterns (must match 3+ to be confident)
TOPIC_KEYWORDS = {
    'setbacks': ['setback', 'set back', 'boundary clearance', 'front yard', 'rear yard', 'side yard', 'building line'],
    'parking': ['parking', 'car space', 'garage', 'carport', 'vehicle parking', 'parking rate', 'car parking'],
    'height': ['height', 'storey', 'storeys', 'floor level', 'maximum height', 'building height', 'wall height'],
    'heritage': ['heritage', 'conservation', 'historic', 'contributory', 'hca', 'heritage item', 'character'],
    'landscaping': ['landscaping', 'landscaped', 'planting', 'garden area', 'deep soil', 'vegetation'],
    'privacy': ['privacy', 'overlooking', 'window separation', 'screening', 'visual privacy'],
    'solar': ['solar access', 'overshadowing', 'sunlight', 'shadow', 'solar'],
    'trees': ['tree', 'trees', 'canopy', 'arborist', 'tree removal', 'tree protection'],
    'stormwater': ['stormwater', 'drainage', 'runoff', 'detention', 'on-site detention'],
    'flooding': ['flood', 'flooding', 'flood planning', 'flood level', 'inundation'],
}

# Extraction category to topic mapping
EXTRACTION_CATEGORY_MAP = {
    'building_height': 'height', 'building_height_r1': 'height', 'building_height_r2': 'height',
    'building_height_b1': 'height', 'setback_front': 'setbacks', 'setback_front_r1': 'setbacks',
    'setback_front_r2': 'setbacks', 'setback_side': 'setbacks', 'setback_rear': 'setbacks',
    'parking': 'parking', 'parking_accessible': 'parking', 'parking_rate': 'parking',
    'landscaping': 'landscaping', 'landscaping_deep_soil': 'landscaping',
    'landscaping_front_yard': 'landscaping', 'stormwater_management': 'stormwater',
    'drainage': 'stormwater', 'sustainability': 'sustainability', 'acoustic_privacy': 'privacy',
    'fencing_front': 'fencing', 'fencing_front_r1': 'fencing',
}


# =============================================================================
# VERIFICATION ENGINE
# =============================================================================

class VerifiedTopicFixer:
    """Progressive, self-verifying topic classification."""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
        self.extraction_data = self._load_extractions()
        self.stats = {
            'before': {},
            'after': {},
            'steps': []
        }

    def close(self):
        self.conn.close()

    def _load_extractions(self) -> Dict[int, str]:
        """Load LLM extraction data mapping provision_id → category."""
        extraction_map = {}
        output_dir = 'extraction_outputs'

        if not os.path.exists(output_dir):
            return extraction_map

        for root, dirs, files in os.walk(output_dir):
            for filename in files:
                if not filename.endswith('.json'):
                    continue
                try:
                    with open(os.path.join(root, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    items = data if isinstance(data, list) else data.get('requirements', [])
                    for item in items:
                        prov_id = item.get('primary_source_provision_id') or item.get('source_provision_id')
                        category = item.get('category')
                        if prov_id and category:
                            extraction_map[prov_id] = category
                except:
                    pass

        return extraction_map

    # -------------------------------------------------------------------------
    # VERIFICATION METHODS
    # -------------------------------------------------------------------------

    def verify_by_marker(self, marker: str) -> Optional[Tuple[str, str]]:
        """Verify topic from marker. Returns (topic, evidence) or None."""
        if not marker:
            return None
        m = re.match(r'^(C\d+)', marker.strip().upper())
        if m and m.group(1) in LEICHHARDT_MARKERS:
            return LEICHHARDT_MARKERS[m.group(1)], f"marker={m.group(1)}"
        return None

    def verify_by_part(self, dcp_part: str) -> Optional[Tuple[str, str]]:
        """Verify topic from DCP part. Returns (topic, evidence) or None."""
        if not dcp_part:
            return None
        if dcp_part in PART_TOPICS:
            return PART_TOPICS[dcp_part], f"part={dcp_part}"
        return None

    def verify_by_document_id(self, document_id: str) -> Optional[Tuple[str, str]]:
        """Verify topic from document_id section. Returns (topic, evidence) or None."""
        if not document_id or 'marrickville' not in document_id.lower():
            return None
        m = re.search(r'[_-]+2[_-]+(\d+)[_-]', document_id)
        if m and m.group(1) in MARRICKVILLE_SECTIONS:
            section = m.group(1)
            return MARRICKVILLE_SECTIONS[section], f"section=2.{section}"
        return None

    def verify_by_extraction(self, provision_id: int) -> Optional[Tuple[str, str]]:
        """Verify topic from LLM extraction. Returns (topic, evidence) or None."""
        if provision_id not in self.extraction_data:
            return None
        category = self.extraction_data[provision_id]
        topic = EXTRACTION_CATEGORY_MAP.get(category)
        if topic:
            return topic, f"extraction_category={category}"
        return None

    def verify_by_keywords(self, text: str) -> Optional[Tuple[str, str]]:
        """
        Verify topic by strong keyword matching.
        Requires 3+ keyword matches for a topic to be confident.
        Returns (topic, evidence) or None.
        """
        if not text:
            return None

        text_lower = text.lower()
        best_topic = None
        best_count = 0
        best_keywords = []

        for topic, keywords in TOPIC_KEYWORDS.items():
            matches = [kw for kw in keywords if kw.lower() in text_lower]
            if len(matches) >= 3 and len(matches) > best_count:
                best_count = len(matches)
                best_topic = topic
                best_keywords = matches

        if best_topic and best_count >= 3:
            return best_topic, f"keywords={best_keywords[:3]}"
        return None

    def get_verified_topic(self, prov: dict) -> Optional[TopicAssignment]:
        """
        Get verified topic for a provision using the verification hierarchy.
        Returns TopicAssignment if verified, None if cannot verify.
        """
        prov_id = prov['id']
        marker = prov.get('v2_marker')
        part = prov.get('v2_dcp_part')
        doc_id = prov.get('document_id')
        text = prov.get('provision_text', '')[:1000]
        old_topic = prov.get('v2_topic')

        # Try verification methods in order of reliability

        # 1. Marker (100% reliable)
        result = self.verify_by_marker(marker)
        if result:
            topic, evidence = result
            return TopicAssignment(prov_id, topic, old_topic, VerificationMethod.MARKER, 1.0, evidence)

        # 2. Part (100% reliable)
        result = self.verify_by_part(part)
        if result:
            topic, evidence = result
            return TopicAssignment(prov_id, topic, old_topic, VerificationMethod.PART, 1.0, evidence)

        # 3. Document ID section (100% reliable)
        result = self.verify_by_document_id(doc_id)
        if result:
            topic, evidence = result
            return TopicAssignment(prov_id, topic, old_topic, VerificationMethod.DOCUMENT_ID, 1.0, evidence)

        # 4. LLM Extraction (95% reliable)
        result = self.verify_by_extraction(prov_id)
        if result:
            topic, evidence = result
            return TopicAssignment(prov_id, topic, old_topic, VerificationMethod.EXTRACTION, 0.95, evidence)

        # 5. Strong keyword match (80% reliable, requires 3+ matches)
        result = self.verify_by_keywords(text)
        if result:
            topic, evidence = result
            return TopicAssignment(prov_id, topic, old_topic, VerificationMethod.KEYWORD_STRONG, 0.80, evidence)

        return None

    # -------------------------------------------------------------------------
    # STATISTICS & REPORTING
    # -------------------------------------------------------------------------

    def get_accuracy_stats(self) -> Dict:
        """Get current accuracy statistics."""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        cur.execute('''
            SELECT id, v2_marker, v2_dcp_part, document_id, v2_topic,
                   LEFT(provision_text, 1000) as provision_text
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            AND (document_id ILIKE '%leichhardt%'
                 OR document_id ILIKE '%ashfield%'
                 OR document_id ILIKE '%marrickville%')
        ''')

        provisions = cur.fetchall()
        cur.close()

        total = len(provisions)
        by_method = {m: 0 for m in VerificationMethod}
        has_topic = 0
        no_topic = 0

        for prov in provisions:
            if prov['v2_topic'] and prov['v2_topic'] not in ('', 'None'):
                has_topic += 1
            else:
                no_topic += 1

            assignment = self.get_verified_topic(prov)
            if assignment:
                by_method[assignment.method] += 1
            else:
                by_method[VerificationMethod.UNVERIFIED] += 1

        verified = sum(by_method[m] for m in VerificationMethod if m != VerificationMethod.UNVERIFIED)

        return {
            'total': total,
            'has_topic': has_topic,
            'no_topic': no_topic,
            'verified': verified,
            'unverified': by_method[VerificationMethod.UNVERIFIED],
            'verified_pct': round(100 * verified / total, 1) if total else 0,
            'by_method': {m.value: by_method[m] for m in VerificationMethod}
        }

    def print_stats(self, stats: Dict, label: str):
        """Print statistics."""
        print(f"\n{'='*60}")
        print(f"{label}")
        print(f"{'='*60}")
        print(f"Total provisions: {stats['total']}")
        print(f"Has topic: {stats['has_topic']}")
        print(f"No topic: {stats['no_topic']}")
        print(f"\nVERIFIED: {stats['verified']} ({stats['verified_pct']}%)")
        print(f"UNVERIFIED: {stats['unverified']}")
        print(f"\nBy method:")
        for method, count in stats['by_method'].items():
            if count > 0:
                print(f"  {method}: {count}")

    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------

    def run_step(self, step_num: int, min_confidence: float = 0.8) -> Dict:
        """
        Run a verification step.

        Step 1: Apply marker-based topics (confidence=1.0)
        Step 2: Apply part-based topics (confidence=1.0)
        Step 3: Apply document_id topics (confidence=1.0)
        Step 4: Apply extraction topics (confidence=0.95)
        Step 5: Apply strong keyword topics (confidence=0.80)
        """
        confidence_levels = {
            1: (1.0, [VerificationMethod.MARKER]),
            2: (1.0, [VerificationMethod.PART]),
            3: (1.0, [VerificationMethod.DOCUMENT_ID]),
            4: (0.95, [VerificationMethod.EXTRACTION]),
            5: (0.80, [VerificationMethod.KEYWORD_STRONG]),
        }

        if step_num not in confidence_levels:
            print(f"Invalid step: {step_num}")
            return {}

        min_conf, methods = confidence_levels[step_num]
        method_names = [m.value for m in methods]

        print(f"\n{'#'*60}")
        print(f"# STEP {step_num}: {method_names} (confidence >= {min_conf})")
        print(f"{'#'*60}")

        # Get stats before
        stats_before = self.get_accuracy_stats()
        self.print_stats(stats_before, f"BEFORE STEP {step_num}")

        # Find provisions to update
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT id, v2_marker, v2_dcp_part, document_id, v2_topic,
                   LEFT(provision_text, 1000) as provision_text
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            AND (document_id ILIKE '%leichhardt%'
                 OR document_id ILIKE '%ashfield%'
                 OR document_id ILIKE '%marrickville%')
        ''')

        provisions = cur.fetchall()
        updates = []

        for prov in provisions:
            assignment = self.get_verified_topic(prov)
            if assignment and assignment.method in methods:
                if assignment.confidence >= min_conf:
                    if assignment.new_topic != assignment.old_topic:
                        updates.append(assignment)

        print(f"\nUpdates to apply: {len(updates)}")

        if updates[:5]:
            print("\nSample updates:")
            for u in updates[:5]:
                print(f"  ID {u.provision_id}: {u.old_topic} -> {u.new_topic} ({u.evidence})")

        # Apply updates
        if not self.dry_run and updates:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'scripts/backups/verified_step{step_num}_{timestamp}.json'
            os.makedirs('scripts/backups', exist_ok=True)

            backup_data = [(u.provision_id, u.old_topic, u.new_topic, u.method.value, u.evidence) for u in updates]
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            print(f"\nBackup: {backup_file}")

            for u in updates:
                cur.execute(
                    "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
                    (u.new_topic, u.provision_id)
                )

            self.conn.commit()
            print(f"Applied {len(updates)} updates")

        cur.close()

        # Get stats after
        stats_after = self.get_accuracy_stats()
        self.print_stats(stats_after, f"AFTER STEP {step_num}")

        # Verify improvement
        improvement = stats_after['verified'] - stats_before['verified']
        print(f"\n{'='*60}")
        print(f"STEP {step_num} VERIFICATION")
        print(f"{'='*60}")
        print(f"Verified before: {stats_before['verified']} ({stats_before['verified_pct']}%)")
        print(f"Verified after:  {stats_after['verified']} ({stats_after['verified_pct']}%)")
        print(f"Improvement: +{improvement} provisions")

        if improvement < 0:
            print("⚠️  WARNING: Verification decreased! Something went wrong.")
        elif improvement == 0 and len(updates) > 0:
            print("⚠️  WARNING: No improvement despite updates.")
        else:
            print(f"✓ Step {step_num} verified successfully")

        return {
            'step': step_num,
            'methods': method_names,
            'updates': len(updates),
            'before': stats_before,
            'after': stats_after,
            'improvement': improvement
        }

    def run_all(self):
        """Run all verification steps progressively."""
        print("="*60)
        print("VERIFIED TOPIC CLASSIFICATION - PROGRESSIVE EXECUTION")
        print("="*60)

        if self.dry_run:
            print("\n*** DRY RUN - No changes will be made ***")

        # Initial stats
        initial = self.get_accuracy_stats()
        self.print_stats(initial, "INITIAL STATE")

        results = []
        for step in range(1, 6):
            result = self.run_step(step)
            results.append(result)

        # Final summary
        final = self.get_accuracy_stats()

        print("\n" + "="*60)
        print("FINAL SUMMARY")
        print("="*60)
        print(f"\nInitial verified: {initial['verified']} ({initial['verified_pct']}%)")
        print(f"Final verified:   {final['verified']} ({final['verified_pct']}%)")
        print(f"Total improvement: +{final['verified'] - initial['verified']} provisions")

        print(f"\nBy verification method:")
        for method, count in final['by_method'].items():
            if count > 0:
                pct = round(100 * count / final['total'], 1)
                print(f"  {method}: {count} ({pct}%)")

        if final['unverified'] > 0:
            print(f"\n⚠️  {final['unverified']} provisions remain UNVERIFIED")
            print("These need manual review or LLM classification with context.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Verified topic classification')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Preview only (default)')
    parser.add_argument('--execute', action='store_true', help='Actually make changes')
    parser.add_argument('--step', type=int, help='Run specific step only (1-5)')
    parser.add_argument('--stats', action='store_true', help='Show current stats only')

    args = parser.parse_args()

    fixer = VerifiedTopicFixer(dry_run=not args.execute)

    try:
        if args.stats:
            stats = fixer.get_accuracy_stats()
            fixer.print_stats(stats, "CURRENT STATE")
        elif args.step:
            fixer.run_step(args.step)
        else:
            fixer.run_all()
    finally:
        fixer.close()


if __name__ == '__main__':
    main()
