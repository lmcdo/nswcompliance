#!/usr/bin/env python3
"""
Site Condition Tagger

Tags provisions that only apply when a property has specific site conditions:
- heritage: Heritage items or conservation areas
- flood: Flood prone land
- bushfire: Bushfire prone land

These provisions should be EXCLUDED when the property doesn't have the condition.
"""

import re
from typing import Optional, Tuple


class SiteConditionTagger:
    """
    Tag provisions with required site conditions.

    Usage:
        tagger = SiteConditionTagger()
        condition, confidence = tagger.tag("Heritage items must maintain original facade")
        # condition = "heritage", confidence = "high"
    """

    # Patterns that indicate HERITAGE-SPECIFIC provisions
    HERITAGE_PATTERNS = [
        # Strong indicators (high confidence)
        (r'\bheritage\s+item', 'high'),
        (r'\bheritage\s+conservation\s+area', 'high'),
        (r'\bHCA\b', 'high'),
        (r'\blisted\s+heritage', 'high'),
        (r'\bheritage\s+listed', 'high'),
        (r'\bheritage\s+significance', 'high'),
        (r'\bcontributory\s+item', 'high'),
        (r'\bheritage\s+curtilage', 'high'),
        (r'\bSchedule\s+5\b.*heritage', 'high'),

        # Moderate indicators
        (r'\bconservation\s+area\b', 'medium'),
        (r'\bhistoric\s+character', 'medium'),
        (r'\bheritage\s+value', 'medium'),
        (r'\boriginal\s+fabric', 'medium'),
        (r'\bFederation\s+style', 'medium'),
        (r'\bVictorian\s+style', 'medium'),
        (r'\binter-?war', 'medium'),
    ]

    # Patterns that indicate FLOOD-SPECIFIC provisions
    FLOOD_PATTERNS = [
        # Strong indicators
        (r'\bflood\s+prone', 'high'),
        (r'\bflood\s+planning', 'high'),
        (r'\bflood\s+affected', 'high'),
        (r'\bfloodplain', 'high'),
        (r'\bflood\s+level', 'high'),
        (r'\bflood\s+risk', 'high'),
        (r'\b1[:%]\s+AEP', 'high'),  # 1% Annual Exceedance Probability
        (r'\bPMF\b', 'high'),  # Probable Maximum Flood
        (r'\bflood\s+storage', 'high'),

        # Moderate indicators
        (r'\bflood\s+compatible', 'medium'),
        (r'\bflood\s+evacuation', 'medium'),
        (r'\bflood\s+aware', 'medium'),
    ]

    # Patterns that indicate BUSHFIRE-SPECIFIC provisions
    BUSHFIRE_PATTERNS = [
        # Strong indicators
        (r'\bbushfire\s+prone', 'high'),
        (r'\bbushfire\s+attack\s+level', 'high'),
        (r'\bBAL\b', 'high'),  # Bushfire Attack Level
        (r'\bbushfire\s+hazard', 'high'),
        (r'\bAS\s*3959', 'high'),  # Australian Standard for bushfire
        (r'\bAPZ\b', 'high'),  # Asset Protection Zone
        (r'\basset\s+protection\s+zone', 'high'),
        (r'\binner\s+protection\s+area', 'high'),
        (r'\bouter\s+protection\s+area', 'high'),

        # Moderate indicators
        (r'\bbushfire\s+risk', 'medium'),
        (r'\bfire\s+management', 'medium'),
        (r'\bdefendable\s+space', 'medium'),
    ]

    # Exclusion patterns - these indicate general provisions, not condition-specific
    EXCLUSION_PATTERNS = [
        r'\bexcept\s+(?:for\s+)?heritage',  # "except for heritage items"
        r'\bdoes\s+not\s+apply\s+to\s+heritage',
        r'\bunless\s+.*heritage',
        r'\bother\s+than\s+heritage',
        r'\bexcluding\s+heritage',
    ]

    def __init__(self):
        """Initialize with compiled patterns."""
        self.heritage_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.HERITAGE_PATTERNS
        ]
        self.flood_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.FLOOD_PATTERNS
        ]
        self.bushfire_patterns = [
            (re.compile(p, re.IGNORECASE), conf)
            for p, conf in self.BUSHFIRE_PATTERNS
        ]
        self.exclusion_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.EXCLUSION_PATTERNS
        ]

    def tag(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Tag a provision with its required site condition.

        Args:
            text: The provision text

        Returns:
            Tuple of (condition, confidence) where:
            - condition: "heritage" | "flood" | "bushfire" | None
            - confidence: "high" | "medium" | None
        """
        if not text:
            return None, None

        # Check for exclusion patterns first
        for pattern in self.exclusion_patterns:
            if pattern.search(text):
                # This provision mentions heritage but as an exception
                # It's a general provision, not heritage-specific
                return None, None

        # Check each condition type
        heritage_conf = self._check_patterns(text, self.heritage_patterns)
        flood_conf = self._check_patterns(text, self.flood_patterns)
        bushfire_conf = self._check_patterns(text, self.bushfire_patterns)

        # Return highest confidence match
        results = [
            ('heritage', heritage_conf),
            ('flood', flood_conf),
            ('bushfire', bushfire_conf),
        ]

        # Sort by confidence (high > medium > None)
        conf_order = {'high': 2, 'medium': 1, None: 0}
        results.sort(key=lambda x: conf_order.get(x[1], 0), reverse=True)

        if results[0][1]:  # If best match has a confidence
            return results[0]

        return None, None

    def _check_patterns(self, text: str, patterns: list) -> Optional[str]:
        """Check patterns and return highest confidence match."""
        best_confidence = None
        conf_order = {'high': 2, 'medium': 1}

        for pattern, confidence in patterns:
            if pattern.search(text):
                if best_confidence is None:
                    best_confidence = confidence
                elif conf_order.get(confidence, 0) > conf_order.get(best_confidence, 0):
                    best_confidence = confidence

        return best_confidence


def tag_site_condition(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Convenience function for tagging."""
    tagger = SiteConditionTagger()
    return tagger.tag(text)


# CLI for testing
if __name__ == "__main__":
    test_cases = [
        # Heritage
        "Heritage items must maintain their original facade and roof form.",
        "Development in heritage conservation areas must be sympathetic.",
        "The HCA contains significant Federation architecture.",

        # Flood
        "Flood prone land requires a flood risk assessment.",
        "Floor levels must be 500mm above the 1% AEP flood level.",
        "Development on floodplains must not impede flood storage.",

        # Bushfire
        "Bushfire prone land requires BAL assessment.",
        "Development must comply with AS 3959 for bushfire construction.",
        "Asset Protection Zones must be maintained.",

        # General (no condition)
        "Buildings must be setback 6m from the front boundary.",
        "Maximum building height is 9m.",
        "Except for heritage items, the setback may be reduced.",

        # Edge cases
        "Heritage interpretation signage is encouraged.",
        "Flood lighting must not cause glare.",  # 'flood' but not flood-prone
    ]

    tagger = SiteConditionTagger()

    print("=== Site Condition Tagger Tests ===\n")
    for text in test_cases:
        condition, confidence = tagger.tag(text)
        if condition:
            print(f"[{condition.upper()}] ({confidence})")
        else:
            print("[GENERAL] (no condition required)")
        print(f"  {text[:70]}...")
        print()
