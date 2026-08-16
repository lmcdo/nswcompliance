from dotenv import load_dotenv; load_dotenv()
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
# What documents are in the DB?
cur.execute("SELECT DISTINCT document_id, source_council FROM regulatory_provisions WHERE document_id IS NOT NULL GROUP BY document_id, source_council ORDER BY source_council, document_id LIMIT 30")
print("=== document_ids in regulatory_provisions ===")
for r in cur.fetchall(): print(r)
# What's in instrument_registry?
cur.execute("SELECT instrument_key, instrument_label, instrument_type FROM instrument_registry ORDER BY instrument_type")
print("\n=== instrument_registry ===")
for r in cur.fetchall(): print(r)
conn.close()
