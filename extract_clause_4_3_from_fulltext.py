#!/usr/bin/env python3
import sys
import re
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT full_text
            FROM documents
            WHERE id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
        """)

        fulltext = cur.fetchone()[0]

        # Find clause 4.3 in the full text
        # Look for pattern like "4.3   Height of buildings"
        matches = list(re.finditer(r'(^|\n)4\.3\s+', fulltext, re.MULTILINE))

        if matches:
            print(f"Found {len(matches)} occurrences of clause 4.3\n")

            for i, match in enumerate(matches):
                start = match.start()
                # Extract 1000 chars after the match
                extract = fulltext[start:start+1000]
                print(f"\n=== Occurrence {i+1} ===")
                print(extract)
                print("="*80)
        else:
            print("No clause 4.3 found with standard pattern")
            print("\nSearching for any '4.3' in text...")
            idx = fulltext.find('4.3')
            if idx >= 0:
                print(f"\nFound at position {idx}:")
                print(fulltext[max(0,idx-200):idx+800])