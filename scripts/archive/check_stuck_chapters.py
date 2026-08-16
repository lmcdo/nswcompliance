#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT council, chapter_key, chapter_label, council_url, url_last_changed,
           last_extracted_at, check_failures, notes
    FROM dcp_chapter_registry
    WHERE needs_extraction = TRUE
      AND (last_extracted_at IS NULL OR url_last_changed > last_extracted_at)
      AND url_last_changed < NOW() - INTERVAL '25 hours'
    ORDER BY council, chapter_key
""")
for r in cur.fetchall():
    print(f"Council:      {r[0]}")
    print(f"Chapter key:  {r[1]}")
    print(f"Label:        {r[2]}")
    print(f"URL:          {r[3]}")
    print(f"Changed:      {r[4]}")
    print(f"Last extract: {r[5]}")
    print(f"Failures:     {r[6]}")
    print(f"Notes:        {r[7]}")
    print()
conn.close()
