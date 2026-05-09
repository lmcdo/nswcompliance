#!/usr/bin/env python3
"""
Cross-Reference Extractor

Detects references to other planning instruments, clauses, and sections
within provision text. Deterministic regex — no LLM.

Output: list of RuleReference dicts with target and relationship.
"""

import re
from typing import List, Dict


# Patterns that indicate the provision defers to another instrument
DEFERS_TO_PATTERNS = [
    # "Refer to Clause 6.20 of the Inner West LEP 2022"
    r'[Rr]efer\s+to\s+((?:Clause|Section|Part|Schedule|Chapter)\s+[\w\.\-]+(?:\s+of\s+(?:the\s+)?[\w\s]+(?:LEP|DCP|SEPP|Act)[\w\s\d]*))',
    # "as required by SEPP (Housing) 2021"
    r'as\s+(?:required|specified|stipulated)\s+(?:by|in|under)\s+((?:SEPP|LEP|DCP|the\s+)[\w\s\(\)\-,]+\d{4})',
    # "in accordance with Clause 4.3"
    r'in\s+accordance\s+with\s+((?:Clause|Section|Part|Schedule|Chapter)\s+[\w\.\-]+(?:\s+of\s+(?:the\s+)?[\w\s]+(?:LEP|DCP|SEPP)[\w\s\d]*))',
]

# Patterns that indicate supplementary requirements
SUPPLEMENTS_PATTERNS = [
    # "Part C1.9 Safety by Design of this Development Control Plan"
    r'(?:Part|Section|Chapter)\s+([\w\.\-]+)\s+[\w\s]+of\s+this\s+(?:DCP|Development\s+Control\s+Plan)',
    # "See also Section 2.5"
    r'[Ss]ee\s+also\s+((?:Section|Part|Clause|Chapter)\s+[\w\.\-]+)',
]

# General cross-reference patterns (relationship inferred from context)
GENERAL_REF_PATTERNS = [
    # "Clause 4.3 of the LEP 2022"
    r'(Clause\s+\d+\.?\d*(?:\.\d+)?)\s+of\s+(?:the\s+)?([\w\s]+(?:LEP|DCP|SEPP)[\w\s\d]*)',
    # "Part B3" or "Section 2.5" standalone references
    r'(?:under|per|see)\s+((?:Part|Section|Chapter)\s+[A-Z]?\d+(?:\.\d+)?)',
    # "Schedule 1" or "Schedule 2"
    r'(Schedule\s+\d+)',
    # "Inner West LEP 2022" instrument references
    r'((?:Inner\s+West|Woollahra|Waverley|North\s+Sydney|City\s+of\s+Sydney|Ku[\-\s]ring[\-\s]gai|Randwick|Canada\s+Bay)\s+(?:LEP|DCP)\s+\d{4})',
    # SEPP references
    r'(SEPP\s*\([\w\s\&]+\)\s*\d{4})',
    # "State Environmental Planning Policy (X) 2021"
    r'(State\s+Environmental\s+Planning\s+Policy\s*\([\w\s\&]+\)\s*\d{4})',
]

# Spatial/map reference patterns
SPATIAL_PATTERNS = [
    r'(?:as\s+)?(?:shown|identified|indicated|depicted)\s+(?:on|in)\s+(?:the\s+)?(?:Map|Figure|Diagram)\s+\d+',
    r'(?:Map|Figure|Diagram)\s+\d+',
    r'Height\s+of\s+Buildings\s+Map',
    r'Land\s+Zoning\s+Map',
    r'Heritage\s+Map',
    r'Flood\s+Planning\s+Map',
    r'!\[.*?\]\(.*?\)',  # Markdown image references
]


def extract_references(text: str) -> List[Dict]:
    """Extract cross-references from provision text.

    Returns list of dicts: {"target": str, "relationship": str}
    """
    refs = []
    seen_targets = set()

    # Defers-to references
    for pattern in DEFERS_TO_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            target = match.group(1).strip()
            target = _clean_target(target)
            if target and target not in seen_targets:
                refs.append({"target": target, "relationship": "defers_to"})
                seen_targets.add(target)

    # Supplements references
    for pattern in SUPPLEMENTS_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            target = match.group(1).strip()
            target = _clean_target(target)
            if target and target not in seen_targets:
                refs.append({"target": target, "relationship": "supplements"})
                seen_targets.add(target)

    # General references (default to see_also)
    for pattern in GENERAL_REF_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Combine all groups into target
            groups = [g for g in match.groups() if g]
            target = " ".join(groups).strip()
            target = _clean_target(target)
            if target and target not in seen_targets:
                refs.append({"target": target, "relationship": "see_also"})
                seen_targets.add(target)

    return refs


def detect_spatial_component(text: str) -> bool:
    """Check if provision references maps, figures, or diagrams."""
    for pattern in SPATIAL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def _clean_target(target: str) -> str:
    """Normalise a reference target string."""
    # Remove trailing punctuation
    target = target.rstrip('.,;:')
    # Collapse whitespace
    target = re.sub(r'\s+', ' ', target).strip()
    # Remove very short targets (probably false positives)
    if len(target) < 4:
        return ""
    return target
