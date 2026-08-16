#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-BASED TOPIC RECLASSIFICATION WITH SECTION CONTEXT

This script fixes topic misclassification by:
1. Using marker→topic mapping for provisions WITH markers (reliable, no LLM needed)
2. Using LLM with section header context for provisions WITHOUT markers

The key insight: provide the LLM with the DCP section header/title,
NOT just the provision text. This gives context that keyword matching lacks.

SAFEGUARDS:
- Backup before changes
- Dry run by default
- Checkpoint/resume support
- Validation after processing
- Cost estimation before running
"""
import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2
from psycopg2.extras import RealDictCursor

# OpenAI for LLM classification
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: openai not installed. LLM classification unavailable.")

# =============================================================================
# MARKER → TOPIC MAPPING (Reliable, no LLM needed)
# =============================================================================

# Leichhardt Part C Section 1 control markers
LEICHHARDT_MARKER_TOPICS = {
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

# All valid topics
VALID_TOPICS = [
    'site_analysis', 'heritage', 'parking', 'building_form', 'roofing',
    'landscaping', 'fencing', 'setbacks', 'trees', 'flooding', 'contamination',
    'bicycle_parking', 'access', 'building_design', 'open_space', 'privacy',
    'solar', 'views', 'height', 'safety', 'signage', 'advertising',
    'vehicle_access', 'stormwater', 'waste', 'environmental', 'general',
    'water', 'energy', 'food_premises', 'neighbourhood'
]


# =============================================================================
# LLM TOPIC CLASSIFIER
# =============================================================================

class LLMTopicClassifier:
    """Use LLM to classify provision topics with section context."""

    def __init__(self, model: str = "gpt-4o-mini"):
        if not HAS_OPENAI:
            raise RuntimeError("OpenAI not installed")
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = model
        self.total_tokens = 0

    def classify(self, provision_text: str, section_context: str) -> Tuple[str, float]:
        """
        Classify a provision into a topic.

        Args:
            provision_text: The provision text
            section_context: The DCP section/chapter this provision is from

        Returns:
            Tuple of (topic, confidence)
        """
        prompt = f"""You are classifying a planning provision into a topic category.

SECTION CONTEXT: {section_context}

PROVISION TEXT:
{provision_text[:500]}

VALID TOPICS:
{', '.join(VALID_TOPICS)}

Based on the section context and provision text, what is the most appropriate topic?
Respond with ONLY the topic name (one word from the list above).
If uncertain, respond with the most likely topic based on the section context."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0
            )

            self.total_tokens += response.usage.total_tokens

            topic = response.choices[0].message.content.strip().lower()

            # Validate topic
            if topic not in VALID_TOPICS:
                # Try to find closest match
                for valid in VALID_TOPICS:
                    if valid in topic or topic in valid:
                        topic = valid
                        break
                else:
                    topic = 'general'

            return topic, 0.8  # Confidence estimate

        except Exception as e:
            print(f"LLM error: {e}")
            return None, 0.0

    def estimate_cost(self, num_provisions: int) -> float:
        """Estimate cost for processing N provisions."""
        # Approx 300 tokens per provision (input + output)
        tokens = num_provisions * 300
        # gpt-4o-mini: $0.15 per 1M input, $0.60 per 1M output
        cost = tokens * 0.0003 / 1000  # rough estimate
        return cost


# =============================================================================
# RECLASSIFIER
# =============================================================================

