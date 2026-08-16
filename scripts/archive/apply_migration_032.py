#!/usr/bin/env python3
"""Apply migration 032 and backfill dcp_version + extraction_method on existing rows."""
import os, sys, psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()

# --- Apply migration ---
with open('migrations/032_dcp_setback_controls_versioning.sql') as f:
    sql = f.read()
for stmt in sql.split(';'):
    # Strip line comments, then check if anything remains
    lines = [l for l in stmt.splitlines() if not l.strip().startswith('--')]
    stmt = '\n'.join(lines).strip()
    if stmt:
        cur.execute(stmt)
print("Migration 032 applied")

# --- Backfill existing rows ---
# dcp_version: use the chapter-level version for the source chapter
# extraction_method: how each set of rows was obtained

BACKFILL = [
    # (lga, section_ref_fragment, dcp_version, extraction_method)
    ('ku_ring_gai',  'section_a_part_4',       'v1.0-baseline',    'text_extraction'),
    ('marrickville', 'part4_s1_low_density',    'v1.1-2026-04-06',  'text_extraction'),
    ('ashfield',     'chapter-f-dev-category',  'v1.1-2026-03-02',  'mistral_ocr'),
    ('waverley',     'waverley-dcp-2022',        'v1.1-2026-03-16',  'text_extraction'),
]

for lga, section_frag, version, method in BACKFILL:
    cur.execute("""
        UPDATE dcp_setback_controls
        SET dcp_version = %s, extraction_method = %s
        WHERE lga = %s
          AND section_ref ILIKE %s
          AND dcp_version IS NULL
    """, (version, method, lga, f'%{section_frag}%'))
    print(f"  Backfilled {cur.rowcount} rows: {lga} → {version} ({method})")

conn.commit()
conn.close()
print("Done.")
