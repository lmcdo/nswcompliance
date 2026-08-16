#!/usr/bin/env python3
"""Verify the classifier fixes work correctly."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enrichment.extractors.actionable_classifier import ActionableClassifier

classifier = ActionableClassifier()

print("=" * 60)
print("CLASSIFIER FIX VERIFICATION")
print("=" * 60)

# Test 1: Blank line fix
print("\n### TEST 1: Blank Line Fix ###\n")

text_with_blank = """

C62 Additions must not compromise the symmetry."""

text_clean = "C62 Additions must not compromise the symmetry."

result1 = classifier.classify(text_with_blank, "Marrickville_DCP")
result2 = classifier.classify(text_clean, "Marrickville_DCP")

print(f"Text WITH blank line: {result1}")
print(f"Text without blank:   {result2}")
print(f"PASS: {result1[0] == result2[0] == True}")

# Test 2: Underscore pattern fix
print("\n### TEST 2: Underscore Pattern Fix ###\n")

import re

# First verify the pattern matching works
pattern = re.compile(r'Local[_ ]Environmental[_ ]Plan', re.IGNORECASE)
doc_id = "Inner_West_Local_Environmental_Plan_2022"
match = pattern.search(doc_id)
print(f"Pattern match test: {match.group() if match else 'NO MATCH'}")

# Use a provision that has 2+ actionable patterns to pass LEP threshold
# (LEP requires 2+ patterns or 1 pattern + >150 chars)
lep_provision = "(3) Development consent must not be granted. Minimum setback of 6m required."

# Test with underscore document ID (previously would be "Unknown", now is "LEP/SEPP")
result3 = classifier.classify(lep_provision, "Inner_West_Local_Environmental_Plan_2022")
print(f"LEP with underscores: {result3}")
print(f"  Doc ID: Inner_West_Local_Environmental_Plan_2022")

# Verify is_mixed is being detected
for p in classifier.mixed_doc_patterns:
    if p.search(doc_id):
        print(f"  Matched MIXED pattern: {p.pattern}")
        break

# Test with space document ID
result4 = classifier.classify(lep_provision, "Inner West Local Environmental Plan 2022")
print(f"LEP with spaces:      {result4}")
print(f"PASS: {result3[0] == True and result3[1] == 'lep_sepp_strong_indicators'}")

# Test 3: Rescue logic for boilerplate with actionable content
print("\n### TEST 3: Boilerplate Rescue Logic ###\n")

# This text starts with "Figure 1" (boilerplate pattern) but has strong actionable signals
rescue_text = "Figure 1 shows the required setback of minimum 6m. Buildings must not exceed 9m height."

result5 = classifier.classify(rescue_text, "Marrickville_DCP")
print(f"Figure 1 with controls: {result5}")
print(f"PASS: {result5[0] == True and result5[1] == 'rescued_high_actionable_score'}")

# Test 4: Pure boilerplate should still be excluded
print("\n### TEST 4: Pure Boilerplate Still Excluded ###\n")

boilerplate = "This version compiled and maintained by the Parliamentary Counsel's Office."
result6 = classifier.classify(boilerplate, "Any_Document")
print(f"Pure boilerplate: {result6}")
print(f"PASS: {result6[0] == False}")

# Summary
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
all_pass = (
    result1[0] == True and
    result2[0] == True and
    result3[0] == True and
    result3[1] == 'lep_sepp_strong_indicators' and
    result5[0] == True and
    result5[1] == 'rescued_high_actionable_score' and
    result6[0] == False
)
print(f"\nAll tests passed: {all_pass}")
