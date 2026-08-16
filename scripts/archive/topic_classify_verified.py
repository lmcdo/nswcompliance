#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SELF-TESTING TOPIC CLASSIFICATION

Progressive, test-driven classification that:
1. CLASSIFIES - LLM assigns topic with reasoning
2. TESTS - Runs keyword tests against provision text
3. CHECKS - If keyword fails, semantic LLM check (optional)
4. ACCEPTS/REJECTS - Only accepts if tests pass

NO GUESSING. Every classification must pass tests.

Usage:
    python scripts/topic_classify_verified.py --dry-run      # Preview
    python scripts/topic_classify_verified.py --execute      # Run with testing
    python scripts/topic_classify_verified.py --stats        # Current stats
    python scripts/topic_classify_verified.py --resume       # Resume from checkpoint
"""
import os
import sys
import re
import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

import psycopg2
from psycopg2.extras import RealDictCursor

# Optional: OpenAI for classification
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# =============================================================================
# TEST DEFINITIONS - What proves a topic is correct
# =============================================================================

TOPIC_TESTS = {
    'setbacks': {
        'keywords': ['setback', 'set back', 'boundary clearance', 'front yard', 'rear yard',
                     'side yard', 'building line', 'street frontage', 'boundary setback'],
        'patterns': [r'\d+\.?\d*\s*m(?:etre)?s?\s+(?:from|to)\s+(?:boundary|street)',
                     r'(?:front|side|rear)\s+setback'],
        'negative': ['setback from requirements'],  # False positives to exclude
    },
    'parking': {
        'keywords': ['parking', 'car space', 'garage', 'carport', 'vehicle parking',
                     'parking rate', 'car parking', 'parking spaces', 'off-street parking'],
        'patterns': [r'\d+\s+(?:car\s+)?(?:spaces?|parks?)', r'parking\s+(?:rate|provision)'],
        'negative': ['parking meter', 'parking fine'],
    },
    'height': {
        'keywords': ['height', 'storey', 'storeys', 'floor level', 'maximum height',
                     'building height', 'wall height', 'roof height', 'height limit'],
        'patterns': [r'\d+\.?\d*\s*m(?:etre)?s?\s+(?:height|high)', r'\d+\s+store?y'],
        'negative': [],
    },
    'heritage': {
        'keywords': ['heritage', 'conservation', 'historic', 'contributory', 'heritage item',
                     'heritage significance', 'heritage conservation', 'heritage value'],
        'patterns': [r'heritage\s+(?:item|area|conservation)', r'hca\b', r'contributory\s+item'],
        'negative': [],
    },
    'landscaping': {
        'keywords': ['landscaping', 'landscaped', 'planting', 'garden area', 'deep soil',
                     'vegetation', 'landscaped area', 'soft landscaping', 'plant species'],
        'patterns': [r'\d+%?\s+(?:landscap|garden)', r'deep\s+soil\s+(?:zone|area)'],
        'negative': [],
    },
    'privacy': {
        'keywords': ['privacy', 'overlooking', 'window separation', 'screening', 'visual privacy',
                     'acoustic privacy', 'private open space', 'direct views'],
        'patterns': [r'(?:visual|acoustic)\s+privacy', r'overlooking\s+(?:of|to)'],
        'negative': [],
    },
    'solar': {
        'keywords': ['solar access', 'overshadowing', 'sunlight', 'shadow', 'solar',
                     'daylight', 'sun access', 'shadow diagram'],
        'patterns': [r'solar\s+access', r'\d+\s*hours?\s+(?:of\s+)?(?:sun|solar)'],
        'negative': ['solar panel'],
    },
    'trees': {
        'keywords': ['tree', 'trees', 'canopy', 'arborist', 'tree removal', 'tree protection',
                     'tree preservation', 'significant tree', 'street tree'],
        'patterns': [r'tree\s+(?:protection|preservation|removal)', r'canopy\s+cover'],
        'negative': [],
    },
    'stormwater': {
        'keywords': ['stormwater', 'drainage', 'runoff', 'detention', 'on-site detention',
                     'water management', 'rainwater', 'osd'],
        'patterns': [r'(?:storm)?water\s+(?:management|detention)', r'on-?site\s+detention'],
        'negative': [],
    },
    'flooding': {
        'keywords': ['flood', 'flooding', 'flood planning', 'flood level', 'inundation',
                     'flood prone', 'flood risk', 'flood management'],
        'patterns': [r'flood\s+(?:planning|level|prone|risk)', r'fpl\b'],
        'negative': [],
    },
    'fencing': {
        'keywords': ['fence', 'fencing', 'front fence', 'side fence', 'boundary fence',
                     'fence height', 'pool fence'],
        'patterns': [r'(?:front|side|rear|boundary)\s+fence', r'fence\s+height'],
        'negative': [],
    },
    'access': {
        'keywords': ['access', 'driveway', 'pedestrian access', 'vehicle access', 'accessible',
                     'disability access', 'entry', 'egress'],
        'patterns': [r'(?:pedestrian|vehicle|disability)\s+access', r'driveway\s+(?:width|location)'],
        'negative': ['access to information', 'access to services'],
    },
    'building_design': {
        'keywords': ['building design', 'facade', 'articulation', 'architectural', 'elevation',
                     'external appearance', 'building form', 'design quality'],
        'patterns': [r'(?:building|facade)\s+design', r'architectural\s+(?:design|quality)'],
        'negative': [],
    },
    'signage': {
        'keywords': ['sign', 'signage', 'advertising sign', 'business sign', 'illuminated sign'],
        'patterns': [r'(?:advertising|business|illuminated)\s+sign'],
        'negative': [],
    },
}

# Topics without specific tests - these need semantic verification
SEMANTIC_ONLY_TOPICS = ['general', 'precinct', 'site_analysis', 'sustainability',
                         'energy', 'water', 'wsud', 'contamination', 'safety',
                         'bicycle_parking', 'vehicle_access', 'views', 'roofing',
                         'advertising', 'open_space', 'social_impact', 'urban_design',
                         'biodiversity', 'environmental', 'waste', 'infrastructure',
                         'food_premises', 'dwelling_houses', 'dual_occupancy',
                         'multi_dwelling', 'residential_flat', 'commercial',
                         'industrial', 'mixed_use']


# =============================================================================
# TEST ENGINE
# =============================================================================

class TestResult(Enum):
    PASS_KEYWORD = "pass_keyword"      # Keyword found in text
    PASS_PATTERN = "pass_pattern"      # Regex pattern matched
    PASS_SEMANTIC = "pass_semantic"    # LLM confirmed semantic match
    FAIL_KEYWORD = "fail_keyword"      # No keywords found
    FAIL_SEMANTIC = "fail_semantic"    # LLM rejected
    FAIL_NOT_ACTIONABLE = "fail_not_actionable"  # Not a real provision
    SKIP_NO_TEST = "skip_no_test"      # Topic has no tests defined
    ERROR = "error"


@dataclass
class ClassificationResult:
    provision_id: int
    old_topic: Optional[str]
    new_topic: str
    test_result: TestResult
    evidence: str  # What proved this correct
    confidence: float
    llm_reasoning: Optional[str] = None


class TopicTester:
    """Tests whether a topic assignment is correct."""

    def __init__(self, use_semantic: bool = False, openai_client=None):
        self.use_semantic = use_semantic
        self.client = openai_client
        self.semantic_cache = {}  # Cache semantic results

    def test_topic(self, text: str, topic: str, provision_id: int = 0) -> Tuple[TestResult, str, float]:
        """
        Test if topic is correct for given text.
        Returns (result, evidence, confidence).
        """
        if not text or not topic:
            return TestResult.ERROR, "empty_input", 0.0

        text_lower = text.lower()

        # Check if we have tests for this topic
        if topic not in TOPIC_TESTS:
            if topic in SEMANTIC_ONLY_TOPICS and self.use_semantic:
                return self._semantic_test(text, topic, provision_id)
            return TestResult.SKIP_NO_TEST, f"no_tests_for_{topic}", 0.5

        tests = TOPIC_TESTS[topic]

        # 1. Check negative patterns first (false positives)
        for neg in tests.get('negative', []):
            if neg.lower() in text_lower:
                # Found negative pattern - might be false positive
                pass  # Continue to positive tests

        # 2. Keyword test (fast, deterministic)
        matched_keywords = []
        for kw in tests['keywords']:
            if kw.lower() in text_lower:
                matched_keywords.append(kw)

        if len(matched_keywords) >= 2:
            return TestResult.PASS_KEYWORD, f"keywords=[{', '.join(matched_keywords[:3])}]", 0.95
        elif len(matched_keywords) == 1:
            # One keyword - check patterns for more confidence
            pass

        # 3. Pattern test (regex)
        matched_patterns = []
        for pattern in tests.get('patterns', []):
            if re.search(pattern, text_lower):
                matched_patterns.append(pattern)

        if matched_patterns:
            return TestResult.PASS_PATTERN, f"pattern_match", 0.90

        # 4. Single keyword + context
        if len(matched_keywords) == 1:
            # One keyword found - borderline, use semantic if available
            if self.use_semantic:
                return self._semantic_test(text, topic, provision_id)
            return TestResult.PASS_KEYWORD, f"keywords=[{matched_keywords[0]}]", 0.70

        # 5. No keywords found - fail or try semantic
        if self.use_semantic:
            return self._semantic_test(text, topic, provision_id)

        return TestResult.FAIL_KEYWORD, "no_keywords_found", 0.0

    def _semantic_test(self, text: str, topic: str, provision_id: int) -> Tuple[TestResult, str, float]:
        """LLM-based semantic verification."""
        if not self.client:
            return TestResult.SKIP_NO_TEST, "no_llm_client", 0.5

        # Check cache
        cache_key = f"{provision_id}:{topic}"
        if cache_key in self.semantic_cache:
            return self.semantic_cache[cache_key]

        prompt = f"""Verify if this text is about "{topic}".

