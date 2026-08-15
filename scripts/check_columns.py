#!/usr/bin/env python3
"""Quick check for column names."""
import os
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

url = os.getenv('DATABASE_URL')
conn = psycopg2.connect(url)
cur = conn.cursor()
cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    AND (column_name LIKE '%section%' OR column_name LIKE '%toc%' OR column_name LIKE '%header%')
    ORDER BY column_name
""")
print("Columns matching section/toc/header:")
for row in cur.fetchall():
    print(f"  {row[0]}")
conn.close()
