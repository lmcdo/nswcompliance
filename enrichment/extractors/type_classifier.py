#!/usr/bin/env python3
"""
Provision Type Classifier

Classifies provisions into types:
- control: Mandatory requirements ("must", "shall", "minimum")
- objective: Goals and purposes ("to ensure", "aim", "purpose")
- definition: Definitions ("means", "includes", "refers to")
- note: Notes and exceptions ("note:", "except where")
- procedural: Process requirements ("applications must submit")

Uses heuristics first, falls back to general classification.
"""

import re
from typing import Tuple, Optional


class TypeClassifier:
    """
    Classify provision type based on text patterns.

    Usage:
        classifier = TypeClassifier()
        prov_type, confidence = classifier.classify("Buildings must be setback 6m")
        # prov_type = "control", confidence = "high"
    """

    # Patterns for CONTROL provisions (mandatory requirements)
    CONTROL_PATTERNS = [
        # Strong indicators
        (r'\b(must|shall)\s+(not\s+)?(be|have|provide|comply|include|ensure|maintain)', 'high'),
        (r'\b(is|are)\s+(to|required\s+to)\b', 'high'),
        (r'\bminimum\s+\d', 'high'),
        (r'\bmaximum\s+\d', 'high'),
        (r'\bmust\s+not\s+exceed', 'high'),
        (r'\b(is|are)\s+prohibited', 'high'),
        (r'\b(is|are)\s+not\s+permitted', 'high'),
        (r'^C\d+[\.\s]', 'high'),  # Numbered controls like "C1. Buildings must..."

        # Moderate indicators
        (r'\brequired\s+to\b', 'medium'),
        (r'\bshall\b', 'medium'),
        (r'\bmust\b', 'medium'),
        (r'\bonly\s+permitted', 'medium'),
    ]

    # Patterns for OBJECTIVE provisions (goals/purposes)
    OBJECTIVE_PATTERNS = [
        # Strong indicators
        (r'^O\d+[\.\s]', 'high'),  # Numbered objectives like "O1. To ensure..."
        (r'^Objective[s]?\s*[:\-]', 'high'),
        (r'^Purpose[s]?\s*[:\-]', 'high'),
        (r'^Aim[s]?\s*[:\-]', 'high'),
        (r'\bObjective[s]?\s*$', 'high'),  # Section header

        # Moderate indicators
        (r'^To\s+(ensure|provide|maintain|protect|encourage|promote|achieve|enhance|minimise|minimize)', 'medium'),
        (r'\bThe\s+objective[s]?\s+(is|are)\b', 'medium'),
        (r'\bThe\s+purpose\s+(is|are)\b', 'medium'),
        (r'\bThe\s+aim\s+(is|are)\b', 'medium'),
    ]

    # Patterns for DEFINITION provisions
    DEFINITION_PATTERNS = [
        # Strong indicators
        (r'^Definition[s]?\s*[:\-]', 'high'),
        (r'\bmeans\s+(the|a|an|any)\b', 'high'),
        (r'\bincludes\s+(the|a|an|any)\b', 'high'),
        (r'\bmeans\s*[:\-]', 'high'),
        (r'\bincludes\s*[:\-]', 'high'),
        (r'\brefers\s+to\b', 'high'),
        (r'\bis\s+defined\s+as\b', 'high'),
        (r'\bhas\s+the\s+same\s+meaning\b', 'high'),
        (r'^\w+\s+means\b', 'high'),  # "Setback means..."

        # Moderate indicators
        (r'"\w+"\s+means', 'medium'),
        (r'\bmeans\b.*\bincluding\b', 'medium'),
        (r'\bfor\s+the\s+purpose\s+of\s+this\b.*\bmeans\b', 'medium'),
    ]

    # Patterns for NOTE provisions
    NOTE_PATTERNS = [
        # Strong indicators
        (r'^Note[s]?\s*[:\-]', 'high'),
        (r'^Note\s*\d+\s*[:\-]', 'high'),
        (r'^NB\s*[:\-]', 'high'),
        (r'^Advisory\s+Note', 'high'),
        (r'^Editor.?s\s+Note', 'high'),

        # Moderate indicators
        (r'^Except\s+where', 'medium'),
        (r'^This\s+does\s+not\s+apply', 'medium'),
        (r'^See\s+also\b', 'medium'),
        (r'^Refer\s+to\b', 'medium'),
    ]

    # Patterns for PROCEDURAL provisions
    PROCEDURAL_PATTERNS = [
        # Strong indicators
        (r'\bapplication[s]?\s+must\s+(include|be accompanied|submit|provide|demonstrate)', 'high'),
        (r'\bsubmit\s+(a|an|the)\b.*\b(application|plan|report|assessment)', 'high'),
        (r'\bdevelopment\s+application\s+must', 'high'),
        (r'\bprior\s+to\s+(lodg|submitt|commenc)', 'high'),

        # Moderate indicators
        (r'\bconsultation\s+(is\s+)?required', 'medium'),
        (r'\bnotification\s+(is\s+)?required', 'medium'),
        (r'\breport\s+must\s+be\s+submitted', 'medium'),
    ]

    def __init__(self):
        """Initialize with compiled patterns."""
        self.patterns = {
            'control': [(re.compile(p, re.IGNORECASE | re.MULTILINE), c) for p, c in self.CONTROL_PATTERNS],
            'objective': [(re.compile(p, re.IGNORECASE | re.MULTILINE), c) for p, c in self.OBJECTIVE_PATTERNS],
            'definition': [(re.compile(p, re.IGNORECASE | re.MULTILINE), c) for p, c in self.DEFINITION_PATTERNS],
            'note': [(re.compile(p, re.IGNORECASE | re.MULTILINE), c) for p, c in self.NOTE_PATTERNS],
            'procedural': [(re.compile(p, re.IGNORECASE | re.MULTILINE), c) for p, c in self.PROCEDURAL_PATTERNS],
        }

    def classify(self, text: str) -> Tuple[str, str]:
        """
        Classify provision type.

        Args:
            text: The provision text

        Returns:
            Tuple of (type, confidence) where:
            - type: "control" | "objective" | "definition" | "note" | "procedural"
            - confidence: "high" | "medium" | "low"
        """
        if not text or len(text.strip()) < 5:
            return 'control', 'low'  # Default to control

        text = text.strip()

        # Check each type and collect scores
        scores = {}
        for prov_type, patterns in self.patterns.items():
            score, best_conf = self._score_patterns(text, patterns)
            scores[prov_type] = (score, best_conf)

        # Find best match
        best_type = None
        best_score = 0
        best_conf = 'low'

        for prov_type, (score, conf) in scores.items():
            # Weight high confidence matches more
            weighted_score = score * (2 if conf == 'high' else 1)
            if weighted_score > best_score:
                best_score = weighted_score
                best_type = prov_type
                best_conf = conf

        # If no strong match, default to control (most common)
        if best_type is None or best_score == 0:
            return 'control', 'low'

        return best_type, best_conf

    def _score_patterns(self, text: str, patterns: list) -> Tuple[int, Optional[str]]:
        """Score text against patterns, return (score, best_confidence)."""
        score = 0
        best_conf = None
        conf_order = {'high': 2, 'medium': 1}

        for pattern, confidence in patterns:
            if pattern.search(text):
                score += conf_order.get(confidence, 1)
                if best_conf is None or conf_order.get(confidence, 0) > conf_order.get(best_conf, 0):
                    best_conf = confidence

        return score, best_conf


