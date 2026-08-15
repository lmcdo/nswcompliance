#!/usr/bin/env python3
"""
Improved Topic Tagger for Leichhardt DCP

Improvements over current method:
1. More flexible C marker extraction (not just line start)
2. Weighted keyword scoring (count matches, pick highest)
3. Context-aware disambiguation

This is a REFERENCE IMPLEMENTATION for testing - not production code.
"""

import re
from typing import Optional, Tuple
from collections import defaultdict


# Leichhardt C markers -> topics
LEICHHARDT_C_TOPICS = {
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

# Topic keywords with weights
# Format: {topic: [(pattern, weight), ...]}
# Higher weight = more specific/indicative
WEIGHTED_KEYWORDS = {
    'parking': [
        (r'\bparking\s+space', 3),
        (r'\bcar\s*space', 3),
        (r'\bparking\b', 2),
        (r'\bgarage\b', 2),
        (r'\bvehicle\s+space', 2),
    ],
    'heritage': [
        (r'\bheritage\s+item', 4),
        (r'\bheritage\s+conservation', 4),
        (r'\bHCA\b', 3),
        (r'\bheritage\b', 2),
        (r'\bconservation\s+area', 3),
        (r'\bcontributory\b', 2),
        (r'\bhistoric\b', 1),
    ],
    'trees': [
        (r'\btree\s+preservation', 4),
        (r'\bsignificant\s+tree', 3),
        (r'\btree\s+removal', 3),
        (r'\btree\b', 2),
        (r'\bcanopy\b', 2),
        (r'\barborist', 2),
    ],
    'landscaping': [
        (r'\blandscap(e|ing)\s+plan', 4),
        (r'\blandscap(e|ing)\s+design', 3),
        (r'\bsoft\s+landscap', 3),
        (r'\blandscap', 2),
        (r'\bplanting\b', 1),
        (r'\bgarden\b', 1),
    ],
    'setbacks': [
        (r'\bfront\s+setback', 4),
        (r'\brear\s+setback', 4),
        (r'\bside\s+setback', 4),
        (r'\bsetback\b', 3),
        (r'\bboundary\s+distance', 2),
    ],
    'height': [
        (r'\bbuilding\s+height', 4),
        (r'\bmaximum\s+height', 4),
        (r'\bheight\s+limit', 3),
        (r'\bheight\b', 2),
        (r'\bstorey\b', 2),
        (r'\bFSR\b', 2),
        (r'\bfloor\s+space\s+ratio', 3),
    ],
    'building_form': [
        (r'\bbuilt\s+form', 4),
        (r'\bbulk\s+and\s+scale', 4),
        (r'\bstreetscape', 3),
        (r'\bcharacter\b', 2),
        (r'\bmassing\b', 2),
        (r'\bform\b', 1),
    ],
    'building_design': [
        (r'\barchitectural\b', 3),
        (r'\bfacade\b', 3),
        (r'\barticulation', 3),
        (r'\bmaterials\b', 2),
        (r'\bdesign\b', 1),
    ],
    'solar': [
        (r'\bsolar\s+access', 4),
        (r'\bovershadow', 3),
        (r'\bsunlight', 2),
        (r'\bnorthern\s+aspect', 2),
        (r'\bdaylight\b', 1),
    ],
    'privacy': [
        (r'\bvisual\s+privacy', 4),
        (r'\boverloking', 3),
        (r'\bprivacy\s+screen', 3),
        (r'\bprivacy\b', 2),
    ],
    'access': [
        (r'\bpedestrian\s+access', 4),
        (r'\bdisabled\s+access', 4),
        (r'\buniversal\s+access', 4),
        (r'\bdriveway\b', 2),
        (r'\baccess\b', 1),
    ],
    'open_space': [
        (r'\bprivate\s+open\s+space', 4),
        (r'\bcommunal\s+open\s+space', 4),
        (r'\bopen\s+space', 3),
        (r'\bcourtyard\b', 2),
        (r'\bPOS\b', 2),
    ],
    'stormwater': [
        (r'\bstormwater\s+management', 4),
        (r'\bon-site\s+detention', 3),
        (r'\bOSD\b', 3),
        (r'\bstormwater\b', 2),
        (r'\bdrainage\b', 1),
    ],
    'contamination': [
        (r'\bsite\s+contamination', 4),
        (r'\bsite\s+audit', 3),
        (r'\bremediat', 3),
        (r'\bcontaminat', 2),
        (r'\bhazardous\b', 2),
    ],
    'waste': [
        (r'\bwaste\s+management', 4),
        (r'\bbin\s+storage', 3),
        (r'\brecycling\b', 2),
        (r'\bwaste\b', 2),
    ],
    'flooding': [
        (r'\bflood\s+prone', 4),
        (r'\bflood\s+planning', 3),
        (r'\bflood\s+level', 3),
        (r'\bflood\b', 2),
        (r'\binundation\b', 2),
    ],
    'safety': [
        (r'\bCPTED\b', 4),
        (r'\bcrime\s+prevention', 4),
        (r'\bsurveillance\b', 2),
        (r'\bsafety\b', 2),
        (r'\bsecurity\b', 1),
    ],
    'signage': [
        (r'\bsignage\b', 3),
        (r'\bsign\b', 2),
    ],
    'fencing': [
        (r'\bfront\s+fence', 4),
        (r'\bboundary\s+fence', 3),
        (r'\bfenc(e|ing)\b', 2),
    ],
}


def extract_c_marker_improved(text: str) -> Optional[str]:
    """
    Extract C marker with more flexible matching.

    Looks for C marker:
    1. At start of text (after stripping)
    2. At start of first line
    3. After common prefixes (bullets, numbers)
    """
    if not text:
        return None

    text = text.strip()

    # Pattern 1: Exact start
    match = re.match(r'^(C\d+)\b', text)
    if match:
        return match.group(1)

    # Pattern 2: After common prefix (bullet, number, letter)
    match = re.match(r'^[\s•\-\*\(\)a-z0-9\.]+\s*(C\d+)\b', text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 3: First line only
    first_line = text.split('\n')[0].strip()
    match = re.search(r'\b(C\d+)\b', first_line)
    if match:
        return match.group(1)

    return None


def score_topic_keywords(text: str) -> dict:
    """
    Score topics based on weighted keyword matches.

    Returns {topic: score} dict.
    """
    if not text:
        return {}

    text_lower = text.lower()
    scores = defaultdict(int)

    for topic, patterns in WEIGHTED_KEYWORDS.items():
        for pattern, weight in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            scores[topic] += len(matches) * weight

    return dict(scores)


def get_best_topic(scores: dict, min_score: int = 2) -> Optional[str]:
    """
    Get best topic from scores.

    Args:
        scores: {topic: score} dict
        min_score: Minimum score required to assign topic

    Returns:
        Best topic or None if no topic meets threshold
    """
    if not scores:
        return None

    # Filter by minimum score
    valid = {t: s for t, s in scores.items() if s >= min_score}
    if not valid:
        return None

    # Get topic with highest score
    return max(valid.items(), key=lambda x: x[1])[0]


def extract_topic_improved(text: str, part: str = None) -> Tuple[Optional[str], str]:
    """
    Extract topic using improved method.

    Returns:
        (topic, method) where method describes how topic was determined
    """
    # Step 1: Try C marker (most reliable)
    marker = extract_c_marker_improved(text)
    if marker:
        topic = LEICHHARDT_C_TOPICS.get(marker)
        if topic:
            return (topic, 'c_marker')

    # Step 2: Weighted keyword scoring
    scores = score_topic_keywords(text)
    topic = get_best_topic(scores, min_score=2)
    if topic:
        return (topic, 'weighted_keyword')

    # Step 3: Fallback to 'general' for intro/admin text
    if is_admin_text(text):
        return ('general', 'admin_fallback')

    return (None, 'unknown')


def is_admin_text(text: str) -> bool:
    """Check if text is administrative/introductory"""
    if not text:
        return False

    text_lower = text.lower()

    admin_patterns = [
        r'\bobjective\b',
        r'\bpurpose\b',
        r'\bthis\s+section\b',
        r'\bthis\s+plan\b',
        r'\bcouncil\s+will\b',
        r'\bdevelopment\s+application\b',
    ]

    for pattern in admin_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def compare_methods(text: str):
    """Compare current vs improved method for a provision"""
    # Current method (earliest keyword)
    from layer_topic_tagger import LayerTopicTagger
    tagger = LayerTopicTagger()
    current_topic = tagger._extract_topic_from_text(text)

    # Improved method
    improved_topic, method = extract_topic_improved(text)

    return {
        'text_preview': text[:100] if text else '',
        'current': current_topic,
        'improved': improved_topic,
        'method': method,
        'changed': current_topic != improved_topic
    }


if __name__ == '__main__':
    # Test examples
    test_cases = [
        "C3 Parking must be provided at the rear of the building.",
        "The heritage conservation area requires careful consideration.",
        "Parking requirements for heritage buildings in the area.",
        "Trees and landscaping must be maintained.",
        "This section outlines the objectives for development.",
        "a) C14 The minimum number of parking spaces is...",
    ]

    print("Testing improved topic extraction:")
    print("=" * 80)

    for text in test_cases:
        topic, method = extract_topic_improved(text)
        marker = extract_c_marker_improved(text)
        scores = score_topic_keywords(text)
        top_scores = sorted(scores.items(), key=lambda x: -x[1])[:3]

        print(f"\nText: {text[:60]}...")
        print(f"  C marker: {marker}")
        print(f"  Top scores: {top_scores}")
        print(f"  Result: {topic} (via {method})")
