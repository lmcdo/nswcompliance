import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

cur.execute("""
    SELECT
        source_council,
        COUNT(*) FILTER (WHERE is_current = TRUE AND source_chapter_key IS NULL)  AS null_key_current,
        COUNT(*) FILTER (WHERE is_current = FALSE AND source_chapter_key IS NULL) AS null_key_deleted,
        COUNT(*) FILTER (WHERE is_current = TRUE AND source_chapter_key IS NOT NULL)  AS keyed_current,
        COUNT(*) FILTER (WHERE is_current = FALSE AND source_chapter_key IS NOT NULL) AS keyed_deleted
    FROM regulatory_provisions
    GROUP BY source_council
    ORDER BY source_council
""")

print(f"{'council':<25} {'null_cur':>9} {'null_del':>9} {'keyed_cur':>10} {'keyed_del':>10}")
print("-" * 65)
for row in cur.fetchall():
    flag = " <<< DAMAGE" if row[2] > 0 else ""
    print(f"{row[0]:<25} {row[1]:>9} {row[2]:>9} {row[3]:>10} {row[4]:>10}{flag}")

conn.close()