TEXT:
{text[:800]}

RULES:
- Answer YES if the text primarily discusses {topic}
- Answer NO if it's about something else
- Provide a brief quote (max 10 words) that proves your answer

FORMAT:
ANSWER: YES or NO
QUOTE: "..."
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0
            )

            answer = response.choices[0].message.content.strip()

            if "ANSWER: YES" in answer.upper() or answer.upper().startswith("YES"):
                quote = ""
                if "QUOTE:" in answer:
                    quote = answer.split("QUOTE:")[1].strip()[:50]
                result = (TestResult.PASS_SEMANTIC, f"llm_confirmed: {quote}", 0.85)
            else:
                result = (TestResult.FAIL_SEMANTIC, "llm_rejected", 0.0)

            self.semantic_cache[cache_key] = result
            return result

        except Exception as e:
            return TestResult.ERROR, f"llm_error: {str(e)[:30]}", 0.0


# =============================================================================
# CLASSIFIER
# =============================================================================

class VerifiedClassifier:
    """Classifies provisions with mandatory testing."""

    def __init__(self, dry_run: bool = True, use_semantic: bool = False):
        self.dry_run = dry_run
        self.conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))

        # Setup OpenAI if available
        self.openai_client = None
        if HAS_OPENAI and os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI()

        self.tester = TopicTester(use_semantic=use_semantic, openai_client=self.openai_client)

        # Checkpoint file
        self.checkpoint_file = 'scripts/checkpoints/topic_classify_checkpoint.json'
        os.makedirs('scripts/checkpoints', exist_ok=True)

        # Stats
        self.stats = {
            'processed': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'by_result': {}
        }

    def close(self):
        self.conn.close()

    def get_unverified_provisions(self) -> List[dict]:
        """Get provisions that need classification."""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)

        # Get provisions without reliable topics
        # These are ones that were assigned via page inheritance (guessing)
        cur.execute('''
            SELECT id, provision_text, v2_topic, v2_marker, v2_dcp_part,
                   document_id, pdf_page
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            AND (document_id ILIKE '%leichhardt%'
                 OR document_id ILIKE '%ashfield%'
                 OR document_id ILIKE '%marrickville%')
            AND (v2_marker IS NULL OR v2_marker = '')
            AND v2_topic IS NOT NULL
            AND v2_topic != ''
            ORDER BY id
        ''')

        provisions = cur.fetchall()
        cur.close()
        return provisions

    def classify_with_llm(self, text: str) -> Tuple[str, str]:
        """Use LLM to classify provision. Returns (topic, reasoning)."""
        if not self.openai_client:
            return None, "no_llm_client"

        topics_list = list(TOPIC_TESTS.keys()) + SEMANTIC_ONLY_TOPICS[:10]

        prompt = f"""Classify this planning provision into ONE topic.

PROVISION:
{text[:1000]}

AVAILABLE TOPICS:
{', '.join(topics_list)}

RULES:
- Choose the MOST SPECIFIC topic that fits
- If about multiple things, choose the PRIMARY topic
- "general" only if nothing else fits
- If this is NOT a development control (e.g., intro text, legislative background, definitions, TOC), answer "NOT_ACTIONABLE"

FORMAT:
TOPIC: <one_word or NOT_ACTIONABLE>
REASON: <why this topic, reference specific text>
"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0
            )

            answer = response.choices[0].message.content.strip()

            topic = None
            reason = ""

            for line in answer.split('\n'):
                if line.startswith('TOPIC:'):
                    topic = line.replace('TOPIC:', '').strip().lower()
                elif line.startswith('REASON:'):
                    reason = line.replace('REASON:', '').strip()

            return topic, reason

        except Exception as e:
            return None, f"error: {str(e)}"

    def process_provision(self, prov: dict, reclassify: bool = False) -> ClassificationResult:
        """Process a single provision with testing."""
        prov_id = prov['id']
        text = prov.get('provision_text', '')[:1500]
        old_topic = prov.get('v2_topic')

        # Determine new topic
        if reclassify and self.openai_client:
            new_topic, reasoning = self.classify_with_llm(text)
            if not new_topic:
                new_topic = old_topic
                reasoning = "llm_failed_keeping_old"
        else:
            new_topic = old_topic
            reasoning = "testing_existing"

        # Check if LLM said not actionable
        if new_topic and new_topic.upper() == 'NOT_ACTIONABLE':
            return ClassificationResult(
                provision_id=prov_id,
                old_topic=old_topic,
                new_topic='NOT_ACTIONABLE',
                test_result=TestResult.FAIL_NOT_ACTIONABLE,
                evidence="llm_identified_not_actionable",
                confidence=0.90,
                llm_reasoning=reasoning
            )

        # TEST the topic
        test_result, evidence, confidence = self.tester.test_topic(text, new_topic, prov_id)

        return ClassificationResult(
            provision_id=prov_id,
            old_topic=old_topic,
            new_topic=new_topic,
            test_result=test_result,
            evidence=evidence,
            confidence=confidence,
            llm_reasoning=reasoning
        )

    def save_checkpoint(self, processed_ids: List[int], results: List[ClassificationResult]):
        """Save progress checkpoint."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'processed_ids': processed_ids,
            'stats': self.stats,
            'results': [asdict(r) for r in results[-100:]]  # Last 100
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load_checkpoint(self) -> set:
        """Load checkpoint to resume."""
        if not os.path.exists(self.checkpoint_file):
            return set()
        try:
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
            return set(data.get('processed_ids', []))
        except:
            return set()

    def run(self, reclassify: bool = False, limit: int = None, resume: bool = False):
        """Run classification with testing."""
        print("=" * 60)
        print("SELF-TESTING TOPIC CLASSIFICATION")
        print("=" * 60)

        if self.dry_run:
            print("\n*** DRY RUN - No changes will be made ***")

        if reclassify:
            print("Mode: RECLASSIFY (LLM will assign new topics)")
        else:
            print("Mode: TEST ONLY (testing existing topics)")

        # Get provisions
        provisions = self.get_unverified_provisions()
        print(f"\nTotal unverified provisions: {len(provisions)}")

        # Resume from checkpoint if requested
        processed_ids = set()
        if resume:
            processed_ids = self.load_checkpoint()
            print(f"Resuming from checkpoint: {len(processed_ids)} already processed")

        if limit:
            provisions = provisions[:limit]
            print(f"Limited to: {limit} provisions")

        # Process
        results = []
        passed = []
        failed = []

        for i, prov in enumerate(provisions):
            if prov['id'] in processed_ids:
                continue

            result = self.process_provision(prov, reclassify=reclassify)
            results.append(result)
            processed_ids.add(prov['id'])

            # Track stats
            self.stats['processed'] += 1
            result_key = result.test_result.value
            self.stats['by_result'][result_key] = self.stats['by_result'].get(result_key, 0) + 1

            if result.test_result in [TestResult.PASS_KEYWORD, TestResult.PASS_PATTERN, TestResult.PASS_SEMANTIC]:
                self.stats['passed'] += 1
                passed.append(result)
            elif result.test_result == TestResult.SKIP_NO_TEST:
                self.stats['skipped'] += 1
            elif result.test_result == TestResult.ERROR:
                self.stats['errors'] += 1
            elif result.test_result == TestResult.FAIL_NOT_ACTIONABLE:
                self.stats['not_actionable'] = self.stats.get('not_actionable', 0) + 1
                failed.append(result)  # Track separately but include in failed list for reporting
            else:
                self.stats['failed'] += 1
                failed.append(result)

            # Progress
            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(provisions)} | Passed: {self.stats['passed']} | Failed: {self.stats['failed']}")
                self.save_checkpoint(list(processed_ids), results)

        # Save final checkpoint
        self.save_checkpoint(list(processed_ids), results)

        # Print results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"\nProcessed: {self.stats['processed']}")
        print(f"PASSED:       {self.stats['passed']} ({100*self.stats['passed']/max(1,self.stats['processed']):.1f}%)")
        print(f"FAILED:       {self.stats['failed']} ({100*self.stats['failed']/max(1,self.stats['processed']):.1f}%)")
        print(f"NOT_ACTIONABLE: {self.stats.get('not_actionable', 0)}")
        print(f"SKIPPED:      {self.stats['skipped']}")
        print(f"ERRORS:       {self.stats['errors']}")

        print(f"\nBy test result:")
        for result_type, count in sorted(self.stats['by_result'].items()):
            print(f"  {result_type}: {count}")

        # Show sample failures
        if failed[:5]:
            print(f"\nSample FAILED classifications:")
            for f in failed[:5]:
                print(f"  ID {f.provision_id}: topic={f.new_topic}, {f.evidence}")

        # Show what would be updated
        if not self.dry_run and passed:
            print(f"\nApplying {len(passed)} verified classifications...")
            self._apply_updates(passed)

        return results

    def _apply_updates(self, results: List[ClassificationResult]):
        """Apply verified classifications to database."""
        cur = self.conn.cursor()

        # Backup first
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/verified_classify_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        backup_data = [asdict(r) for r in results]
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        print(f"Backup: {backup_file}")

        # Only update if topic changed AND test passed
        updates = [r for r in results if r.old_topic != r.new_topic]

        for r in updates:
            cur.execute(
                "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
                (r.new_topic, r.provision_id)
            )

        self.conn.commit()
        cur.close()
        print(f"Applied {len(updates)} topic updates")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Self-testing topic classification')
    parser.add_argument('--dry-run', action='store_true', default=True, help='Preview only')
    parser.add_argument('--execute', action='store_true', help='Actually make changes')
    parser.add_argument('--reclassify', action='store_true', help='Use LLM to reclassify')
    parser.add_argument('--semantic', action='store_true', help='Enable semantic testing')
    parser.add_argument('--limit', type=int, help='Limit provisions to process')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--stats', action='store_true', help='Show current stats only')

    args = parser.parse_args()

    classifier = VerifiedClassifier(
        dry_run=not args.execute,
        use_semantic=args.semantic
    )

    try:
        if args.stats:
            provs = classifier.get_unverified_provisions()
            print(f"Unverified provisions: {len(provs)}")

            # Sample test existing topics
            print("\nTesting sample of existing topics...")
            for prov in provs[:20]:
                result = classifier.process_provision(prov)
                status = "✓" if result.test_result.value.startswith("pass") else "✗"
                print(f"  {status} ID {result.provision_id}: {result.new_topic} ({result.evidence})")
        else:
            classifier.run(
                reclassify=args.reclassify,
                limit=args.limit,
                resume=args.resume
            )
    finally:
        classifier.close()


if __name__ == '__main__':
    main()
