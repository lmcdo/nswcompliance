#!/usr/bin/env python3
"""Extract specific pages from R2 PDFs for landscaping detail."""
import os, sys, io
from dotenv import load_dotenv
from pathlib import Path
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from pypdf import PdfReader

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor(cursor_factory=RealDictCursor)

council = sys.argv[1]
chapter_key = sys.argv[2]
pages = [int(p) for p in sys.argv[3].split(",")]

cur.execute("""
    SELECT r2_public_pdf_url, council_url
    FROM dcp_chapter_registry
    WHERE council = %s AND chapter_key = %s
""", (council, chapter_key))
row = cur.fetchone()
url = row.get("r2_public_pdf_url") or row.get("council_url")

print(f"Downloading {council}/{chapter_key}...")
r = httpx.get(url, timeout=120.0, follow_redirects=True)
r.raise_for_status()
reader = PdfReader(io.BytesIO(r.content))
print(f"Total pages: {len(reader.pages)}")

for p in pages:
    if p >= len(reader.pages):
        print(f"\nPage {p}: OUT OF RANGE")
        continue
    text = reader.pages[p].extract_text() or ""
    print(f"\n{'='*60}")
    print(f"=== Page {p} ===")
    print(f"{'='*60}")
    print(text)

conn.close()
