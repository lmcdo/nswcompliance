import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 98131")
text = cur.fetchone()[0]
print(text[:3000])

conn.close()
