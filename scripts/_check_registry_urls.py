#!/usr/bin/env python3
"""Check dcp_chapter_registry for councils and their PDF URLs."""
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

# Check columns first
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='dcp_chapter_registry' ORDER BY ordinal_position")
cols = [r["column_name"] for r in cur.fetchall()]
print(f"Columns: {cols}")

# Get all councils and their chapters
cur.execute("SELECT * FROM dcp_chapter_registry ORDER BY council, chapter_key")
rows = cur.fetchall()

councils = {}
for r in rows:
    c = r["council"]
    if c not in councils:
        councils[c] = []
    councils[c].append(r)

print(f"\nCouncils in registry: {len(councils)}")
for c, chapters in sorted(councils.items()):
    print(f"\n{c} ({len(chapters)} chapters):")
    for ch in chapters[:5]:
        url = str(ch.get("pdf_url") or ch.get("hub_url") or "")[:80]
        print(f"  {ch['chapter_key']:40s} {url}")
    if len(chapters) > 5:
        print(f"  ... and {len(chapters)-5} more")

conn.close()