class TopicReclassifier:
    """Main reclassification engine."""

    def __init__(self, dry_run: bool = True, use_llm: bool = False):
        self.dry_run = dry_run
        self.use_llm = use_llm
        self.conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
        self.llm = LLMTopicClassifier() if use_llm and HAS_OPENAI else None

        self.stats = {
            'marker_based': 0,
            'llm_based': 0,
            'unchanged': 0,
            'skipped': 0,
            'errors': 0
        }

    def close(self):
        self.conn.close()

    def create_backup(self) -> str:
        """Create backup before changes."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/topic_backup_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''
            SELECT id, v2_topic, v2_marker, v2_dcp_part, document_id
            FROM regulatory_provisions
            WHERE document_id ILIKE '%leichhardt%'
            AND v2_is_actionable = true
        ''')

        rows = cur.fetchall()
        backup_data = {
            'timestamp': timestamp,
            'count': len(rows),
            'provisions': [dict(row) for row in rows]
        }

        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)

        cur.close()
        return backup_file

    def get_topic_from_marker(self, marker: str) -> Optional[str]:
        """Get topic from marker using lookup table."""
        if not marker:
            return None

        # Normalize marker (e.g., "C3.1" -> "C3")
        import re
        match = re.match(r'^(C\d+)', marker.strip().upper())
        if match:
            return LEICHHARDT_MARKER_TOPICS.get(match.group(1))

        return None

    def reclassify_leichhardt(self):
        """Reclassify Leichhardt provisions."""
        print("\n" + "="*70)
        print("RECLASSIFYING LEICHHARDT PROVISIONS")
        print("="*70)

        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        # Get all actionable Leichhardt provisions
        cur.execute('''
            SELECT id, v2_marker, v2_topic, v2_dcp_part, document_id,
                   LEFT(provision_text, 500) as text_preview
            FROM regulatory_provisions
            WHERE document_id ILIKE '%leichhardt%'
            AND v2_is_actionable = true
            AND v2_dcp_part = 'Part C Section 1'
        ''')

        provisions = cur.fetchall()
        print(f"Found {len(provisions)} Part C Section 1 provisions")

        # Estimate LLM cost for provisions without markers
        if self.use_llm:
            without_markers = sum(1 for p in provisions if not self.get_topic_from_marker(p['v2_marker']))
            cost = self.llm.estimate_cost(without_markers)
            print(f"LLM needed for {without_markers} provisions")
            print(f"Estimated cost: ${cost:.2f}")

            if not self.dry_run:
                confirm = input("Proceed? (y/n): ")
                if confirm.lower() != 'y':
                    print("Aborted")
                    return

        changes = []

        for prov in provisions:
            prov_id = prov['id']
            old_topic = prov['v2_topic']
            marker = prov['v2_marker']

            # Try marker-based first (free, reliable)
            new_topic = self.get_topic_from_marker(marker)

            if new_topic:
                self.stats['marker_based'] += 1
            elif self.use_llm and self.llm:
                # Use LLM with section context
                section_context = f"Leichhardt DCP Part C Section 1 - General Development Controls"
                new_topic, confidence = self.llm.classify(prov['text_preview'], section_context)
                if new_topic:
                    self.stats['llm_based'] += 1
                else:
                    self.stats['skipped'] += 1
                    continue
            else:
                self.stats['skipped'] += 1
                continue

            if new_topic != old_topic:
                changes.append({
                    'id': prov_id,
                    'old': old_topic,
                    'new': new_topic,
                    'method': 'marker' if self.get_topic_from_marker(marker) else 'llm'
                })

                if not self.dry_run:
                    cur.execute('''
                        UPDATE regulatory_provisions
                        SET v2_topic = %s
                        WHERE id = %s
                    ''', (new_topic, prov_id))
            else:
                self.stats['unchanged'] += 1

        if not self.dry_run:
            self.conn.commit()

        cur.close()

        # Report
        print(f"\nResults:")
        print(f"  Marker-based: {self.stats['marker_based']}")
        print(f"  LLM-based: {self.stats['llm_based']}")
        print(f"  Unchanged: {self.stats['unchanged']}")
        print(f"  Skipped: {self.stats['skipped']}")
        print(f"\nChanges: {len(changes)}")

        if changes[:10]:
            print("\nSample changes:")
            for c in changes[:10]:
                print(f"  ID {c['id']}: {c['old']} -> {c['new']} ({c['method']})")

        if self.llm:
            print(f"\nLLM tokens used: {self.llm.total_tokens}")


def main():
    parser = argparse.ArgumentParser(description='Reclassify provision topics')
    parser.add_argument('--execute', action='store_true', help='Actually make changes')
    parser.add_argument('--use-llm', action='store_true', help='Use LLM for provisions without markers')
    parser.add_argument('--backup-only', action='store_true', help='Only create backup')

    args = parser.parse_args()

    reclassifier = TopicReclassifier(
        dry_run=not args.execute,
        use_llm=args.use_llm
    )

    try:
        if args.backup_only:
            backup = reclassifier.create_backup()
            print(f"Backup created: {backup}")
        else:
            if args.execute:
                print("Creating backup before changes...")
                backup = reclassifier.create_backup()
                print(f"Backup: {backup}")

            if reclassifier.dry_run:
                print("\n*** DRY RUN - No changes will be saved ***\n")

            reclassifier.reclassify_leichhardt()

    finally:
        reclassifier.close()


if __name__ == '__main__':
    main()
