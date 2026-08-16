#!/usr/bin/env python3
"""
Simulate the impact of classifier fixes on false negatives.
Re-classifies currently excluded provisions with the fixed classifier.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

from enrichment.extractors.actionable_classifier import ActionableClassifier

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

classifier = ActionableClassifier()

print("=" * 70)
print("SIMULATING CLASSIFIER FIX IMPACT")
print("=" * 70)

# Get all currently excluded provisions
cur.execute("""
    SELECT id, document_id, provision_text FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND provision_text IS NOT NULL
""")

rows = cur.fetchall()
total_excluded = len(rows)

print(f"\nTotal currently excluded provisions: {total_excluded}")
print("\nRe-classifying with fixed classifier...")

reclassified = 0
reclassified_reasons = {}
reclassified_with_must = 0
reclassified_c_controls = 0
sample_reclassified = []

for id, doc_id, text in rows:
    is_actionable, reason = classifier.classify(text, doc_id)

    if is_actionable:
        reclassified += 1
        reclassified_reasons[reason] = reclassified_reasons.get(reason, 0) + 1

        # Track specific categories
        if 'must' in text.lower() or 'shall' in text.lower():
            reclassified_with_must += 1
        if text.strip().startswith('C') and len(text) > 2 and text[1].isdigit():
            reclassified_c_controls += 1

        # Keep samples
        if len(sample_reclassified) < 10:
            sample_reclassified.append((id, doc_id[:50], text[:100], reason))

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

print(f"\nProvisions that would be RECLASSIFIED as actionable: {reclassified}")
print(f"Percentage of excluded that are false negatives: {reclassified/total_excluded*100:.1f}%")
print()

print("Reclassification reasons:")
for reason, count in sorted(reclassified_reasons.items(), key=lambda x: -x[1]):
    print(f"  {reason}: {count}")

print()
print(f"Reclassified with must/shall: {reclassified_with_must}")
print(f"Reclassified C-numbered controls: {reclassified_c_controls}")

print("\n" + "=" * 70)
print("SAMPLE RECLASSIFIED PROVISIONS")
print("=" * 70)
for id, doc, text, reason in sample_reclassified:
    print(f"\n[{id}] ({reason})")
    print(f"  Doc: {doc}")
    print(f"  Text: {text}...")

# Compare to current actionable count
cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true")
current_actionable = cur.fetchone()[0]

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"\nCurrent actionable: {current_actionable}")
print(f"Would become actionable: {current_actionable + reclassified}")
print(f"New actionable rate: {(current_actionable + reclassified) / (total_excluded + current_actionable) * 100:.1f}%")

# Estimate remaining false negatives
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE v2_is_actionable = false
    AND (provision_text ILIKE '%must%' OR provision_text ILIKE '%shall%')
""")
must_shall_excluded = cur.fetchone()[0]

remaining_fn = must_shall_excluded - reclassified_with_must
print(f"\nEstimated remaining false negatives (must/shall): {remaining_fn}")
print(f"Remaining false negative rate: {remaining_fn / (total_excluded + current_actionable) * 100:.1f}%")

conn.close()
