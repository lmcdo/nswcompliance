#!/usr/bin/env python3
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    SELECT id, section_header, provision_text
    FROM regulatory_provisions
    WHERE source_council='ku_ring_gai' AND v2_dcp_part='part_12_signage' AND is_current=true
    LIMIT 2
""")
for row in cur.fetchall():
    print(f"=== id={row[0]} header={row[1]} ===")
    print(repr(row[2][:2500]))
    print()
cur.close()
conn.close()
