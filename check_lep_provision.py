#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')
from db_safety_wrapper import get_safe_connection

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, ref_number, section_header, provision_text, LENGTH(provision_text)
            FROM regulatory_provisions
            WHERE id = 9092
        """)

        row = cur.fetchone()
        if row:
            print(f"ID: {row[0]}")
            print(f"Ref: {row[1]}")
            print(f"Header: {row[2]}")
            print(f"Text length: {row[4]} chars")
            print(f"\nFull text:\n{row[3]}")