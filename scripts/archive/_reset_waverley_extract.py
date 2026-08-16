#!/usr/bin/env python3
"""Reset needs_extraction for Waverley after URL-only update."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    UPDATE dcp_chapter_registry
    SET needs_extraction = FALSE
    WHERE council = 'waverley'
    RETURNING id, chapter_key, council_url
""")
for r in cur.fetchall():
    print(f"  {r[0]} | {r[1]} | url={r[2][:60]}...")
conn.commit()
cur.close()
conn.close()
print("Done — needs_extraction reset to FALSE.")
