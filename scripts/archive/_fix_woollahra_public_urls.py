#!/usr/bin/env python3
"""Check R2 public URL patterns and set for Woollahra chapters."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# First, check existing public URL patterns from other councils
cur.execute("""
    SELECT council, chapter_key, r2_current_path, r2_public_pdf_url
    FROM dcp_chapter_registry
    WHERE r2_public_pdf_url IS NOT NULL
    LIMIT 5
""")
print("=== Existing public URL patterns ===")
for r in cur.fetchall():
    print(f"  {r[0]}/{r[1]}")
    print(f"    r2_path:    {r[2]}")
    print(f"    public_url: {r[3]}")
    print()

# Show Woollahra chapters needing public URLs
cur.execute("""
    SELECT id, chapter_key, r2_current_path
    FROM dcp_chapter_registry
    WHERE council = 'woollahra' AND is_active = TRUE
    ORDER BY chapter_key
""")
print("=== Woollahra chapters (need public URLs) ===")
for r in cur.fetchall():
    print(f"  {r[0]:>5} | {r[1]:<30} | {r[2]}")

cur.close()
conn.close()
