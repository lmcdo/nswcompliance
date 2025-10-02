#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, LENGTH(full_text)
            FROM documents
            WHERE id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
        """)

        row = cur.fetchone()
        if row:
            print(f"Document ID: {row[0]}")
            print(f"Full text length: {row[1]} chars")

            # Get a sample to see if clause 4.3 content is in there
            cur.execute("""
                SELECT SUBSTRING(full_text, 1, 5000)
                FROM documents
                WHERE id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50'
            """)
            sample = cur.fetchone()[0]

            if '4.3' in sample and 'height' in sample.lower():
                print("\n✓ Contains clause 4.3 content")
                # Find the section
                idx = sample.find('4.3')
                print(f"\nSample around 4.3:\n{sample[max(0,idx-100):idx+500]}")
            else:
                print("\n✗ Does NOT contain clause 4.3 in first 5000 chars")
                print(f"\nFirst 500 chars:\n{sample[:500]}")