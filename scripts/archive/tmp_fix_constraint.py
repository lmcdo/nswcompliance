import os, psycopg2

conn = psycopg2.connect(os.environ["DATABASE_URL"])
conn.autocommit = True
cur = conn.cursor()

# Drop old constraint and add expanded one
cur.execute("ALTER TABLE dcp_setback_controls DROP CONSTRAINT dcp_setback_controls_applicability_check")
cur.execute("""
ALTER TABLE dcp_setback_controls ADD CONSTRAINT dcp_setback_controls_applicability_check 
CHECK (applicability IN ('universal_residential', 'secondary_dwelling_specific', 'zone_specific', 'precinct_specific', 'development_specific'))
""")
print("Updated applicability constraint")

# Verify
cur.execute("""
SELECT pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'dcp_setback_controls_applicability_check'
""")
print(cur.fetchone()[0])

conn.close()
