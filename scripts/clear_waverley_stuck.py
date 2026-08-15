#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
cur.execute("""
    UPDATE dcp_chapter_registry SET
        needs_extraction  = FALSE,
        last_extracted_at = NOW(),
        notes             = 'Amendment 5 re-checked 2026-04-21. C1.16 SD controls unchanged: max_height 3.0m (not fronting laneway), side setbacks merit-based. DB row confirmed correct.',
        updated_at        = NOW()
    WHERE council = 'waverley' AND chapter_key = 'waverley-dcp-2022'
    RETURNING id, council, chapter_key
""")
row = cur.fetchone()
print(f"Cleared: id={row[0]} {row[1]}/{row[2]}")
conn.commit()
conn.close()
