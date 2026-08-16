#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOPIC NORMALIZATION AND VERIFICATION

Step 1: Normalize inconsistent topic casing/naming
Step 2: Test all topics against keyword patterns
Step 3: Report what passes vs fails

Usage:
    python scripts/topic_normalize_and_verify.py --dry-run   # Preview
    python scripts/topic_normalize_and_verify.py --execute   # Apply fixes
"""
import os
import sys
import re
import json
from datetime import datetime
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

import psycopg2
from psycopg2.extras import RealDictCursor


# =============================================================================
# TOPIC NORMALIZATION MAP
# =============================================================================

# Maps all variants to canonical lowercase_underscore form
TOPIC_NORMALIZATION = {
    # Heritage
    'Heritage': 'heritage',
    'heritage': 'heritage',

    # Building form/design
    'Building Form': 'building_form',
    'building_form': 'building_form',
    'Building Design': 'building_design',
    'building_design': 'building_design',

    # Parking
    'Parking': 'parking',
    'parking': 'parking',

    # Access
    'Access': 'access',
    'access': 'access',
    'Vehicle Access': 'vehicle_access',
    'vehicle_access': 'vehicle_access',
    'Bicycle Parking': 'bicycle_parking',
    'bicycle_parking': 'bicycle_parking',

    # Site analysis
    'Site Analysis': 'site_analysis',
    'site_analysis': 'site_analysis',

    # Height
    'Height': 'height',
    'height': 'height',

    # Trees
    'Trees': 'trees',
    'trees': 'trees',

    # Landscaping
    'Landscaping': 'landscaping',
    'landscaping': 'landscaping',

    # Setbacks
    'Setbacks': 'setbacks',
    'setbacks': 'setbacks',

    # Fencing
    'Fencing': 'fencing',
    'fencing': 'fencing',

    # Privacy
    'Privacy': 'privacy',
    'privacy': 'privacy',

    # Solar
    'Solar': 'solar',
    'solar': 'solar',

    # Views
    'Views': 'views',
    'views': 'views',

    # Safety
    'Safety': 'safety',
    'safety': 'safety',

    # Signage
    'Signage': 'signage',
    'signage': 'signage',

    # Stormwater/Water
    'Stormwater': 'stormwater',
    'stormwater': 'stormwater',
    'Water': 'water',
    'water': 'water',
    'wsud': 'wsud',

    # Energy
    'Energy': 'energy',
    'energy': 'energy',

    # Environmental
    'Contamination': 'contamination',
    'contamination': 'contamination',
    'Flooding': 'flooding',
    'flooding': 'flooding',
    'biodiversity': 'biodiversity',
    'environmental': 'environmental',

    # Other
    'Roofing': 'roofing',
    'roofing': 'roofing',
    'Open Space': 'open_space',
    'open_space': 'open_space',
    'Waste': 'waste',
    'waste': 'waste',
    'Food Premises': 'food_premises',
    'food_premises': 'food_premises',

    # General
    'general': 'general',
    'precinct': 'precinct',
    'site_specific': 'site_specific',
    'social_impact': 'social_impact',
    'urban_design': 'urban_design',
}


# =============================================================================
# KEYWORD TESTS - What proves a topic is correct
# =============================================================================

TOPIC_TESTS = {
    'setbacks': {
        'keywords': ['setback', 'set back', 'boundary clearance', 'front yard', 'rear yard',
                     'side yard', 'building line', 'street frontage', 'boundary setback',
                     'front setback', 'side setback', 'rear setback'],
        'patterns': [r'\d+\.?\d*\s*m(?:etre)?s?\s+(?:from|to)\s+(?:boundary|street)',
                     r'(?:front|side|rear)\s+setback'],
    },
    'parking': {
        'keywords': ['parking', 'car space', 'garage', 'carport', 'vehicle parking',
                     'parking rate', 'car parking', 'parking spaces', 'off-street parking',
                     'parking area', 'parking provision'],
        'patterns': [r'\d+\s+(?:car\s+)?(?:spaces?|parks?)', r'parking\s+(?:rate|provision)'],
    },
    'height': {
        'keywords': ['height', 'storey', 'storeys', 'floor level', 'maximum height',
                     'building height', 'wall height', 'roof height', 'height limit',
                     'height control', 'height plane'],
        'patterns': [r'\d+\.?\d*\s*m(?:etre)?s?\s+(?:height|high)', r'\d+\s+store?y'],
    },
    'heritage': {
        'keywords': ['heritage', 'conservation', 'historic', 'contributory', 'heritage item',
                     'heritage significance', 'heritage conservation', 'heritage value',
                     'heritage area', 'character', 'hca'],
        'patterns': [r'heritage\s+(?:item|area|conservation)', r'contributory\s+item'],
    },
    'landscaping': {
        'keywords': ['landscaping', 'landscaped', 'planting', 'garden area', 'deep soil',
                     'vegetation', 'landscaped area', 'soft landscaping', 'plant species',
                     'landscape plan', 'landscape design'],
        'patterns': [r'\d+%?\s+(?:landscap|garden)', r'deep\s+soil\s+(?:zone|area)'],
    },
    'privacy': {
        'keywords': ['privacy', 'overlooking', 'window separation', 'screening', 'visual privacy',
                     'acoustic privacy', 'private open space', 'direct views', 'privacy screen'],
        'patterns': [r'(?:visual|acoustic)\s+privacy', r'overlooking'],
    },
    'solar': {
        'keywords': ['solar access', 'overshadowing', 'sunlight', 'shadow', 'solar',
                     'daylight', 'sun access', 'shadow diagram', 'north facing'],
        'patterns': [r'solar\s+access', r'\d+\s*hours?\s+(?:of\s+)?(?:sun|solar)'],
    },
    'trees': {
        'keywords': ['tree', 'trees', 'canopy', 'arborist', 'tree removal', 'tree protection',
                     'tree preservation', 'significant tree', 'street tree', 'tree management'],
        'patterns': [r'tree\s+(?:protection|preservation|removal)', r'canopy\s+cover'],
    },
    'stormwater': {
        'keywords': ['stormwater', 'drainage', 'runoff', 'detention', 'on-site detention',
                     'water management', 'rainwater', 'osd', 'stormwater management'],
        'patterns': [r'(?:storm)?water\s+(?:management|detention)', r'on-?site\s+detention'],
    },
    'flooding': {
        'keywords': ['flood', 'flooding', 'flood planning', 'flood level', 'inundation',
                     'flood prone', 'flood risk', 'flood management', 'floodplain'],
        'patterns': [r'flood\s+(?:planning|level|prone|risk)', r'fpl\b'],
    },
    'fencing': {
        'keywords': ['fence', 'fencing', 'front fence', 'side fence', 'boundary fence',
                     'fence height', 'pool fence', 'fencing materials'],
        'patterns': [r'(?:front|side|rear|boundary)\s+fence', r'fence\s+height'],
    },
    'access': {
        'keywords': ['access', 'driveway', 'pedestrian access', 'vehicle access', 'accessible',
                     'disability access', 'entry', 'egress', 'accessway', 'pathway'],
        'patterns': [r'(?:pedestrian|vehicle|disability)\s+access', r'driveway\s+(?:width|location)'],
    },
    'building_design': {
        'keywords': ['building design', 'facade', 'articulation', 'architectural', 'elevation',
                     'external appearance', 'design quality', 'materials', 'finishes'],
        'patterns': [r'(?:building|facade)\s+design', r'architectural\s+(?:design|quality)'],
    },
    'building_form': {
        'keywords': ['building form', 'bulk', 'scale', 'massing', 'building envelope',
                     'floor space ratio', 'fsr', 'site coverage', 'building footprint'],
        'patterns': [r'building\s+(?:form|envelope)', r'floor\s+space\s+ratio', r'site\s+coverage'],
    },
    'signage': {
        'keywords': ['sign', 'signage', 'advertising sign', 'business sign', 'illuminated sign',
                     'sign height', 'sign area'],
        'patterns': [r'(?:advertising|business|illuminated)\s+sign'],
    },
    'vehicle_access': {
        'keywords': ['driveway', 'crossover', 'vehicle crossing', 'vehicle access', 'garage entry',
                     'driveway width', 'access point'],
        'patterns': [r'vehicle\s+(?:crossing|access)', r'driveway\s+(?:width|grade)'],
    },
    'bicycle_parking': {
        'keywords': ['bicycle', 'bike parking', 'bicycle parking', 'bike storage', 'cycle',
                     'bicycle facilities', 'end of trip'],
        'patterns': [r'bicycle\s+(?:parking|storage|facilities)'],
    },
    'roofing': {
        'keywords': ['roof', 'roofing', 'roof form', 'roof pitch', 'roof design', 'eaves',
                     'roof materials', 'roof colour'],
        'patterns': [r'roof\s+(?:form|pitch|design|material)'],
    },
    'open_space': {
        'keywords': ['open space', 'private open space', 'communal open space', 'outdoor living',
                     'courtyard', 'balcony', 'terrace'],
        'patterns': [r'(?:private|communal)\s+open\s+space', r'outdoor\s+living'],
    },
    'site_analysis': {
        'keywords': ['site analysis', 'site context', 'site assessment', 'site characteristics',
                     'site constraints', 'site opportunities', 'context analysis'],
        'patterns': [r'site\s+(?:analysis|context|assessment)'],
    },
    'water': {
        'keywords': ['water', 'water efficiency', 'water conservation', 'rainwater tank',
                     'water recycling', 'water sensitive', 'water supply'],
        'patterns': [r'water\s+(?:efficiency|conservation|recycling)', r'rainwater\s+tank'],
    },
    'energy': {
        'keywords': ['energy', 'energy efficiency', 'basix', 'thermal', 'insulation',
                     'solar panels', 'passive design', 'natural ventilation'],
        'patterns': [r'energy\s+(?:efficiency|rating)', r'basix', r'thermal\s+(?:comfort|performance)'],
    },
    'contamination': {
        'keywords': ['contamination', 'contaminated', 'remediation', 'soil contamination',
                     'hazardous', 'site audit', 'environmental assessment'],
        'patterns': [r'(?:soil|site)\s+contamination', r'remediation'],
    },
    'waste': {
        'keywords': ['waste', 'garbage', 'bin storage', 'waste management', 'recycling',
                     'waste collection', 'bin enclosure'],
        'patterns': [r'waste\s+(?:management|storage|collection)', r'bin\s+(?:storage|enclosure)'],
    },
    'safety': {
        'keywords': ['safety', 'crime prevention', 'cpted', 'surveillance', 'lighting',
                     'secure', 'security', 'safe design'],
        'patterns': [r'crime\s+prevention', r'cpted', r'natural\s+surveillance'],
    },
    'wsud': {
        'keywords': ['wsud', 'water sensitive urban design', 'bioretention', 'rain garden',
                     'permeable', 'infiltration'],
        'patterns': [r'water\s+sensitive\s+urban\s+design', r'bioretention'],
    },
}


def test_topic(text: str, topic: str) -> tuple:
    """Test if topic matches text. Returns (passed, evidence, confidence)."""
    if not text or not topic:
        return False, "empty", 0.0

    text_lower = text.lower()

    if topic not in TOPIC_TESTS:
        return None, f"no_test_for_{topic}", 0.0

    tests = TOPIC_TESTS[topic]

    # Keyword test
    matched = [kw for kw in tests['keywords'] if kw.lower() in text_lower]
    if len(matched) >= 2:
        return True, f"keywords={matched[:3]}", 0.95

    # Pattern test
    for pattern in tests.get('patterns', []):
        if re.search(pattern, text_lower):
            return True, "pattern_match", 0.90

    # Single keyword
    if len(matched) == 1:
        return True, f"keyword={matched[0]}", 0.70

    return False, "no_match", 0.0


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()

    dry_run = not args.execute

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 70)
    print("TOPIC NORMALIZATION AND VERIFICATION")
    print("=" * 70)

    if dry_run:
        print("\n*** DRY RUN ***\n")

    # ==========================================================================
    # STEP 1: NORMALIZE TOPICS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("STEP 1: NORMALIZE TOPIC CASING")
    print("=" * 70)

    cur.execute('''
        SELECT id, v2_topic, LEFT(provision_text, 500) as text_sample
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
        AND v2_topic IS NOT NULL
    ''')

    provisions = cur.fetchall()
    print(f"Total provisions with topics: {len(provisions)}")

    # Find normalizations needed
    normalizations = defaultdict(list)
    for prov in provisions:
        old_topic = prov['v2_topic']
        if old_topic in TOPIC_NORMALIZATION:
            new_topic = TOPIC_NORMALIZATION[old_topic]
            if old_topic != new_topic:
                normalizations[f"{old_topic} -> {new_topic}"].append(prov['id'])

    print(f"\nNormalization needed:")
    total_norm = 0
    for change, ids in sorted(normalizations.items(), key=lambda x: -len(x[1])):
        print(f"  {change}: {len(ids)} provisions")
        total_norm += len(ids)

    print(f"\nTotal to normalize: {total_norm}")

    if not dry_run and total_norm > 0:
        # Backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/normalize_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        backup_data = [(prov['id'], prov['v2_topic']) for prov in provisions]
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        print(f"\nBackup: {backup_file}")

        # Apply normalizations
        for prov in provisions:
            old_topic = prov['v2_topic']
            if old_topic in TOPIC_NORMALIZATION:
                new_topic = TOPIC_NORMALIZATION[old_topic]
                if old_topic != new_topic:
                    cur.execute(
                        "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
                        (new_topic, prov['id'])
                    )

        conn.commit()
        print(f"Applied {total_norm} normalizations")

    # ==========================================================================
    # STEP 2: TEST ALL TOPICS
    # ==========================================================================
    print("\n" + "=" * 70)
    print("STEP 2: TEST TOPIC ACCURACY")
    print("=" * 70)

    # Re-fetch with normalized topics
    cur.execute('''
        SELECT id, v2_topic, provision_text
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
        AND v2_topic IS NOT NULL
    ''')

    provisions = cur.fetchall()

    stats = {
        'total': len(provisions),
        'passed': 0,
        'failed': 0,
        'no_test': 0,
        'by_topic': defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0, 'no_test': 0})
    }

    failed_samples = defaultdict(list)

    for prov in provisions:
        topic = prov['v2_topic']
        # Normalize for testing
        if topic in TOPIC_NORMALIZATION:
            topic = TOPIC_NORMALIZATION[topic]

        text = (prov['provision_text'] or '')[:1500]

        passed, evidence, conf = test_topic(text, topic)

        stats['by_topic'][topic]['total'] += 1

        if passed is True:
            stats['passed'] += 1
            stats['by_topic'][topic]['passed'] += 1
        elif passed is False:
            stats['failed'] += 1
            stats['by_topic'][topic]['failed'] += 1
            if len(failed_samples[topic]) < 3:
                failed_samples[topic].append({
                    'id': prov['id'],
                    'text': text[:200]
                })
        else:  # None = no test
            stats['no_test'] += 1
            stats['by_topic'][topic]['no_test'] += 1

    # Print results
    print(f"\nTotal: {stats['total']}")
    print(f"PASSED:  {stats['passed']} ({100*stats['passed']/stats['total']:.1f}%)")
    print(f"FAILED:  {stats['failed']} ({100*stats['failed']/stats['total']:.1f}%)")
    print(f"NO TEST: {stats['no_test']} ({100*stats['no_test']/stats['total']:.1f}%)")

    print(f"\nBy topic (sorted by failure rate):")
    print(f"{'Topic':<20} {'Total':>6} {'Pass':>6} {'Fail':>6} {'NoTest':>6} {'Pass%':>7}")
    print("-" * 60)

    topic_data = []
    for topic, data in stats['by_topic'].items():
        testable = data['passed'] + data['failed']
        pass_rate = 100 * data['passed'] / testable if testable > 0 else -1
        topic_data.append((topic, data, pass_rate))

    # Sort by pass rate (lowest first)
    for topic, data, pass_rate in sorted(topic_data, key=lambda x: (x[2] == -1, x[2])):
        pass_str = f"{pass_rate:.0f}%" if pass_rate >= 0 else "N/A"
        print(f"{topic:<20} {data['total']:>6} {data['passed']:>6} {data['failed']:>6} {data['no_test']:>6} {pass_str:>7}")

    # Show failed samples
    if failed_samples:
        print(f"\n" + "=" * 70)
        print("SAMPLE FAILURES (topic doesn't match text)")
        print("=" * 70)
        for topic, samples in list(failed_samples.items())[:5]:
            print(f"\n{topic}:")
            for s in samples[:2]:
                print(f"  ID {s['id']}: {s['text'][:100]}...")

    cur.close()
    conn.close()

    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Verified accurate: {stats['passed']} ({100*stats['passed']/stats['total']:.1f}%)")
    print(f"Failed verification: {stats['failed']} ({100*stats['failed']/stats['total']:.1f}%)")
    print(f"Need semantic test: {stats['no_test']} ({100*stats['no_test']/stats['total']:.1f}%)")


if __name__ == '__main__':
    main()
