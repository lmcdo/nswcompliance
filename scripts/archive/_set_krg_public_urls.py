#!/usr/bin/env python3
"""Set r2_public_pdf_url for all Ku-ring-gai chapters."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

R2_PUBLIC_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev"

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute("""
    SELECT chapter_key, r2_current_path
    FROM dcp_chapter_registry
    WHERE council = 'ku_ring_gai' AND is_active = TRUE AND r2_current_path IS NOT NULL
""")
rows = cur.fetchall()

updated = 0
for chapter_key, r2_path in rows:
    public_url = f"{R2_PUBLIC_BASE}/{r2_path}"
    cur.execute("""
        UPDATE dcp_chapter_registry
        SET r2_public_pdf_url = %s
        WHERE council = 'ku_ring_gai' AND chapter_key = %s
    """, (public_url, chapter_key))
    updated += 1
    print(f"  {chapter_key} -> {public_url}")

conn.commit()
print(f"\nUpdated {updated} rows.")
cur.close()
conn.close()
