import os, psycopg2
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'dcp_chapter_registry' ORDER BY ordinal_position")
print("Columns:", [r[0] for r in cur.fetchall()])

cur.execute("""
    SELECT chapter_key, council_url
    FROM dcp_chapter_registry
    WHERE council = 'leichhardt'
    ORDER BY sort_order
""")
print("\nAll registered URLs:")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

conn.close()
