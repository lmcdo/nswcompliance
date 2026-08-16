#!/usr/bin/env python3
"""
Validation Script: Check metadata enrichment accuracy

Randomly sample provisions and compare automated enrichment
against manual expert categorization.
"""

import os
import random
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 80)
print("ENRICHMENT ACCURACY VALIDATION")
print("=" * 80)
print()

# Get random sample of enriched provisions
print("Sampling provisions for manual validation...")
cur.execute("""
SELECT
    id,
    provision_text,
    v2_marker,
    v2_provision_type,
    v2_display_priority,
    v2_has_numeric_value,
    v2_topic
FROM regulatory_provisions
WHERE document_id ILIKE '%Marrickville%'
  AND v2_is_actionable = true
  AND v2_display_priority IS NOT NULL
ORDER BY RANDOM()
LIMIT 20;
""")

samples = cur.fetchall()

print(f"\n{'='*80}")
print(f"MANUAL VALIDATION SAMPLE (20 provisions)")
print(f"{'='*80}\n")

validation_results = []

for i, (prov_id, text, marker, prov_type, priority, has_numeric, topic) in enumerate(samples, 1):
    print(f"\n{'─'*80}")
    print(f"PROVISION {i}/20 (ID: {prov_id})")
    print(f"{'─'*80}")
    print(f"\nTopic: {topic}")
    print(f"Marker: {marker}")
    print(f"\nText:\n{text[:300]}...")

    print(f"\n{'AUTOMATED ENRICHMENT:'}")
    print(f"  Type:     {prov_type or 'NULL'}")
    print(f"  Priority: {priority or 'NULL'}")
    print(f"  Numeric:  {has_numeric}")

    # Manual validation questions
    print(f"\n{'MANUAL VALIDATION:'}")

    # 1. Is provision type correct?
    print(f"\n1. Is provision type '{prov_type}' CORRECT?")
    print(f"   Options: objective / control / performance_criteria / other")
    correct_type = input(f"   Correct type (or press Enter if '{prov_type}' is right): ").strip()
    if not correct_type:
        correct_type = prov_type

    # 2. Is priority correct?
    print(f"\n2. Is priority '{priority}' CORRECT?")
    print(f"   Options: critical / important / guideline / contextual")
    correct_priority = input(f"   Correct priority (or press Enter if '{priority}' is right): ").strip()
    if not correct_priority:
        correct_priority = priority

    # 3. Is numeric detection correct?
    print(f"\n3. Is numeric detection '{has_numeric}' CORRECT?")
    correct_numeric = input(f"   Correct value (True/False, or press Enter if '{has_numeric}' is right): ").strip()
    if not correct_numeric:
        correct_numeric = str(has_numeric)

    # Record results
    validation_results.append({
        'id': prov_id,
        'type_correct': correct_type == prov_type,
        'priority_correct': correct_priority == priority,
        'numeric_correct': correct_numeric == str(has_numeric),
        'automated': {
            'type': prov_type,
            'priority': priority,
            'numeric': has_numeric
        },
        'manual': {
            'type': correct_type,
            'priority': correct_priority,
            'numeric': correct_numeric
        }
    })

    print(f"\n{'='*80}\n")

# Calculate accuracy
type_accuracy = sum(1 for r in validation_results if r['type_correct']) / len(validation_results) * 100
priority_accuracy = sum(1 for r in validation_results if r['priority_correct']) / len(validation_results) * 100
numeric_accuracy = sum(1 for r in validation_results if r['numeric_correct']) / len(validation_results) * 100

print(f"\n{'='*80}")
print(f"ACCURACY RESULTS (n={len(validation_results)})")
print(f"{'='*80}\n")
print(f"  Provision Type:    {type_accuracy:.1f}% accurate")
print(f"  Display Priority:  {priority_accuracy:.1f}% accurate")
print(f"  Numeric Detection: {numeric_accuracy:.1f}% accurate")
print(f"\n  Overall Accuracy:  {(type_accuracy + priority_accuracy + numeric_accuracy) / 3:.1f}%")

# Show errors
print(f"\n{'='*80}")
print(f"ERRORS FOUND")
print(f"{'='*80}\n")

for i, r in enumerate(validation_results, 1):
    if not (r['type_correct'] and r['priority_correct'] and r['numeric_correct']):
        print(f"\nProvision {i} (ID: {r['id']}):")
        if not r['type_correct']:
            print(f"  Type:     {r['automated']['type']} → {r['manual']['type']}")
        if not r['priority_correct']:
            print(f"  Priority: {r['automated']['priority']} → {r['manual']['priority']}")
        if not r['numeric_correct']:
            print(f"  Numeric:  {r['automated']['numeric']} → {r['manual']['numeric']}")

conn.close()

print(f"\n{'='*80}")
print(f"RECOMMENDATION:")
print(f"{'='*80}\n")

overall_accuracy = (type_accuracy + priority_accuracy + numeric_accuracy) / 3

if overall_accuracy >= 95:
    print("✅ EXCELLENT: Safe for production use with disclaimers")
elif overall_accuracy >= 85:
    print("⚠️  GOOD: Safe for use with confidence scores and user override")
elif overall_accuracy >= 70:
    print("⚠️  MODERATE: Use with caution, show confidence scores, require review")
else:
    print("❌ POOR: Not reliable enough for production, needs improvement")

print()
