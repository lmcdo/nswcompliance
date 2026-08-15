from dotenv import load_dotenv; import os, psycopg2
load_dotenv('.env')
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
# Check v2_precinct_id for marrickville — is_current vs all
cur.execute("""
    SELECT is_current, COUNT(*) FILTER (WHERE v2_precinct_id IS NOT NULL) AS has_precinct, COUNT(*) AS total
    FROM regulatory_provisions WHERE source_council='marrickville' GROUP BY is_current
""")
print("marrickville precinct by is_current:", cur.fetchall())
cur.close(); conn.close()
