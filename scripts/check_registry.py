#!/usr/bin/env python3
import os, sys
from pathlib import Path
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv
import psycopg2

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"])
cur = conn.cursor()

cur.execute("SELECT council, count(*) FROM dcp_chapter_registry GROUP BY council ORDER BY council")
print("Chapters by council:")
for row in cur.fetchall():
    print(f"  {row[0]:20s}: {row[1]}")

cur.execute("SELECT count(*) FROM dcp_chapter_registry WHERE content_hash IS NOT NULL")
print(f"\nWith hash (uploaded) : {cur.fetchone()[0]}")

cur.execute("SELECT count(*) FROM dcp_chapter_registry WHERE content_hash IS NULL")
print(f"Missing hash         : {cur.fetchone()[0]}")

cur.execute("SELECT council, chapter_key FROM dcp_chapter_registry WHERE content_hash IS NULL")
rows = cur.fetchall()
if rows:
    print("\nChapters missing hash:")
    for r in rows:
        print(f"  {r[0]}/{r[1]}")

cur.close()
conn.close()
