#!/usr/bin/env python3
"""
Search council DCP chapter PDFs (from R2) for landscaping/deep soil controls.
Fetches URLs from dcp_chapter_registry.
"""
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

council = sys.argv[1] if len(sys.argv) > 1 else None

if council:
    cur.execute("""
        SELECT council, chapter_key, chapter_label, r2_public_pdf_url, council_url
        FROM dcp_chapter_registry
        WHERE council = %s AND is_active = TRUE
        ORDER BY chapter_key
    """, (council,))
else:
    cur.execute("""
        SELECT council, chapter_key, chapter_label, r2_public_pdf_url, council_url
        FROM dcp_chapter_registry
        WHERE is_active = TRUE
        ORDER BY council, chapter_key
    """)

chapters = cur.fetchall()
print(f"Found {len(chapters)} chapters")

for ch in chapters:
    url = ch.get("r2_public_pdf_url") or ch.get("council_url")
    if not url:
        continue

    council_name = ch["council"]
    key = ch["chapter_key"]
    label = ch.get("chapter_label") or key

    print(f"\n{'='*60}")
    print(f"Council: {council_name} | Chapter: {key} | Label: {label}")
    print(f"URL: {url[:100]}")

    try:
        r = httpx.get(url, timeout=60.0, follow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        print(f"  SKIP (download failed): {e}")
        continue

    try:
        reader = PdfReader(io.BytesIO(r.content))
    except Exception as e:
        print(f"  SKIP (not a valid PDF): {e}")
        continue

    hits = 0
    for i in range(len(reader.pages)):
        text = reader.pages[i].extract_text() or ""
        lower = text.lower()
        if ("landscap" in lower or "deep soil" in lower) and ("%" in text or "minimum" in lower):
            preview = text.strip().replace("\n", " | ")
            print(f"  Page {i}: {preview[:400]}")
            hits += 1
            if hits >= 5:
                print(f"  ... (truncated at 5 hits)")
                break

    if hits == 0:
        print(f"  No landscaping hits in {len(reader.pages)} pages")

conn.close()
