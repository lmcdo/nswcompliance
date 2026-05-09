#!/usr/bin/env python3
"""
Actionable Provision Classifier

Classifies provisions as actionable (development controls) or boilerplate.
Uses regex patterns to identify:
- Boilerplate: Legislative headers, disclaimers, procedural text
- Actionable: Controls, objectives, requirements with substance

This is Phase 0.5 of enrichment - filter before other processing.
"""

import re
from typing import Tuple


class ActionableClassifier:
    """
    Classify provisions as actionable or boilerplate.

    Usage:
        classifier = ActionableClassifier()
        is_actionable, reason = classifier.classify(text, document_id)
    """

    # Patterns that indicate BOILERPLATE (not actionable)
    BOILERPLATE_PATTERNS = [
        # Legislative headers/footers
        r'Parliamentary Counsel',
        r'compiled and maintained',
        r'NSW legislation website',
        r'Interpretation Act',
        r'section 45C',
        r'certified as the form',
        r'usually updated within \d+ working days',
        r'Historical versions',
        r'currency of this information',

        # Empty/placeholder content
        # FIX: Use \A and \Z string anchors instead of ^ and $ line anchors
        # The MULTILINE flag made ^$ match line boundaries, causing false exclusions
        # for provisions with blank lines (e.g., PDF artifacts)
        r'\A[\s\.\-_]+\Z',  # Only matches if ENTIRE string is whitespace/punctuation
        r'^Page \d+',
        r'^\d+$',  # Just a number
        r'^Table of Contents?$',
        r'^Contents$',
        r'^Index$',

        # Administrative text
        r'This Policy is State Environmental Planning Policy',
        r'This Plan is .+ Local Environmental Plan',
        r'made under the Environmental Planning and Assessment Act',
        r'published on the NSW legislation website',
        r'published in .+ Gazette',

        # PDF artifacts
        r'^Figure \d+',
        r'^Map \d+',
        r'^Diagram',
        r'^\[Image\]',
        r'^Source:',
    ]

    # Patterns that indicate ACTIONABLE content
    ACTIONABLE_PATTERNS = [
        # Control language
        r'\b(must|shall|is to|are to|is required|are required)\b',
        r'\b(minimum|maximum|at least|no more than|not exceed)\b',
        r'\b(setback|height|FSR|floor space ratio)\b',
        r'\b(prohibited|permitted|permissible)\b',

        # Numeric controls
        r'\d+\.?\d*\s*(m|metres?|m2|m²|storeys?|%)',
        r'\d+:\d+',  # FSR ratios

        # Objective language
        r'\b(objective|aim|purpose|intent)\b.*\b(to|is|are)\b',
        r'^O\d+\s',  # Numbered objectives like "O1 To ensure..."
        r'^C\d+\s',  # Numbered controls like "C1 Buildings must..."
        r'^P\d+\s',  # Performance criteria

        # DCP-specific patterns
        r'control[s]?\s+appl',
        r'development\s+(must|shall|is to)',
        r'building[s]?\s+(must|shall|is to)',
    ]

    # Document types that are typically actionable
    ACTIONABLE_DOC_PATTERNS = [
        r'DCP',
        r'Development Control Plan',
    ]

    # Document types that need more scrutiny (mixed content)
    # FIX: Use [_ ] character class to match both spaces and underscores
    # Database document IDs use underscores (e.g., Local_Environmental_Plan)
    # but original patterns only matched spaces, causing LEP/SEPP docs to be
    # treated as "Unknown" with stricter 2+ pattern threshold
    MIXED_DOC_PATTERNS = [
        r'LEP',
        r'Local[_ ]Environmental[_ ]Plan',
        r'SEPP',
        r'State[_ ]Environmental[_ ]Planning[_ ]Policy',
    ]

    # DEFINITIVE control language - if present, ALWAYS actionable (no threshold)
    # "must" and "shall" are legally binding language - period.
    DEFINITIVE_CONTROL_PATTERN = r'\b(must|shall)\b'

    def __init__(self):
        """Initialize with compiled patterns."""
        self.boilerplate_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.BOILERPLATE_PATTERNS
        ]
        self.actionable_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.ACTIONABLE_PATTERNS
        ]
        self.actionable_doc_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.ACTIONABLE_DOC_PATTERNS
        ]
        self.mixed_doc_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.MIXED_DOC_PATTERNS
        ]
        self.definitive_control_pattern = re.compile(
            self.DEFINITIVE_CONTROL_PATTERN, re.IGNORECASE
        )

    # Section heading keywords that unambiguously indicate non-actionable or actionable content.
    # Checked against the section_header column before any content analysis.
    NON_ACTIONABLE_HEADING_SUFFIXES = (
        " — Objectives",
        " — General Objectives",
        "— Objectives",
        "— General Objectives",
    )
    ACTIONABLE_HEADING_SUFFIXES = (
        " — Controls",
        " — General Controls",
        " — Design Guidance",
        " — Performance Criteria",
        "— Controls",
        "— General Controls",
        "— Design Guidance",
        "— Performance Criteria",
    )

    def classify(self, text: str, document_id: str = None, section_header: str = None) -> Tuple[bool, str]:
        """
        Classify a provision as actionable or boilerplate.

        Args:
            text:           The provision text
            document_id:    Optional document identifier for context
            section_header: Optional section title for structural heading-based rules.
                            Heading-based decisions take priority over content analysis
                            because they reflect the structural intent of the DCP author
                            (e.g., "Controls" sections are always actionable; "Objectives"
                            sections are always aspirational goals, not controls).

        Returns:
            Tuple of (is_actionable: bool, reason: str)
        """
        # Structural heading rules take priority — they encode the DCP author's intent.
        if section_header:
            h = section_header.strip()
            for suffix in self.ACTIONABLE_HEADING_SUFFIXES:
                if h.endswith(suffix):
                    return True, "heading_controls"
            for suffix in self.NON_ACTIONABLE_HEADING_SUFFIXES:
                if h.endswith(suffix):
                    return False, "heading_objectives"

        if not text or len(text.strip()) < 10:
            return False, "too_short"

        text_clean = text.strip()

        # Check for boilerplate patterns first
        boilerplate_match = None
        for pattern in self.boilerplate_patterns:
            if pattern.search(text_clean):
                boilerplate_match = pattern
                break

        # Count actionable patterns BEFORE rejecting for boilerplate
        # This enables rescue logic for provisions that match boilerplate
        # but have strong actionable signals
        actionable_score = 0
        for pattern in self.actionable_patterns:
            if pattern.search(text_clean):
                actionable_score += 1

        # DEFINITIVE CONTROL: "must" and "shall" are ALWAYS actionable
        # This check comes FIRST - these words mean it's a legal requirement
        # They override boilerplate patterns because the control is real
        has_definitive_control = self.definitive_control_pattern.search(text_clean)
        if has_definitive_control:
            return True, "definitive_control_language"

        # RESCUE LOGIC: If boilerplate matched but actionable score is high,
        # include anyway - the provision likely contains real controls despite
        # matching a boilerplate pattern (e.g., "Figure 1" followed by setback requirements)
        if boilerplate_match:
            if actionable_score >= 3:
                return True, "rescued_high_actionable_score"
            elif actionable_score < 2:
                return False, "boilerplate_pattern"
            # If score is 2, continue to document-type-based decision

        # Check document type
        is_dcp = False
        is_mixed = False
        if document_id:
            for pattern in self.actionable_doc_patterns:
                if pattern.search(document_id):
                    is_dcp = True
                    break
            for pattern in self.mixed_doc_patterns:
                if pattern.search(document_id):
                    is_mixed = True
                    break

        # Decision logic (actionable_score already calculated above)
        if is_dcp:
            # DCP documents: lower threshold, most content is actionable
            if actionable_score >= 1:
                return True, "dcp_with_control_language"
            elif len(text_clean) > 100:
                # DCP text over 100 chars without boilerplate is likely actionable
                return True, "dcp_substantial_text"
            else:
                return False, "dcp_no_indicators"

        elif is_mixed:
            # LEP/SEPP: need stronger signals
            if actionable_score >= 2:
                return True, "lep_sepp_strong_indicators"
            elif actionable_score == 1 and len(text_clean) > 150:
                return True, "lep_sepp_moderate_indicators"
            else:
                return False, "lep_sepp_weak_indicators"

        else:
            # Unknown document type: be conservative
            if actionable_score >= 2:
                return True, "unknown_strong_indicators"
            else:
                return False, "unknown_weak_indicators"


