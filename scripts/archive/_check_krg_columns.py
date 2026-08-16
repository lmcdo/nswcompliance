#!/usr/bin/env python3
"""Check how many KRG provisions have Objectives|Controls two-column layout."""
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
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council='ku_ring_gai' AND is_current=true
    AND provision_text ILIKE '%Objectives Controls%'
""")
two_col = cur.fetchone()[0]
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council='ku_ring_gai' AND is_current=true
""")
total = cur.fetchone()[0]
print(f"KRG provisions with 'Objectives Controls' two-column layout: {two_col} of {total}")
cur.close()
conn.close()
