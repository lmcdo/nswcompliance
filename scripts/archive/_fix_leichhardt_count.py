import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()
cur.execute("""
    UPDATE dcp_chapter_registry
    SET hub_expected_count = hub_expected_count + 1
    WHERE council = 'leichhardt' AND hub_expected_count IS NOT NULL
    RETURNING hub_expected_count
""")
row = cur.fetchone()
conn.commit()
print(f"hub_expected_count for leichhardt now: {row[0] if row else 'unchanged (was NULL)'}")
conn.close()
