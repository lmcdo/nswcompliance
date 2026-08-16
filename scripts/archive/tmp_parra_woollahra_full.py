import os, psycopg2, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Parramatta dwelling house building envelope (105051)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 105051")
text = cur.fetchone()[0]
print("=== Parramatta DH Building Envelope ===")
print(text[:2000])

# Parramatta multi-dwelling building envelope (105069)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 105069")
text = cur.fetchone()[0]
print("\n\n=== Parramatta Multi-Dwelling Building Envelope ===")
print(text[:2000])

# Woollahra building envelope (98913)
cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = 98913")
text = cur.fetchone()[0]
print("\n\n=== Woollahra Building Envelope (B3.2) ===")
print(text[:2000])

conn.close()
