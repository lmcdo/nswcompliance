#!/usr/bin/env python3
import os, json, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')

missing = [79881, 84492, 84050, 83069, 78537, 80145, 80168, 84314, 84337, 81279, 83333, 81290, 83356, 84454, 84459]

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute('''
    SELECT id, v2_topic, LEFT(provision_text, 250) as text
    FROM regulatory_provisions
    WHERE id = ANY(%s)
''', (missing,))

for row in cur.fetchall():
    text = (row['text'] or '').replace('\n', ' ')
    print(f"ID {row['id']} | {row['v2_topic']} | {text}...")
    print()

cur.close()
conn.close()