def classify_provision(text: str, document_id: str = None) -> Tuple[bool, str]:
    """Convenience function for classification."""
    classifier = ActionableClassifier()
    return classifier.classify(text, document_id)


# CLI for testing
if __name__ == "__main__":
    test_cases = [
        # Boilerplate examples
        ("This version of the legislation is compiled and maintained by the Parliamentary Counsel's Office", "SEPP_Test"),
        ("Legislation on this site is usually updated within 3 working days", "SEPP_Test"),
        ("Page 42", "DCP_Test"),

        # Actionable examples
        ("Buildings must be setback a minimum of 6 metres from the front boundary.", "Ashfield_DCP"),
        ("Maximum building height is 9m or 2 storeys.", "Marrickville_DCP"),
        ("O1 To ensure development maintains the character of the streetscape.", "DCP_Test"),
        ("C4 The front setback must be at least 6m.", "DCP_Test"),
        ("Development is prohibited on land identified as environmentally sensitive.", "LEP_Test"),
        ("The FSR must not exceed 0.5:1 for residential development.", "LEP_Test"),
    ]

    classifier = ActionableClassifier()

    print("=== Actionable Classifier Tests ===\n")
    for text, doc_id in test_cases:
        is_actionable, reason = classifier.classify(text, doc_id)
        status = "ACTIONABLE" if is_actionable else "BOILERPLATE"
        print(f"[{status}] ({reason})")
        print(f"  Doc: {doc_id}")
        print(f"  Text: {text[:80]}...")
        print()
