#!/usr/bin/env python3
"""
Clean up duplicate ADG records
Uses safe db wrapper
"""
import sys
sys.path.append('venv_linux/lib/python3.11/site-packages')
from db_safety_wrapper import get_safe_connection

print("Cleaning up duplicate ADG records...")

with get_safe_connection() as conn:
    with conn.cursor() as cur:
        # Delete ALL ADG records
        cur.execute("DELETE FROM setback_rules WHERE ref_number LIKE 'ADG 3F-1%'")
        deleted = cur.rowcount
        conn.commit()
        print(f"Deleted {deleted} ADG records")
        print("Ready to re-insert fresh data")
