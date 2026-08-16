#!/usr/bin/env python3
"""
Analyze why keyword match rate is only ~85%

Categories:
1. LEGITIMATE (not errors):
   - C marker assigned (text may not have keywords)
   - Page-based assignment (Part D)
   - Part default (Chapter E1 heritage)
   - Text discusses topic without our keywords

2. ACTUAL ERRORS:
   - Wrong topic assigned
   - Keywords too narrow
   - Ambiguous text, wrong choice made
"""

import os
import re
from collections import defaultdict
from typing import Optional, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Current keywords (from layer_topic_tagger.py)
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard',
    'height': r'\bheight|storey|floor\s+level|building\s+height',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation',
    'heritage': r'\bheritage|conservation|historic',
    'trees': r'\btree|canopy|vegetation',
    'fencing': r'\bfenc|fence|front\s+boundary\s+treatment',
    'access': r'\baccess|entry|driveway|pedestrian',
    'stormwater': r'\bstormwater|drainage|runoff',
    'waste': r'\bwaste|garbage|recycling|bin',
    'waste_management': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign|signage|advertising',
    'building_form': r'\bbulk|scale|massing|form|character',
    'building_design': r'\bdesign|facade|articulation|materials',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'roofing': r'\broof|pitch|eaves',
    'site_analysis': r'\bsite\s+analysis|context|surroundings',
    'bicycle_parking': r'\bbicycle|bike|cycling',
    'vehicle_access': r'\bvehicle\s+access|driveway|crossover',
    'advertising': r'\badvertis|billboard',
    'views': r'\bview|outlook|vista',
    'energy': r'\benergy|solar\s+panel|renewable|photovoltaic',
    'water': r'\bwater|rainwater|wsud',
    'general': r'\bobjective|aim|purpose|principle',
    'residential': r'\bresidential|dwelling|apartment',
    'commercial': r'\bcommercial|retail|shop',
    'industrial': r'\bindustrial|warehouse',
    'mixed_use': r'\bmixed\s+use',
    'density': r'\bdensity|FSR|floor\s+space',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood',
    'sustainability': r'\bsustainab|BASIX|energy\s+efficien',
    'site_specific': r'\bsite\s+specific|masterplan',
    'environmental': r'\benvironmental|ecology|habitat',
}


def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)


def has_keyword_match(text: str, topic: str) -> bool:
    """Check if text contains keywords for topic"""
    if not text or not topic:
        return False
    pattern = TOPIC_KEYWORDS.get(topic)
    if not pattern:
        return False
    return bool(re.search(pattern, text.lower(), re.IGNORECASE))


def get_all_keyword_matches(text: str) -> Dict[str, int]:
    """Get all topic keyword matches in text"""
    if not text:
        return {}
    matches = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        if found:
            matches[topic] = len(found)
    return matches


def has_c_marker(text: str) -> Optional[str]:
    """Check if text starts with C marker"""
    if not text:
        return None
    match = re.match(r'^(C\d+)', text.strip())
    return match.group(1) if match else None


