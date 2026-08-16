#!/usr/bin/env python3
"""Flag all active KRG chapters for re-extraction with improved column detection."""
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
    UPDATE dcp_chapter_registry
    SET needs_extraction = TRUE
    WHERE council = 'ku_ring_gai' AND is_active = TRUE
    RETURNING chapter_key
""")
flagged = cur.fetchall()
conn.commit()
print(f"Flagged {len(flagged)} KRG chapters for re-extraction:")
for row in flagged:
    print(f"  {row[0]}")
cur.close()
conn.close()
