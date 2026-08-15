#!/usr/bin/env python3
"""Update Ashfield Chapter H URL and clear stuck flag."""
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
NEW_URL = 'https://www.innerwest.nsw.gov.au/sites/default/files/page-documents/Inner_West_Ashfield_DCP_2016_-_Chapter_H_-_with_IWLEP_2022_amendments_Apr_24.pdf'
cur.execute("""
    UPDATE dcp_chapter_registry SET
        council_url        = %s,
        needs_extraction   = FALSE,
        check_failures     = 0,
        url_last_changed   = NULL,
        last_extracted_at  = NOW(),
        notes              = 'Chapter H = amendments schedule (admin only, no setback controls). URL updated 2026-04-21. Low priority for re-extraction.',
        updated_at         = NOW()
    WHERE council = 'ashfield' AND chapter_key = 'chapter-h-amendments'
    RETURNING id, council, chapter_key
""", (NEW_URL,))
row = cur.fetchone()
print(f"Updated id={row[0]} {row[1]}/{row[2]}")
conn.commit()
conn.close()
