#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAST TOPIC FIX - Two-phase approach

Phase 1: Test existing topics with keywords (NO LLM) - instant
Phase 2: Reclassify failures with LLM (batched)

Usage:
    python scripts/topic_fix_fast.py --phase1           # Test only, show what passes/fails
    python scripts/topic_fix_fast.py --phase2 --limit 100  # LLM reclassify 100 failures
    python scripts/topic_fix_fast.py --phase2 --execute    # Apply LLM fixes
"""
import os
import sys
import re
import json
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

import psycopg2
from psycopg2.extras import RealDictCursor

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


# =============================================================================
# KEYWORD TESTS
# =============================================================================

TOPIC_TESTS = {
    'setbacks': ['setback', 'set back', 'front yard', 'rear yard', 'side yard', 'building line', 'boundary setback',
                 'building envelopes', 'separation from', 'adjoining properties'],
    'parking': ['parking', 'car space', 'garage', 'carport', 'parking rate', 'car parking', 'parking spaces', 'car share',
                'space per', 'spaces per', '1 space', 'visitor spaces'],
    'height': ['height', 'storey', 'storeys', 'maximum height', 'building height', 'wall height', 'height limit'],
    'heritage': ['heritage', 'conservation', 'historic', 'contributory', 'heritage item', 'hca', 'character',
                 'original form', 'original material', 'original joinery', 'original verandah',
                 'victorian', 'federation', 'inter-war', 'bungalow', 'italianate',
                 'archaeological', 'streetscape', 'aesthetic significance', 'roof form', 'chimneys',
                 'front verandah', 'significant elements', 'awning level', 'subdivision',
                 'alterations and additions', 'additions above ground', 'building typologies',
                 'can be seen from the street', 'adapted for new uses', 'significant earlier forms',
                 'gable ends', 'timber shingled', 'face brickwork', 'unsympathetic',
                 'controls apply', 'reasonably be seen'],
    'landscaping': ['landscaping', 'landscaped', 'planting', 'garden area', 'deep soil', 'soft landscaping',
                    'green wall', 'green facade', 'living wall', 'native plants', 'communal open space',
                    'garden structures', 'conservatories', 'gazebos', 'hedges', 'greenway corridor',
                    'fauna', 'landscape documentation', 'communal landscape',
                    'topographic', 'landscape features', 'significant trees', 'sandstone'],
    'privacy': ['privacy', 'overlooking', 'window separation', 'screening', 'visual privacy', 'acoustic privacy'],
    'solar': ['solar access', 'overshadowing', 'sunlight', 'shadow', 'solar', 'daylight', 'north facing'],
    'trees': ['tree', 'trees', 'canopy', 'arborist', 'tree removal', 'tree protection',
              'branch failure', 'limb fall', 'vegetation', 'species', 'ringbark', 'uproot', 'fell'],
    'stormwater': ['stormwater', 'drainage', 'runoff', 'detention', 'on-site detention', 'osd',
                   'swmmp', 'roof areas', 'drained to the street', 'kerb and gutter', 'kerb connection',
                   'drains directly', 'impervious area', 'separators', 'sediment', 'litter traps'],
    'flooding': ['flood', 'flooding', 'flood planning', 'flood level', 'inundation', 'flood prone',
                 'ahd', 'australian height datum', 'surface flows', 'landform'],
    'fencing': ['fence', 'fencing', 'front fence', 'boundary fence', 'fence height'],
    'access': ['access', 'driveway', 'pedestrian access', 'vehicle access', 'accessible', 'entry',
               'public transport', 'pedestrians and cycling', 'disability', 'usable balcony'],
    'building_design': ['building design', 'facade', 'articulation', 'architectural', 'elevation', 'materials',
                        'balconies', 'verandahs', 'awnings', 'corner site', 'street frontage',
                        'high quality appearance', 'fronts, backs and tops',
                        'integral part of the building', 'minimum width', 'living area'],
    'building_form': ['building form', 'bulk', 'scale', 'massing', 'fsr', 'floor space ratio', 'site coverage',
                      'basement', 'structural', 'geotechnical', 'subsurface'],
    'signage': ['sign', 'signage', 'advertising sign', 'business sign', 'banner', 'scaffolding', 'building wrap'],
    'vehicle_access': ['driveway', 'crossover', 'vehicle crossing', 'garage entry', 'driveway width',
                       'loading', 'service vehicle', 'delivery', 'turning area', 'swept path',
                       'forward entering', 'safe movement of vehicles', 'footpath',
                       'turning bays', 'street closure', 'traffic impacts'],
    'bicycle_parking': ['bicycle', 'bike parking', 'bicycle parking', 'bike storage', 'cycle'],
    'roofing': ['roof', 'roofing', 'roof form', 'roof pitch', 'eaves', 'roof materials'],
    'open_space': ['open space', 'private open space', 'communal open space', 'outdoor living', 'balcony',
                   'recreation activities', 'children\'s play', 'sitting areas', 'seating'],
    'site_analysis': ['site analysis', 'site context', 'site assessment', 'site characteristics',
                      'site and context', 'site conditions', 'site opportunities', 'dominant features'],
    'water': ['water', 'water efficiency', 'rainwater tank', 'water recycling', 'water conservation'],
    'energy': ['energy', 'energy efficiency', 'basix', 'thermal', 'insulation', 'passive design',
               'electrical and mechanical', 'heating systems', 'fuel', 'gas or oil',
               'wood burning', 'alterations and additions', 'energy consumption'],
    'contamination': ['contamination', 'contaminated', 'remediation', 'soil contamination', 'hazardous',
                      'hydrocarbon', 'volatile', 'soil sampling', 'site investigation', 'site audit'],
    'waste': ['waste', 'garbage', 'bin storage', 'waste management', 'recycling', 'bins',
              'bin bay', 'bin room', 'presentation space', 'ventilation', 'odour'],
    'safety': ['safety', 'crime prevention', 'cpted', 'surveillance', 'lighting', 'security', 'well lit', 'feel safe',
               'safe, active', 'welcoming public spaces', 'property crime'],
    'wsud': ['wsud', 'water sensitive urban design', 'bioretention', 'rain garden', 'permeable'],
    'views': ['view', 'views', 'view sharing', 'view corridor', 'scenic'],
    'general': ['provisions', 'requirements', 'controls', 'objectives', 'development',
                'allotments', 'boarding house', 'sqm', 'residents', 'amenity', 'noise',
                'wash basin', 'toilet', 'shower', 'kitchen', 'laundry', 'refrigerator',
                'staffing', 'waiting area', 'floor space ratio', 'contributions',
                'sink', 'stove', 'cooker', 'residential uses', 'ground level'],
    'precinct': ['precinct', 'character', 'neighbourhood', 'desired future', 'existing character', 'distinctive',
                 'escarpment', 'rock edges', 'domain interface', 'active land uses'],
    'site_specific': ['site specific', 'norton street', 'johnston street', 'parramatta road', 'applies to',
                      'wharf road', 'chester street', 'birchgrove', 'ballast point'],
    'biodiversity': ['biodiversity', 'endangered', 'threatened species', 'wildlife corridor', 'riparian', 'habitat'],
    'environmental': ['environmental', 'environment', 'ecological', 'natural'],
    'social_impact': ['social impact', 'community', 'social'],
    'sustainability': ['sustainability', 'sustainable', 'ecologically sustainable', 'esd'],
}


def test_topic(text: str, topic: str) -> bool:
    """Quick keyword test. Returns True if topic likely matches."""
    if not text or not topic:
        return False

    text_lower = text.lower()
    keywords = TOPIC_TESTS.get(topic, [])

    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches >= 1


def classify_batch_llm(provisions: list, client) -> dict:
    """Classify multiple provisions with LLM. Returns {id: (topic, reasoning)}."""

    results = {}

    # Process in batches of 5 for parallel API calls
    batch_size = 5

    for i in range(0, len(provisions), batch_size):
        batch = provisions[i:i+batch_size]

        def classify_one(prov):
            text = prov['provision_text'][:800] if prov.get('provision_text') else ''

            prompt = f"""Classify this planning provision into ONE topic.

