#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

print("="*80)
print("INNER WEST DCP PROVISIONS ANALYSIS")
print("="*80)

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Find all Inner West DCP documents
        print("\n[1] Inner West DCP Documents:")
        cur.execute("""
            SELECT id, pdf_name, char_count
            FROM documents
            WHERE document_type = 'DCP'
            AND pdf_name LIKE '%Inner%West%'
            ORDER BY pdf_name
            LIMIT 10
        """)

        dcp_docs = []
        for row in cur.fetchall():
            dcp_docs.append(row[0])
            print(f"\n  {row[1]}")
            print(f"  Document ID: {row[0]}")
            print(f"  Size: {row[2]} chars")

        if not dcp_docs:
            print("\n  No Inner West DCP documents found")
            sys.exit(0)

        # Check what provisions exist
        print("\n" + "="*80)
        print("[2] DCP Provision Categories:")

        # Sample provisions by topic
        topics = [
            ('setback', 'Setbacks'),
            ('height', 'Height'),
            ('parking', 'Car Parking'),
            ('landscap', 'Landscaping'),
            ('site coverage', 'Site Coverage'),
            ('heritage', 'Heritage'),
            ('FSR', 'Floor Space Ratio'),
            ('privacy', 'Privacy'),
            ('solar', 'Solar Access')
        ]

        for keyword, label in topics:
            cur.execute("""
                SELECT COUNT(DISTINCT ref_number)
                FROM regulatory_provisions
                WHERE document_id = ANY(%s)
                AND (provision_text ILIKE %s OR section_header ILIKE %s)
            """, (dcp_docs, f'%{keyword}%', f'%{keyword}%'))

            count = cur.fetchone()[0]
            if count > 0:
                print(f"\n  {label}: {count} provisions")

                # Show sample
                cur.execute("""
                    SELECT ref_number, section_header, LEFT(provision_text, 100)
                    FROM regulatory_provisions
                    WHERE document_id = ANY(%s)
                    AND (provision_text ILIKE %s OR section_header ILIKE %s)
                    ORDER BY ref_number
                    LIMIT 3
                """, (dcp_docs, f'%{keyword}%', f'%{keyword}%'))

                for row in cur.fetchall():
                    print(f"    - {row[0]}: {row[1] or 'No header'}")
                    print(f"      {row[2]}...")

        # Check for specific control types
        print("\n" + "="*80)
        print("[3] Specific Control Analysis:")

        # Setback provisions with actual numbers
        cur.execute("""
            SELECT ref_number, provision_text
            FROM regulatory_provisions
            WHERE document_id = ANY(%s)
            AND provision_text ~* '\\d+\\.?\\d*\\s*m.*setback'
            LIMIT 5
        """, (dcp_docs,))

        print("\n  Setback controls with dimensions:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1][:150]}...")

        # Parking rates
        cur.execute("""
            SELECT ref_number, provision_text
            FROM regulatory_provisions
            WHERE document_id = ANY(%s)
            AND provision_text ~* 'space.*per|parking.*rate'
            LIMIT 5
        """, (dcp_docs,))

        print("\n  Parking rate provisions:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1][:150]}...")

print("\n" + "="*80)
print("RECOMMENDATION FOR UI")
print("="*80)
print("""
Based on DCP provisions in database, show these in UI for each property:

PRIORITY 1 (Certifiers need these most):
- Setbacks (front/side/rear with specific dimensions)
- Site coverage limits
- Car parking requirements
- Building height (DCP-specific controls)

PRIORITY 2 (Planners need these):
- Landscaping requirements
- Privacy controls
- Heritage guidelines (if applicable)
- Character area controls

PRIORITY 3 (Nice to have):
- Solar access provisions
- Building design guidelines
- Materials/finishes

Implementation:
1. Extract DCP controls from Planning API (if available)
2. If not in API, extract from documents.full_text like we did for LEP
3. Link to regulatory_provisions for full text
4. Display in same slide-out panel as LEP/SEPP
""")