def classify_provision_type(text: str) -> Tuple[str, str]:
    """Convenience function for classification."""
    classifier = TypeClassifier()
    return classifier.classify(text)


# CLI for testing
if __name__ == "__main__":
    test_cases = [
        # Controls
        "Buildings must be setback a minimum of 6 metres from the front boundary.",
        "C1 Development must not exceed the maximum building height.",
        "The floor space ratio shall not exceed 0.5:1.",
        "Residential flat buildings are prohibited in this zone.",

        # Objectives
        "O1 To ensure development maintains the streetscape character.",
        "Objective: To protect the amenity of neighbouring properties.",
        "To minimise overshadowing of adjoining properties.",

        # Definitions
        "Site coverage means the proportion of a site covered by buildings.",
        "Setback includes any part of a building above ground level.",
        "Definition: A heritage item refers to items listed in Schedule 5.",

        # Notes
        "Note: This control does not apply to heritage items.",
        "Advisory Note: Applicants should consult with Council early.",
        "Except where otherwise specified, these controls apply.",

        # Procedural
        "Applications must include a site analysis diagram.",
        "A heritage impact statement must be submitted with the application.",
        "Prior to lodging a DA, consultation with neighbours is required.",

        # Ambiguous (should default to control)
        "The streetscape should be considered in all development.",
    ]

    classifier = TypeClassifier()

    print("=== Provision Type Classifier Tests ===\n")
    for text in test_cases:
        prov_type, confidence = classifier.classify(text)
        print(f"[{prov_type.upper()}] ({confidence})")
        print(f"  {text[:70]}...")
        print()