TEXT: {text}

TOPICS: setbacks, parking, height, heritage, landscaping, privacy, solar, trees,
stormwater, flooding, fencing, access, building_design, building_form, signage,
vehicle_access, bicycle_parking, roofing, open_space, site_analysis, water,
energy, contamination, waste, safety, wsud, views, general, precinct

If NOT a development control (intro text, definitions, TOC), say NOT_ACTIONABLE.

Reply with just: TOPIC_NAME or NOT_ACTIONABLE"""

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=20,
                    temperature=0
                )
                topic = response.choices[0].message.content.strip().lower()
                # Clean up response
                topic = topic.replace('topic:', '').replace('answer:', '').strip()
                if ' ' in topic:
                    topic = topic.split()[0]
                return prov['id'], topic
            except Exception as e:
                return prov['id'], f"error:{str(e)[:20]}"

        # Parallel execution within batch
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(classify_one, p): p for p in batch}
            for future in as_completed(futures):
                prov_id, topic = future.result()
                results[prov_id] = topic

        # Progress
        if (i + batch_size) % 50 == 0:
            print(f"  LLM classified: {min(i + batch_size, len(provisions))}/{len(provisions)}")

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase1', action='store_true', help='Test existing topics (no LLM)')
    parser.add_argument('--phase2', action='store_true', help='LLM reclassify failures')
    parser.add_argument('--execute', action='store_true', help='Apply changes to database')
    parser.add_argument('--limit', type=int, help='Limit provisions to process')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 60)
    print("FAST TOPIC FIX")
    print("=" * 60)

    # Get all provisions
    cur.execute('''
        SELECT id, v2_topic, provision_text, v2_marker
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
        AND v2_topic IS NOT NULL
    ''')
    provisions = cur.fetchall()
    print(f"\nTotal provisions: {len(provisions)}")

    # ==========================================================================
    # PHASE 1: Keyword test all existing topics
    # ==========================================================================
    if args.phase1 or not args.phase2:
        print("\n" + "=" * 60)
        print("PHASE 1: KEYWORD TESTING (instant, no LLM)")
        print("=" * 60)

        passed = []
        failed = []
        no_test = []

        for prov in provisions:
            topic = prov['v2_topic']
            text = prov.get('provision_text', '') or ''

            # Skip if has marker (already reliable)
            if prov.get('v2_marker'):
                passed.append(prov)
                continue

            # Topics without keyword tests
            if topic not in TOPIC_TESTS:
                no_test.append(prov)
                continue

            if test_topic(text, topic):
                passed.append(prov)
            else:
                failed.append(prov)

        print(f"\nPASSED (topic matches text): {len(passed)}")
        print(f"FAILED (topic doesn't match): {len(failed)}")
        print(f"NO TEST (general, precinct, etc.): {len(no_test)}")

        # Breakdown by topic
        failed_by_topic = defaultdict(list)
        for p in failed:
            failed_by_topic[p['v2_topic']].append(p)

        print(f"\nFailed by topic:")
        for topic, provs in sorted(failed_by_topic.items(), key=lambda x: -len(x[1]))[:15]:
            print(f"  {topic}: {len(provs)}")

        # Save failed IDs for phase 2
        with open('scripts/checkpoints/phase1_failed.json', 'w') as f:
            json.dump([p['id'] for p in failed], f)
        print(f"\nSaved {len(failed)} failed IDs to scripts/checkpoints/phase1_failed.json")

    # ==========================================================================
    # PHASE 2: LLM reclassify failures
    # ==========================================================================
    if args.phase2:
        print("\n" + "=" * 60)
        print("PHASE 2: LLM RECLASSIFICATION")
        print("=" * 60)

        if not HAS_OPENAI or not os.getenv('OPENAI_API_KEY'):
            print("ERROR: OpenAI not available")
            return

        client = OpenAI()

        # Load failed IDs
        try:
            with open('scripts/checkpoints/phase1_failed.json', 'r') as f:
                failed_ids = set(json.load(f))
        except FileNotFoundError:
            print("Run --phase1 first to identify failures")
            return

        # Get failed provisions
        failed_provs = [p for p in provisions if p['id'] in failed_ids]
        print(f"Failed provisions to reclassify: {len(failed_provs)}")

        if args.limit:
            failed_provs = failed_provs[:args.limit]
            print(f"Limited to: {args.limit}")

        # LLM classify
        print("\nClassifying with LLM...")
        start = time.time()
        new_topics = classify_batch_llm(failed_provs, client)
        elapsed = time.time() - start
        print(f"Done in {elapsed:.1f}s ({len(new_topics)/elapsed:.1f} provisions/sec)")

        # Analyze results
        changes = []
        not_actionable = []
        errors = []
        same = []

        for prov in failed_provs:
            prov_id = prov['id']
            old_topic = prov['v2_topic']
            new_topic = new_topics.get(prov_id, '')

            if new_topic.startswith('error:'):
                errors.append((prov_id, new_topic))
            elif new_topic == 'not_actionable':
                not_actionable.append(prov_id)
            elif new_topic == old_topic:
                same.append(prov_id)
            elif new_topic:
                changes.append((prov_id, old_topic, new_topic))

        print(f"\nResults:")
        print(f"  Topic changes: {len(changes)}")
        print(f"  NOT_ACTIONABLE: {len(not_actionable)}")
        print(f"  Same topic: {len(same)}")
        print(f"  Errors: {len(errors)}")

        # Sample changes
        if changes[:10]:
            print(f"\nSample topic changes:")
            for pid, old, new in changes[:10]:
                print(f"  ID {pid}: {old} -> {new}")

        # Verify changes pass keyword test
        verified_changes = []
        for prov_id, old_topic, new_topic in changes:
            prov = next((p for p in failed_provs if p['id'] == prov_id), None)
            if prov:
                text = prov.get('provision_text', '') or ''
                if test_topic(text, new_topic):
                    verified_changes.append((prov_id, old_topic, new_topic))

        print(f"\nVerified changes (pass keyword test): {len(verified_changes)}/{len(changes)}")

        # Apply if execute
        if args.execute and (verified_changes or not_actionable):
            print("\nApplying changes...")

            # Backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f'scripts/backups/phase2_llm_{timestamp}.json'
            backup_data = {
                'changes': verified_changes,
                'not_actionable': not_actionable,
                'timestamp': timestamp
            }
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            print(f"Backup: {backup_file}")

            # Apply topic changes
            for prov_id, old_topic, new_topic in verified_changes:
                cur.execute(
                    "UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s",
                    (new_topic, prov_id)
                )

            # Mark not_actionable
            for prov_id in not_actionable:
                cur.execute(
                    "UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s",
                    (prov_id,)
                )

            conn.commit()
            print(f"Applied {len(verified_changes)} topic changes")
            print(f"Marked {len(not_actionable)} as not actionable")

    cur.close()
    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
