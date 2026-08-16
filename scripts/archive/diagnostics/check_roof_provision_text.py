"""
Diagnostic: Check Roof heritage provision text for extraction errors

Checks all Marrickville DCP Roof provisions to identify which ones have
incorrect provision_text (e.g., section intro text instead of specific controls).

Expected:
- Roof provisions should contain specific controls like "8.1.7.3 Solar panels..."
- They should NOT contain general intro text like "8.1.7 Heritage Items" headers

Output:
- List of provisions with their text
- Flag suspicious patterns (intro text, truncated text)
- Summary of how many need fixing
"""

import os
os.environ['SUPABASE_URL'] = 'https://egaxshyzelmkevunrfdl.supabase.co'
os.environ['SUPABASE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVnYXhzaHl6ZWxta2V2dW5yZmRsIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczNTcwMjU0MCwiZXhwIjoyMDUxMjc4NTQwfQ.s3st62Sq5CtUwJkLs5xUuSnJkc4Y9ykhVyhp6c8vtvw'

from supabase import create_client
import re

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

print("=" * 100)
print("DIAGNOSTIC: Roof Heritage Provision Text Check")
print("=" * 100)
print()

# Get all Roof heritage provisions for Marrickville
result = sb.table('regulatory_provisions').select(
    'id, provision_number, provision_text, pdf_page, v2_heritage_type, v2_is_actionable, section_header'
).eq('former_council', 'Marrickville').eq('v2_marker', 'heritage').eq('v2_topic', 'Roof').order('pdf_page').execute()

provisions = result.data
print(f"Found {len(provisions)} Roof heritage provisions in Marrickville DCP")
print()

# Patterns that suggest WRONG text (intro/header text instead of specific controls)
SUSPICIOUS_PATTERNS = [
    r'8\.1\.7\s+Heritage Items',  # Section header instead of control
    r'Heritage items are listed in Schedule 5',  # Intro paragraph
    r'The following controls encourage',  # Intro paragraph
    r'1\.7\.1\s+General controls common to all development',  # Generic control, not roof-specific
    r'Significant internal and external features of heritage ite\.',  # Truncated text
]

# Patterns that suggest CORRECT text (roof-specific controls)
CORRECT_PATTERNS = [
    r'8\.1\.7\.[3-9]',  # Subsection numbers like 8.1.7.3
    r'roof|Roof',  # Contains "roof"
    r'solar|Solar',  # Contains "solar" (common roof topic)
    r'ridgeline',  # Specific roof term
    r'tiles|sheeting|metal|terracotta',  # Roof materials
]

suspicious_count = 0
correct_count = 0
issues = []

for i, p in enumerate(provisions, 1):
    text = p['provision_text'] or ''

    # Check for suspicious patterns
    is_suspicious = any(re.search(pattern, text, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS)

    # Check for correct patterns
    has_roof_content = any(re.search(pattern, text, re.IGNORECASE) for pattern in CORRECT_PATTERNS)

    print(f"\n{'='*100}")
    print(f"PROVISION #{i}: ID {p['id']}")
    print(f"{'='*100}")
    print(f"Number:      {p['provision_number']}")
    print(f"Page:        {p['pdf_page']}")
    print(f"Type:        {p['v2_heritage_type']}")
    print(f"Actionable:  {p['v2_is_actionable']}")
    print(f"Header:      {p['section_header']}")
    print()

    # Show first 500 chars of text
    preview = text[:500] if len(text) > 500 else text
    print(f"TEXT PREVIEW ({len(text)} chars total):")
    print("-" * 100)
    print(preview)
    if len(text) > 500:
        print("...")
    print("-" * 100)
    print()

    # Analysis
    if is_suspicious:
        print("⚠️  SUSPICIOUS: Contains section intro/header text (likely WRONG)")
        suspicious_count += 1
        issues.append({
            'id': p['id'],
            'page': p['pdf_page'],
            'number': p['provision_number'],
            'reason': 'Contains intro/header text instead of roof-specific control'
        })
    elif has_roof_content:
        print("✅ LOOKS CORRECT: Contains roof-specific content")
        correct_count += 1
    else:
        print("❓ UNCLEAR: No obvious roof-specific content, but no intro text either")
        issues.append({
            'id': p['id'],
            'page': p['pdf_page'],
            'number': p['provision_number'],
            'reason': 'Missing roof-specific keywords'
        })

# Summary
print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print(f"Total provisions:     {len(provisions)}")
print(f"Suspicious (wrong):   {suspicious_count} ⚠️")
print(f"Looks correct:        {correct_count} ✅")
print(f"Unclear:              {len(provisions) - suspicious_count - correct_count} ❓")
print()

if issues:
    print(f"\n{len(issues)} PROVISIONS NEED ATTENTION:")
    print("-" * 100)
    for issue in issues:
        print(f"  ID {issue['id']:6d} | Page {issue['page']:3d} | {issue['number']:20s} | {issue['reason']}")
    print()
    print("RECOMMENDATION:")
    print("These provisions likely have incorrect provision_text extracted from PDF.")
    print("They need to be re-extracted with the correct text for roof-specific controls.")
else:
    print("✅ All provisions look correct!")
