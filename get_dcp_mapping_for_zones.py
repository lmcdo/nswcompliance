#!/usr/bin/env python3
"""
Determine which DCP clauses apply to each zone
by analyzing regulatory_provisions
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

print("="*80)
print("DCP ZONE MAPPING ANALYSIS")
print("="*80)

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Find DCP provisions that mention specific zones
        zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4', 'IN1', 'IN2', 'RE1', 'RE2']

        for zone in zones:
            print(f"\n{'='*80}")
            print(f"ZONE {zone}")
            print('='*80)

            # Search for provisions mentioning this zone
            pattern = f'%{zone}%'
            cur.execute("""
                SELECT ref_number, section_header, LEFT(provision_text, 150)
                FROM regulatory_provisions
                WHERE document_id LIKE %s
                AND (
                    provision_text ILIKE %s
                    OR section_header ILIKE %s
                )
                ORDER BY ref_number
                LIMIT 5
            """, ('%Inner_West%DCP%', pattern, pattern))

            results = cur.fetchall()
            if results:
                print(f"Found {len(results)} provisions mentioning {zone}:")
                for row in results:
                    print(f"  {row[0]}: {row[1] or 'No header'}")
                    print(f"    {row[2]}...")
            else:
                print(f"No specific provisions found for {zone}")

        # Check if there are zone-specific DCP chapters
        print(f"\n{'='*80}")
        print("DCP DOCUMENT STRUCTURE")
        print('='*80)

        cur.execute("""
            SELECT DISTINCT document_id, COUNT(*)
            FROM regulatory_provisions
            WHERE document_id LIKE '%Inner_West%DCP%'
            GROUP BY document_id
            ORDER BY document_id
        """)

        print("\nDCP Chapters:")
        for row in cur.fetchall():
            doc = row[0]
            count = row[1]

            # Extract chapter name
            if 'Chapter_A' in doc:
                chapter = 'Chapter A - Miscellaneous'
            elif 'Chapter_B' in doc:
                chapter = 'Chapter B - Public Domain'
            elif 'Chapter_C' in doc:
                chapter = 'Chapter C - Sustainability'
            elif 'Chapter_D' in doc:
                chapter = 'Chapter D - Precinct Guidelines'
            elif 'Chapter_E' in doc:
                chapter = 'Chapter E1 - Heritage'
            elif 'Chapter_F' in doc:
                chapter = 'Chapter F - Development Category'
            elif 'Chapter_G' in doc:
                chapter = 'Chapter G - Definitions'
            elif 'Chapter_H' in doc:
                chapter = 'Chapter H'
            else:
                chapter = 'Unknown'

            print(f"  {chapter}: {count} provisions")

        # Check Chapter F structure (Development Category)
        print(f"\n{'='*80}")
        print("CHAPTER F - DEVELOPMENT CATEGORY (Main Controls)")
        print('='*80)

        cur.execute("""
            SELECT DISTINCT section_header
            FROM regulatory_provisions
            WHERE document_id LIKE '%Chapter_F%'
            AND section_header IS NOT NULL
            AND section_header != ''
            ORDER BY section_header
            LIMIT 20
        """)

        print("\nSection headers in Chapter F:")
        for row in cur.fetchall():
            print(f"  - {row[0]}")

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("""
Inner West DCP structure:
- Chapter F contains development-specific controls (NOT zone-specific)
- Controls apply based on DEVELOPMENT TYPE, not zone
- Need to map: Development Type → DCP Chapter F sections

Mapping should be:
R1/R2/R3/R4 (Residential zones) → Chapter F sections for:
  - Dwelling houses (Part F.1)
  - Multi-dwelling housing (Part F.2)
  - Residential flat buildings (Part F.3)

B1/B2/B4 (Business zones) → Chapter F sections for:
  - Shop top housing
  - Commercial premises
  - Mixed use

All zones → Chapter F generic controls:
  - Setbacks
  - Car parking
  - Landscaping
  - Building design
""")