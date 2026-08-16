#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("SELECT DISTINCT dev_type FROM dcp_setback_controls WHERE control_type = 'car_parking' AND is_current = TRUE ORDER BY dev_type")
print("Existing dev_types:", [r[0] for r in cur.fetchall()])
# Check constraint
cur.execute("""
    SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
    WHERE conrelid = 'dcp_setback_controls'::regclass AND conname LIKE '%applicability%'
""")
for r in cur.fetchall():
    print(f"\nConstraint {r[0]}:")
    print(r[1])
conn.close()
