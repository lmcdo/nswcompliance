#!/usr/bin/env python3
"""Deactivate Ku-ring-gai Part 1 Introduction — unextractable due to OCR double-char artifacts."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = FALSE, is_active = FALSE
    WHERE council = 'ku_ring_gai' AND chapter_key = 'part-1-introduction'
    RETURNING chapter_key
""")
row = cur.fetchone()
conn.commit()
print(f"Deactivated: {row[0] if row else 'not found'}")
cur.close()
conn.close()