def analyze_mismatches(council: str = 'Leichhardt'):
    """Analyze keyword mismatches for a council"""
    conn = get_db_connection()

    print("=" * 80)
    print(f"KEYWORD MISMATCH ANALYSIS - {council.upper()}")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
            ORDER BY v2_dcp_part, id
        """, (f'%{council}%',))
        provisions = cur.fetchall()

    print(f"\nTotal provisions with topics: {len(provisions)}")

    # Categorize each provision
    categories = {
        'keyword_match': [],      # Has keywords for assigned topic
        'c_marker_valid': [],     # Assigned by C marker (legitimate)
        'part_default': [],       # Assigned by part default (e.g., heritage chapter)
        'no_keywords_found': [],  # Text has NO keywords at all
        'wrong_topic': [],        # Has keywords for DIFFERENT topic, not assigned
        'missing_keywords': [],   # Topic is likely correct but keywords missing
    }

    for p in provisions:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']
        part = p['v2_dcp_part'] or ''

        has_match = has_keyword_match(text, assigned)
        all_matches = get_all_keyword_matches(text)
        c_marker = has_c_marker(text)

        if has_match:
            categories['keyword_match'].append(p)
        elif c_marker:
            # C marker assignment - legitimate even without keywords
            categories['c_marker_valid'].append({
                **p,
                'c_marker': c_marker,
                'all_matches': all_matches
            })
        elif part == 'Chapter E1' and assigned == 'heritage':
            # Heritage chapter default - legitimate
            categories['part_default'].append(p)
        elif not all_matches:
            # No keywords found at all
            categories['no_keywords_found'].append({
                **p,
                'text_preview': text[:150]
            })
        elif all_matches and assigned not in all_matches:
            # Has keywords for OTHER topics but not assigned
            categories['wrong_topic'].append({
                **p,
                'assigned': assigned,
                'found_topics': all_matches,
                'text_preview': text[:150]
            })
        else:
            # Catch-all
            categories['missing_keywords'].append({
                **p,
                'all_matches': all_matches
            })

    # Print summary
    total = len(provisions)
    print(f"\n{'Category':<30} {'Count':>8} {'%':>8}")
    print("-" * 50)
    for cat, items in categories.items():
        pct = len(items) / total * 100 if total > 0 else 0
        print(f"{cat:<30} {len(items):>8} {pct:>7.1f}%")

    # Analyze "wrong_topic" - these are actual errors
    wrong = categories['wrong_topic']
    if wrong:
        print(f"\n{'='*80}")
        print(f"WRONG TOPIC ANALYSIS ({len(wrong)} provisions)")
        print("=" * 80)

        # Group by assigned topic
        by_assigned = defaultdict(list)
        for p in wrong:
            by_assigned[p['assigned']].append(p)

        print(f"\nBy assigned topic:")
        for topic, items in sorted(by_assigned.items(), key=lambda x: -len(x[1])):
            print(f"\n  {topic}: {len(items)} provisions")

            # What topics SHOULD they be?
            suggested = defaultdict(int)
            for item in items:
                best = max(item['found_topics'].items(), key=lambda x: x[1])
                suggested[best[0]] += 1

            print(f"    Should probably be:")
            for sugg_topic, count in sorted(suggested.items(), key=lambda x: -x[1])[:5]:
                print(f"      {sugg_topic}: {count}")

        # Show examples
        print(f"\nExamples of wrong assignments:")
        for p in wrong[:10]:
            print(f"\n  ID {p['id']} ({p['v2_dcp_part']})")
            print(f"    Assigned: '{p['assigned']}'")
            print(f"    Keywords found: {p['found_topics']}")
            print(f"    Text: {p['text_preview'][:100]}...")

    # Analyze "no_keywords_found" - need better keywords
    no_kw = categories['no_keywords_found']
    if no_kw:
        print(f"\n{'='*80}")
        print(f"NO KEYWORDS FOUND ({len(no_kw)} provisions)")
        print("=" * 80)

        # Group by assigned topic
        by_topic = defaultdict(list)
        for p in no_kw:
            by_topic[p['v2_topic']].append(p)

        print(f"\nBy assigned topic (need keyword expansion):")
        for topic, items in sorted(by_topic.items(), key=lambda x: -len(x[1]))[:10]:
            print(f"\n  {topic}: {len(items)} provisions without matching keywords")
            print(f"    Examples:")
            for item in items[:3]:
                text = item['text_preview'][:80]
                print(f"      {text}...")

    conn.close()

    return categories


def suggest_keyword_improvements(categories):
    """Suggest specific keyword improvements"""
    print(f"\n{'='*80}")
    print("SUGGESTED KEYWORD IMPROVEMENTS")
    print("=" * 80)

    no_kw = categories['no_keywords_found']

    # Analyze common words in provisions without keyword matches
    from collections import Counter

    word_freq = Counter()
    for p in no_kw:
        text = (p.get('provision_text') or p.get('text_preview') or '').lower()
        # Extract significant words (4+ chars, not common)
        words = re.findall(r'\b[a-z]{4,}\b', text)
        stopwords = {'this', 'that', 'with', 'from', 'have', 'been', 'will', 'shall',
                     'must', 'should', 'would', 'could', 'which', 'where', 'when',
                     'their', 'there', 'these', 'those', 'other', 'such', 'than',
                     'into', 'only', 'also', 'most', 'more', 'some', 'each', 'within'}
        words = [w for w in words if w not in stopwords]
        word_freq.update(words)

    print(f"\nMost common words in provisions without keyword matches:")
    for word, count in word_freq.most_common(30):
        print(f"  {word}: {count}")

    print(f"\nSuggested additions to TOPIC_KEYWORDS:")
    suggestions = {
        'building_design': ['development', 'building', 'constructed', 'construction'],
        'general': ['guideline', 'applies', 'following', 'council', 'application'],
        'residential': ['dwelling', 'residential', 'house', 'housing', 'apartment'],
        'precinct': ['area', 'neighbourhood', 'village', 'centre', 'street'],
        'heritage': ['character', 'period', 'significance', 'contributory'],
        'access': ['pedestrian', 'entry', 'movement', 'path', 'connection'],
    }

    for topic, words in suggestions.items():
        current = TOPIC_KEYWORDS.get(topic, '')
        missing = [w for w in words if w not in current.lower()]
        if missing:
            print(f"\n  {topic}:")
            print(f"    Add: {missing}")


if __name__ == '__main__':
    categories = analyze_mismatches('Leichhardt')
    suggest_keyword_improvements(categories)

    print("\n" + "=" * 80)
    categories_ash = analyze_mismatches('Ashfield')
