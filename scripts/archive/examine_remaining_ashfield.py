#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
cur = conn.cursor()

cur.execute('''
    SELECT id, provision_text, v2_dcp_part, pdf_page
    FROM regulatory_provisions
    WHERE document_id ILIKE %s
      AND v2_topic IS NULL
      AND is_current = TRUE
    ORDER BY v2_dcp_part, pdf_page, id
''', ('%Ashfield%',))

print("Remaining Ashfield None topics:\n")
for p in cur.fetchall():
    text = (p['provision_text'] or '')[:150].replace('\n', ' ')
    print(f"ID {p['id']} ({p['v2_dcp_part']}, page {p['pdf_page']})")
    print(f"  {text}")
    print()

conn.close()
