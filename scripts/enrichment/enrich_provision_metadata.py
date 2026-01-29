#!/usr/bin/env python3
"""
Metadata Enrichment Script

Populates v2_provision_type, v2_display_priority, v2_has_numeric_value
based on rule-based text analysis.
"""

import os
import re
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database connection
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

print("=" * 80)
print("PROVISION METADATA ENRICHMENT")
print("=" * 80)
print()

def analyze_provision(text: str, marker: str = None) -> dict:
    """
    Analyze provision text to extract metadata.

    Returns dict with:
    - provision_type: 'objective', 'control', 'performance_criteria', or None
    - has_numeric_value: bool
    - display_priority: 'critical', 'important', 'guideline', or None
    """
    text_lower = text.lower() if text else ""

    # Detect provision type
    provision_type = None

    # Check marker first (most reliable)
    if marker:
        if marker.startswith('O'):
            provision_type = 'objective'
        elif marker.startswith('C'):
            provision_type = 'control'
        elif marker.startswith('P'):
            provision_type = 'performance_criteria'

    # Check text patterns if no marker
    if not provision_type:
        # Objectives section
        if re.search(r'\b(objectives?|aims?|goals?|purpose)\b', text_lower):
            # Check if it's a heading or actual objective
            if re.search(r'^objectives?:?$|^objectives?\s*\n|\d+\.\d+\.\d+\s*objectives?', text_lower):
                provision_type = 'objective'

        # Controls section
        elif re.search(r'\b(controls?|requirements?|standards?)\b', text_lower):
            if re.search(r'^controls?:?$|^controls?\s*\n|\d+\.\d+\.\d+\s*controls?', text_lower):
                provision_type = 'control'

        # Performance criteria
        elif re.search(r'\b(performance criteria|performance outcomes?)\b', text_lower):
            provision_type = 'performance_criteria'

        # Mandatory language suggests control
        elif re.search(r'\b(must|shall|required|mandatory)\b', text_lower):
            provision_type = 'control'

        # Design guidance language suggests objective
        elif re.search(r'\b(should|encouraged|desirable|preferred)\b', text_lower):
            provision_type = 'objective'

    # Detect numeric values (measurements)
    has_numeric = bool(re.search(
        r'\d+(\.\d+)?\s*(m\b|metres?|meters?|%|percent|mm|km|ha|sqm?|m2|m²|spaces?|storeys?|floors?)',
        text_lower
    ))

    # Assign display priority
    display_priority = None

    if has_numeric:
        # Numeric controls are typically critical
        if provision_type == 'control' or re.search(r'\b(must|shall|maximum|minimum|required)\b', text_lower):
            display_priority = 'critical'
        else:
            display_priority = 'important'
    else:
        # Non-numeric provisions
        if provision_type == 'objective':
            display_priority = 'guideline'
        elif provision_type == 'control':
            display_priority = 'important'
        elif provision_type == 'performance_criteria':
            display_priority = 'guideline'

    return {
        'provision_type': provision_type,
        'has_numeric_value': has_numeric,
        'display_priority': display_priority
    }


# Step 1: Get sample provisions to test logic
print("Step 1: Testing enrichment logic on sample provisions")
print("-" * 80)

cur.execute("""
SELECT id, provision_text, v2_marker
FROM regulatory_provisions
WHERE document_id ILIKE '%Marrickville%'
  AND v2_is_actionable = true
LIMIT 5;
""")

samples = cur.fetchall()
print(f"\nAnalyzing {len(samples)} sample provisions:\n")

for prov_id, text, marker in samples:
    result = analyze_provision(text, marker)
    print(f"ID {prov_id}:")
    print(f"  Marker: {marker}")
    print(f"  Type: {result['provision_type']}")
    print(f"  Has numeric: {result['has_numeric_value']}")
    print(f"  Priority: {result['display_priority']}")
    print(f"  Text preview: {text[:80]}...")
    print()


# Step 2: Ask for confirmation
print("=" * 80)
confirm = input("\nDo you want to proceed with enrichment for ALL provisions? (yes/no): ")

if confirm.lower() != 'yes':
    print("Enrichment cancelled.")
    conn.close()
    exit()


# Step 3: Enrich all actionable provisions
print("\nStep 2: Enriching all actionable provisions")
print("-" * 80)

cur.execute("""
SELECT id, provision_text, v2_marker
FROM regulatory_provisions
WHERE v2_is_actionable = true
  AND (v2_provision_type IS NULL OR v2_display_priority IS NULL);
""")

provisions = cur.fetchall()
total = len(provisions)
print(f"\nFound {total} provisions to enrich")

# Track statistics
stats = {
    'objective': 0,
    'control': 0,
    'performance_criteria': 0,
    'unknown_type': 0,
    'has_numeric': 0,
    'critical': 0,
    'important': 0,
    'guideline': 0,
}

updated = 0
batch_size = 100

for i, (prov_id, text, marker) in enumerate(provisions, 1):
    result = analyze_provision(text, marker)

    # Update database
    cur.execute("""
        UPDATE regulatory_provisions
        SET
            v2_provision_type = %s,
            v2_has_numeric_value = %s,
            v2_display_priority = %s
        WHERE id = %s;
    """, (
        result['provision_type'],
        result['has_numeric_value'],
        result['display_priority'],
        prov_id
    ))

    # Update stats
    if result['provision_type']:
        stats[result['provision_type']] += 1
    else:
        stats['unknown_type'] += 1

    if result['has_numeric_value']:
        stats['has_numeric'] += 1

    if result['display_priority']:
        stats[result['display_priority']] += 1

    updated += 1

    # Commit in batches and show progress
    if i % batch_size == 0:
        conn.commit()
        print(f"  Processed {i}/{total} provisions ({i/total*100:.1f}%)")

# Final commit
conn.commit()

print(f"\n✓ Enriched {updated} provisions")
print()
print("Statistics:")
print(f"  Provision Types:")
print(f"    Objectives:              {stats['objective']:5d}")
print(f"    Controls:                {stats['control']:5d}")
print(f"    Performance Criteria:    {stats['performance_criteria']:5d}")
print(f"    Unknown:                 {stats['unknown_type']:5d}")
print()
print(f"  Numeric Detection:")
print(f"    Has numeric values:      {stats['has_numeric']:5d} ({stats['has_numeric']/total*100:.1f}%)")
print()
print(f"  Display Priority:")
print(f"    Critical:                {stats['critical']:5d}")
print(f"    Important:               {stats['important']:5d}")
print(f"    Guideline:               {stats['guideline']:5d}")

conn.close()

print()
print("=" * 80)
print("ENRICHMENT COMPLETE")
print("=" * 80)
