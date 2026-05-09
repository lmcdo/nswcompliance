#!/usr/bin/env python3
"""
Compliance Type Classifier

Determines HOW a provision should be assessed:
  - numeric_check: Has measurable requirements (6m, 40%, FSR 0.5:1)
  - merit_assessment: Requires professional judgment
  - binary_prohibition: Permitted or not permitted
  - procedural: Submission/process requirements

Uses the provision text and existing enrichment data. Deterministic — no LLM.
"""

import re
from typing import Optional

from enrichment.extractors.rule_schema import ComplianceType


# "must not", "shall not", "is not permitted", "is prohibited", "cannot be"
PROHIBITION_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'\b(must\s+not|shall\s+not|is\s+not\s+permitted|are\s+not\s+permitted)\b',
        r'\b(is\s+prohibited|are\s+prohibited|cannot\s+be|will\s+not\s+be\s+(?:approved|permitted|supported))\b',
        r'\b(not\s+be\s+demolished|not\s+be\s+removed|not\s+be\s+altered)\b',
    ]
]

# "shall submit", "must lodge", "is required to provide", "shall include"
PROCEDURAL_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'\b(must|shall|is\s+required\s+to)\s+(submit|lodge|provide|include|prepare|obtain|demonstrate)\b',
        r'\b(development\s+application\s+must\s+(?:include|be\s+accompanied))\b',
        r'\ba\s+(?:landscape|traffic|heritage|acoustic|arborist|geotechnical)\s+(?:plan|report|study|assessment)\s+(?:must|shall|is\s+required)\b',
        r'\b(?:must|shall)\s+(?:be\s+)?(?:accompanied\s+by|supported\s+by)\b',
    ]
]

# "to the satisfaction", "as determined by", "having regard to", "where appropriate"
MERIT_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'\bto\s+the\s+satisfaction\s+of\s+(?:the\s+)?(?:Council|consent\s+authority)\b',
        r'\bas\s+determined\s+by\s+(?:the\s+)?(?:Council|consent\s+authority)\b',
        r'\bat\s+the\s+discretion\s+of\b',
        r'\bhaving\s+regard\s+to\b',
        r'\bwhere\s+(?:appropriate|possible|practicable)\b',
        r'\bshould\s+be\s+(?:compatible|consistent|sympathetic|appropriate|complementary)\b',
        r'\b(?:respond|contribute|enhance|respect|maintain)\s+(?:the\s+)?(?:character|amenity|streetscape)\b',
        r'\bcompatible\s+with\s+(?:the\s+)?(?:existing|surrounding|established)\b',
    ]
]

# Numeric requirement patterns (already extracted by NumericExtractor,
# but this provides a quick check without running the full extractor)
NUMERIC_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r'\b\d+\.?\d*\s*(?:m|metres?|mm|m²|sqm|storeys?|%)\b',
        r'\bFSR\b.*\d',
        r'\d+:\d+',  # FSR ratios
        r'\b(?:minimum|maximum|at\s+least|no\s+more\s+than|not\s+exceed)\s+\d',
    ]
]


def classify_compliance_type(
    text: str,
    has_numeric_value: Optional[bool] = None,
    section_header: Optional[str] = None,
) -> tuple[str, str]:
    """
    Classify the compliance type of a provision.

    Args:
        text: Provision text
        has_numeric_value: Pre-computed v2_has_numeric_value if available
        section_header: Section header for heading-based rules

    Returns:
        Tuple of (compliance_type: str, reason: str)
    """
    if not text or len(text.strip()) < 10:
        return ComplianceType.MERIT_ASSESSMENT.value, "too_short_default_merit"

    # Heading-based rules (highest priority)
    if section_header:
        h = section_header.strip().lower()
        if "performance criteria" in h:
            return ComplianceType.MERIT_ASSESSMENT.value, "heading_performance_criteria"
        if "design solution" in h:
            return ComplianceType.NUMERIC_CHECK.value, "heading_design_solution"

    # Check prohibition first — "must not" overrides "must + numeric"
    for pattern in PROHIBITION_PATTERNS:
        if pattern.search(text):
            return ComplianceType.BINARY_PROHIBITION.value, "prohibition_language"

    # Check procedural — "shall submit a report"
    for pattern in PROCEDURAL_PATTERNS:
        if pattern.search(text):
            return ComplianceType.PROCEDURAL.value, "submission_requirement"

    # Check numeric — either pre-computed or quick regex
    has_numeric = has_numeric_value
    if has_numeric is None:
        has_numeric = any(p.search(text) for p in NUMERIC_PATTERNS)

    if has_numeric:
        return ComplianceType.NUMERIC_CHECK.value, "has_numeric_requirement"

    # Check merit assessment language
    for pattern in MERIT_PATTERNS:
        if pattern.search(text):
            return ComplianceType.MERIT_ASSESSMENT.value, "merit_language"

    # Default: if it has "must"/"shall" but no numeric, it's likely merit
    if re.search(r'\b(must|shall)\b', text, re.IGNORECASE):
        return ComplianceType.MERIT_ASSESSMENT.value, "control_language_no_numeric"

    return ComplianceType.MERIT_ASSESSMENT.value, "default_merit"
