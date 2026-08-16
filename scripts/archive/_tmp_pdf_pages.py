import os, psycopg2
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")
db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
conn = psycopg2.connect(db)
cur = conn.cursor()

for council in ['ku_ring_gai', 'leichhardt']:
    cur.execute("""
        SELECT source_chapter_key, v2_dcp_part, document_id, pdf_page
        FROM regulatory_provisions
        WHERE source_council = %s AND is_current = true AND v2_is_actionable = true
        ORDER BY source_chapter_key, pdf_page
        LIMIT 6
    """, (council,))
    print(f"=== {council} ===")
    for r in cur.fetchall():
        print(f"  source_chapter_key={r[0]}")
        print(f"  v2_dcp_part={r[1]}  document_id={r[2][:60]}  pdf_page={r[3]}")
        print()

conn.close()
