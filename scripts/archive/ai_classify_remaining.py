#!/usr/bin/env python3
"""
AI classification for remaining topic assignment errors.
Uses Claude Haiku for cost-effective batch classification.
~$0.04 estimated cost for 504 provisions.
"""

import os
import re
import sys
import json
import time
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib
import anthropic

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Valid topics for classification
VALID_TOPICS = [
    'setbacks', 'height', 'parking', 'solar', 'privacy', 'landscaping',
    'heritage', 'trees', 'fencing', 'access', 'stormwater', 'waste',
    'signage', 'building_form', 'building_design', 'open_space', 'flooding',
    'contamination', 'safety', 'residential', 'commercial', 'industrial',
    'precinct', 'general', 'energy', 'environmental', 'water', 'views',
    'mixed_use', 'density', 'food_premises', 'roofing', 'site_specific',
    'sustainability', 'site_analysis'
]

# Expanded keyword patterns for validation
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line',
    'height': r'\bheight|storey|floor\s+level|building\s+height|FSR',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|bicycle',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation|deep\s+soil',
    'heritage': r'\bheritage|conservation|historic|contributory',
    'trees': r'\btree|canopy|arborist',
    'fencing': r'\bfenc|fence',
    'access': r'\baccess|entry|driveway|pedestrian|mobility',
    'stormwater': r'\bstormwater|drainage|runoff|OSD',
    'waste': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign\b|signage|advertising',
    'building_form': r'\bbulk|scale|massing|streetscape',
    'building_design': r'\bfacade|articulation|materials|architectural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'residential': r'\bresidential|dwelling|apartment|house',
    'commercial': r'\bcommercial|retail|shop\b',
    'industrial': r'\bindustrial|warehouse',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood',
    'general': r'\bobjective|aim|purpose|principle',
    'energy': r'\benergy|renewable|thermal|insulation',
    'environmental': r'\benvironmental|ecology|habitat|biodiversity',
    'water': r'\bwater\s+management|rainwater|WSUD',
}


def get_keyword_scores(text):
    if not text:
        return {}
    scores = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)
    return scores


def get_remaining_provisions(conn):
    """Get provisions that still need classification."""
    remaining = []

    for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, provision_text, v2_topic, v2_dcp_part
                FROM regulatory_provisions
                WHERE document_id ILIKE %s
                  AND v2_topic IS NOT NULL
                  AND is_current = TRUE
            """, (f'%{council}%',))
            provisions = cur.fetchall()

        for p in provisions:
            text = p['provision_text'] or ''
            assigned = p['v2_topic']
            part = p['v2_dcp_part'] or ''

            # Skip C markers and part defaults
            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and assigned == 'heritage':
                continue

            scores = get_keyword_scores(text)

            if assigned in scores:
                continue  # Already matched

            # Needs classification
            remaining.append({
                'id': p['id'],
                'council': council,
                'part': part,
                'current_topic': assigned,
                'text': text[:800],  # Limit text length
                'keyword_matches': scores,
            })

    return remaining


def classify_batch(client, provisions, batch_size=10):
    """Classify provisions in batches using Haiku."""
    classifications = []

    topic_list = ', '.join(VALID_TOPICS)

    for i in range(0, len(provisions), batch_size):
        batch = provisions[i:i+batch_size]
        print(f"  Processing batch {i//batch_size + 1}/{(len(provisions)-1)//batch_size + 1}...")

        # Build batch prompt
        batch_items = []
        for j, p in enumerate(batch):
            batch_items.append(f"""
{j+1}. ID: {p['id']}
Current topic: {p['current_topic']}
Text: {p['text'][:400]}
""")

        prompt = f"""You are classifying DCP (Development Control Plan) provisions into topic categories.

Valid topics: {topic_list}

For each provision below, respond with ONLY the provision number and the best topic, one per line.
Format: NUMBER: topic_name
If the current topic is correct, keep it.

Provisions to classify:
{''.join(batch_items)}

Respond with ONLY the classifications, one per line:"""

        try:
            response = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            lines = response.content[0].text.strip().split('\n')
            for line in lines:
                match = re.match(r'(\d+):\s*(\w+)', line.strip())
                if match:
                    idx = int(match.group(1)) - 1
                    topic = match.group(2).strip()
                    if 0 <= idx < len(batch) and topic in VALID_TOPICS:
                        if topic != batch[idx]['current_topic']:
                            classifications.append({
                                'id': batch[idx]['id'],
                                'old_topic': batch[idx]['current_topic'],
                                'new_topic': topic,
                            })

            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            print(f"  Error in batch: {e}")

    return classifications


def main(dry_run=True, max_provisions=None):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print("AI CLASSIFICATION - DRY RUN")
    else:
        print("AI CLASSIFICATION - APPLYING")
    print("=" * 70)

    # Get remaining provisions
    remaining = get_remaining_provisions(conn)
    print(f"\nProvisions needing classification: {len(remaining)}")

    if max_provisions:
        remaining = remaining[:max_provisions]
        print(f"Limited to: {max_provisions}")

    if not remaining:
        print("No provisions need classification!")
        return

    # Initialize Anthropic client
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # Classify
    print("\nClassifying with Haiku...")
    classifications = classify_batch(client, remaining)

    print(f"\nClassifications that would change: {len(classifications)}")

    # Show breakdown
    transitions = defaultdict(int)
    for c in classifications:
        transitions[(c['old_topic'], c['new_topic'])] += 1

    print("\nTop transitions:")
    for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:15]:
        print(f"  {old} -> {new}: {count}")

    if not dry_run and classifications:
        print("\nApplying classifications...")
        with conn.cursor() as cur:
            for c in classifications:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (c['new_topic'], c['id']))
        conn.commit()
        print(f"[OK] Applied {len(classifications)} classifications")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--max', type=int, help='Max provisions to process')
    args = parser.parse_args()
    main(dry_run=args.dry_run, max_provisions=args.max)
