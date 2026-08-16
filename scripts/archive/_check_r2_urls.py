#!/usr/bin/env python3
"""List all R2 public PDF URLs from dcp_chapter_registry."""
import os, sys
from dotenv import load_dotenv
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT council, chapter_key, chapter_label,
           r2_public_pdf_url, council_url, council_page_url
    FROM dcp_chapter_registry
    WHERE is_active = TRUE
    ORDER BY council, chapter_key
""")
for r in cur.fetchall():
    url = r.get("r2_public_pdf_url") or r.get("council_url") or ""
    if url:
        print(f"{r['council']:25s} {r['chapter_key']:45s} {url[:100]}")
    else:
        print(f"{r['council']:25s} {r['chapter_key']:45s} (no URL)")

conn.close()
