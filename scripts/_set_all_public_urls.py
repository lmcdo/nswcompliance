#!/usr/bin/env python3
"""Set r2_public_pdf_url for ALL chapters that have r2_current_path but no public URL."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

R2_PUBLIC_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/"

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute("""
    UPDATE dcp_chapter_registry
    SET r2_public_pdf_url = %s || r2_current_path
    WHERE is_active = TRUE
      AND r2_current_path IS NOT NULL
      AND r2_public_pdf_url IS NULL
    RETURNING council, chapter_key
""", (R2_PUBLIC_BASE,))

updated = cur.fetchall()
conn.commit()

from collections import Counter
by_council = Counter(r[0] for r in updated)
print(f"Set r2_public_pdf_url for {len(updated)} chapters:")
for council, count in sorted(by_council.items()):
    print(f"  {council}: {count}")

cur.close()
conn.close()
