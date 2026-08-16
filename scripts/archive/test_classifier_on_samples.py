#!/usr/bin/env python3
"""Test the actual classifier on sample provisions."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enrichment.extractors.actionable_classifier import ActionableClassifier

classifier = ActionableClassifier()

# Test cases - provisions that SHOULD be actionable but were excluded
test_cases = [
    (
        "Inner_West_Local_Environmental_Plan_2022__NSW_Legislation_51_100",
        "Development control plan must address design principles, objectives, land use distribution, conflict avoidance, housing mixes, building envelopes, heights, sustainable transport, pedestrian movement, car parking, environmental impacts, and landscaping."
    ),
    (
        "State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008_NSW_Legislation",
        "(3B) Side setbacks upper level—dwelling constructed on boundary The upper level of a dwelling house and any attached development, other than a garage, constructed on a boundary must have—"
    ),
    (
        "State_Environmental_Planning_Policy_Housing_2021_NSW_Legislation",
        "(2) Development consent must not be granted under this Division unless the consent authority considers whether— (a) the design of the boarding house will be compatible with— (i) the desirable elements of the character of the local area"
    ),
    (
        "Leichhardt_DCP_2013__5__Part_C_Place_Section_1__with_IWLEP_2022_amendments_March_23",
        "At a minimum, turning areas to enable forward entering and exiting, must be provided, offstreet, in the following instances:"
    ),
    (
        "Leichhardt_DCP_2013__5__Part_C_Place_Section_1__with_IWLEP_2022_amendments_March_23",
        "C15 A minimum 4m wide landscaped area must be provided between the detached secondary dwelling and the principal dwelling house when they are located in tandem style."
    ),
]

print("=" * 70)
print("TESTING CLASSIFIER ON SAMPLE PROVISIONS")
print("=" * 70)

for doc_id, text in test_cases:
    is_actionable, reason = classifier.classify(text, doc_id)

    # Also check pattern matching detail
    is_dcp = any(p.search(doc_id) for p in classifier.actionable_doc_patterns)
    is_mixed = any(p.search(doc_id) for p in classifier.mixed_doc_patterns)

    actionable_score = 0
    matched_patterns = []
    for i, pattern in enumerate(classifier.actionable_patterns):
        if pattern.search(text):
            actionable_score += 1
            matched_patterns.append(classifier.ACTIONABLE_PATTERNS[i][:50])

    print(f"\nDoc: {doc_id}")
    print(f"Text: {text[:100]}...")
    print(f"Length: {len(text)} chars")
    print(f"Doc type: {'DCP' if is_dcp else 'LEP/SEPP' if is_mixed else 'Unknown'}")
    print(f"Actionable score: {actionable_score}")
    print(f"Matched patterns: {matched_patterns}")
    print(f"RESULT: {'ACTIONABLE' if is_actionable else 'NOT ACTIONABLE'} ({reason})")
    print(f"EXPECTED: ACTIONABLE (these contain real controls)")
    print(f"CORRECT: {'YES' if is_actionable else 'NO - FALSE NEGATIVE!'}")
