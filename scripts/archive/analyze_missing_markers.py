#!/usr/bin/env python3
"""
Analyze the 1059 Leichhardt Part C Section 1 provisions without markers.
Can we extract C# from their text? Or are they garbage?
"""
import os
import sys
import re
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("="*80)
print("ANALYZING 1059 LEICHHARDT PART C SECTION 1 PROVISIONS WITHOUT MARKERS")
print("="*80)

cur.execute("""
    SELECT id, LEFT(provision_text, 300) as text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%leichhardt%'
    AND v2_is_actionable = true
    AND v2_dcp_part = 'Part C Section 1'
    AND (v2_marker IS NULL OR v2_marker = '')
""")

provisions = cur.fetchall()
print(f"\nTotal: {len(provisions)}")

# Categorize
categories = defaultdict(list)

for prov_id, text in provisions:
    if not text:
        categories['empty'].append((prov_id, ''))
        continue

    text_clean = text.strip()

    # Check for C# at start
    c_match = re.match(r'^(C\d+)', text_clean)
    if c_match:
        categories['has_C#_in_text'].append((prov_id, text_clean[:80]))
        continue

    # Check for TOC patterns
    if '......' in text or 'SECTION' in text[:30]:
        categories['toc_garbage'].append((prov_id, text_clean[:80]))
        continue

    # Check for Figure references
    if text_clean.startswith('Figure') or text_clean.startswith('FIGURE'):
        categories['figure_ref'].append((prov_id, text_clean[:80]))
        continue

    # Check for objectives (O1, O2)
    if re.match(r'^O\d+', text_clean):
        categories['objective'].append((prov_id, text_clean[:80]))
        continue

    # Check for intro text
    if text_clean.startswith('This ') or text_clean.startswith('The '):
        categories['intro_paragraph'].append((prov_id, text_clean[:80]))
        continue

    # Check for bullet points / lists
    if text_clean.startswith('•') or text_clean.startswith('-') or text_clean.startswith('a.'):
        categories['list_item'].append((prov_id, text_clean[:80]))
        continue

    # Check if it looks like a control (has "shall", "must", "required")
    if any(word in text_clean.lower() for word in ['shall', 'must', 'required', 'minimum', 'maximum']):
        categories['likely_control_no_marker'].append((prov_id, text_clean[:80]))
        continue

    # Unknown
    categories['unknown'].append((prov_id, text_clean[:80]))

print("\n## Categories:\n")
for cat, items in sorted(categories.items(), key=lambda x: -len(x[1])):
    print(f"\n### {cat}: {len(items)} provisions")
    for prov_id, preview in items[:5]:
        print(f"    ID {prov_id}: {preview}...")
    if len(items) > 5:
        print(f"    ... and {len(items) - 5} more")

# Summary
print("\n" + "="*80)
print("SUMMARY - What to do with each category")
print("="*80)

actionable_count = 0
garbage_count = 0
needs_work_count = 0

for cat, items in categories.items():
    count = len(items)
    if cat in ['has_C#_in_text']:
        print(f"\n{cat} ({count}): EXTRACT marker from text → topic derivable")
        actionable_count += count
    elif cat in ['toc_garbage', 'figure_ref', 'empty']:
        print(f"\n{cat} ({count}): Mark as v2_is_actionable=false")
        garbage_count += count
    elif cat in ['objective']:
        print(f"\n{cat} ({count}): Keep as actionable, assign topic from context")
        needs_work_count += count
    elif cat in ['intro_paragraph']:
        print(f"\n{cat} ({count}): Review - likely not actionable controls")
        garbage_count += count
    elif cat in ['list_item']:
        print(f"\n{cat} ({count}): Sub-items of controls - keep, inherit parent topic")
        needs_work_count += count
    elif cat in ['likely_control_no_marker']:
        print(f"\n{cat} ({count}): Real controls - need to find which C# section they belong to")
        needs_work_count += count
    else:
        print(f"\n{cat} ({count}): Review manually")
        needs_work_count += count

print(f"\n\nFinal breakdown of 1059:")
print(f"  Can fix automatically (has C# in text): {categories.get('has_C#_in_text', []).__len__()}")
print(f"  Should mark non-actionable: ~{garbage_count}")
print(f"  Need manual/LLM review: ~{needs_work_count}")

conn.close()
