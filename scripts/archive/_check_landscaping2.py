#!/usr/bin/env python3
import os, sys
from dotenv import load_dotenv
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
if sys.platform == "win32": sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(Path(__file__).parent.parent / ".env")
conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("SELECT * FROM dcp_setback_controls WHERE control_type = 'landscaping_min'")
for r in cur.fetchall():
    for k, v in r.items():
        if v is not None:
            print(f"  {k}: {v}")
conn.close()
