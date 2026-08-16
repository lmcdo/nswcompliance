#!/usr/bin/env python3
"""Create canibuildit_leads table in Supabase."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import psycopg2
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS canibuildit_leads (
        id         BIGSERIAL PRIMARY KEY,
        email      TEXT NOT NULL,
        address    TEXT NOT NULL,
        eligible   BOOLEAN,
        created_at TIMESTAMPTZ DEFAULT now()
    )
""")
conn.commit()
cur.execute("SELECT COUNT(*) FROM canibuildit_leads")
print(f"canibuildit_leads ready ({cur.fetchone()[0]} rows)")
cur.close()
conn.close()
