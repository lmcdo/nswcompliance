#!/usr/bin/env python3
"""Set r2_public_pdf_url for all Woollahra chapters."""
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
    WHERE council = 'woollahra' AND is_active = TRUE
      AND r2_current_path IS NOT NULL
      AND r2_public_pdf_url IS NULL
    RETURNING id, chapter_key, r2_public_pdf_url
""", (R2_PUBLIC_BASE,))

updated = cur.fetchall()
conn.commit()

print(f"Set r2_public_pdf_url for {len(updated)} Woollahra chapters:")
for r in updated:
    print(f"  {r[0]:>5} | {r[1]:<35} | {r[2]}")

cur.close()
conn.close()
