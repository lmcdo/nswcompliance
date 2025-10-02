#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ref_number, section_header
            FROM regulatory_provisions
            WHERE document_id = 'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_section_4'
            ORDER BY id
            LIMIT 30
        """)

        results = cur.fetchall()

        print('Clauses in LEP section 4:')
        for ref, header in results:
            print(f'  {ref}: {header[:70] if header else "No header"}')