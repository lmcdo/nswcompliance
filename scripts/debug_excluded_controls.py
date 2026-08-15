#!/usr/bin/env python3
"""
Debug why DCP provisions and C-numbered controls are being excluded.
"""
import os
import sys
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2
from enrichment.extractors.actionable_classifier import ActionableClassifier

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

classifier = ActionableClassifier()

print("=" * 70)
print("DEBUGGING EXCLUDED DCP AND C-NUMBERED CONTROLS")
print("=" * 70)

# Get sample of excluded C-numbered controls
cur.execute("""
    SELECT id, document_id, provision_text FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND provision_text ~ '^C[0-9]+'
    LIMIT 10
""")
c_controls = cur.fetchall()

print("\n" + "=" * 70)
print("EXCLUDED C-NUMBERED CONTROLS - DETAILED ANALYSIS")
print("=" * 70)

for id, doc_id, text in c_controls:
    print(f"\n[{id}] Document: {doc_id[:60]}")
    print(f"Text: {text[:200]}...")

    # Run classifier
    is_actionable, reason = classifier.classify(text, doc_id)

    # Check document type detection
    is_dcp = any(p.search(doc_id) for p in classifier.actionable_doc_patterns)
    is_mixed = any(p.search(doc_id) for p in classifier.mixed_doc_patterns)

    # Check boilerplate
    boilerplate_match = None
    for i, pattern in enumerate(classifier.boilerplate_patterns):
        if pattern.search(text):
            boilerplate_match = classifier.BOILERPLATE_PATTERNS[i]
            break

    # Check actionable patterns
    actionable_score = 0
    matched_patterns = []
    for i, pattern in enumerate(classifier.actionable_patterns):
        if pattern.search(text):
            actionable_score += 1
            matched_patterns.append(classifier.ACTIONABLE_PATTERNS[i][:40])

    print(f"  Doc type detected: {'DCP' if is_dcp else 'LEP/SEPP' if is_mixed else 'UNKNOWN'}")
    print(f"  Boilerplate match: {boilerplate_match}")
    print(f"  Actionable score: {actionable_score}")
    print(f"  Matched patterns: {matched_patterns[:3]}")
    print(f"  Classifier result: {reason}")
    print(f"  Text length: {len(text)}")

# Now check sample of excluded DCP provisions with control language
print("\n" + "=" * 70)
print("EXCLUDED DCP PROVISIONS WITH CONTROL LANGUAGE")
print("=" * 70)

cur.execute("""
    SELECT id, document_id, provision_text FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND document_id ILIKE '%DCP%'
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
    LIMIT 10
""")
dcp_controls = cur.fetchall()

for id, doc_id, text in dcp_controls:
    print(f"\n[{id}] Document: {doc_id[:60]}")
    print(f"Text: {text[:200]}...")

    # Run classifier
    is_actionable, reason = classifier.classify(text, doc_id)

    # Check document type detection
    is_dcp = any(p.search(doc_id) for p in classifier.actionable_doc_patterns)

    # Check boilerplate
    boilerplate_match = None
    for i, pattern in enumerate(classifier.boilerplate_patterns):
        if pattern.search(text):
            boilerplate_match = classifier.BOILERPLATE_PATTERNS[i]
            break

    # Check actionable patterns
    actionable_score = 0
    matched_patterns = []
    for i, pattern in enumerate(classifier.actionable_patterns):
        if pattern.search(text):
            actionable_score += 1
            matched_patterns.append(classifier.ACTIONABLE_PATTERNS[i][:40])

    print(f"  Doc type detected: {'DCP' if is_dcp else 'UNKNOWN'}")
    print(f"  Boilerplate match: {boilerplate_match}")
    print(f"  Actionable score: {actionable_score}")
    print(f"  Matched patterns: {matched_patterns[:3]}")
    print(f"  Classifier result: {reason}")

# Check the actual patterns
print("\n" + "=" * 70)
print("PATTERN VERIFICATION")
print("=" * 70)

# Test C pattern
c_pattern = re.compile(r'^C\d+\s', re.IGNORECASE | re.MULTILINE)
test_texts = [
    "C6 The notification for Category 2 remediation works must:",
    "C25 Car share parking spaces are to be provided",
    "C1 A landscape plan prepared by a suitably qualified",
]

print("\nTesting '^C\\d+\\s' pattern:")
for text in test_texts:
    match = c_pattern.search(text)
    print(f"  '{text[:50]}...' -> {'MATCH' if match else 'NO MATCH'}")

# Check if pattern is in the classifier
print(f"\nPatterns in classifier containing 'C':")
for p in classifier.ACTIONABLE_PATTERNS:
    if 'C' in p:
        print(f"  {p}")

# Check DCP detection patterns
print(f"\nDCP detection patterns:")
for p in classifier.ACTIONABLE_DOC_PATTERNS:
    print(f"  {p}")

# Test DCP detection on actual document names
test_docs = [
    "Leichhardt_DCP_2013__5__Part_C_Place_Section_1__with_IWLEP_2022_amendments_March_23",
    "Marrickville_DCP_2011_-_4.1_Low_Density_Residential",
    "Ashfield_DCP_Chapter_F",
]

print(f"\nTesting DCP detection on actual document names:")
for doc in test_docs:
    is_dcp = any(p.search(doc) for p in classifier.actionable_doc_patterns)
    print(f"  '{doc[:50]}...' -> {'DCP' if is_dcp else 'NOT DCP'}")

conn.close()
