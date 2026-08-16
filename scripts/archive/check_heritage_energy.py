#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Check dcp_general_requirements for energy provisions tagged as heritage
print("Energy provisions in dcp_general_requirements tagged as heritage:")
cur.execute('''
    SELECT id, category, part_number, part_name, LEFT(requirement_text, 150)
    FROM dcp_general_requirements
    WHERE (category = 'heritage' OR part_name = 'Heritage')
    AND requirement_text ILIKE '%photovoltaic%'
    LIMIT 10
''')
for r in cur.fetchall():
    print(f"ID {r[0]}: cat={r[1]}, part_num={r[2]}, part_name={r[3]}")
    print(f"  text: {r[4]}...")
    print()

# Check all provisions with photovoltaic
print("\n\nAll provisions mentioning photovoltaic:")
cur.execute('''
    SELECT id, category, part_number, part_name
    FROM dcp_general_requirements
    WHERE requirement_text ILIKE '%photovoltaic%'
    LIMIT 20
''')
for r in cur.fetchall():
    print(f"ID {r[0]}: cat={r[1]}, part_num={r[2]}, part_name={r[3]}")

cur.close()
conn.close()
