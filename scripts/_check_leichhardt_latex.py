#!/usr/bin/env python3
"""Check LaTeX artifacts in Leichhardt provisions."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# Find all LaTeX patterns
patterns = [r'\\star', r'\\mathrm', r'\\mathsf', r'\\prime', r'\$', r'\\frac', r'\\textbf', r'\\left', r'\\right']
for pat in patterns:
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE source_council = 'leichhardt' AND is_current = true
        AND provision_text ~ %s
    """, (pat,))
    count = cur.fetchone()[0]
    if count > 0:
        print(f"Pattern '{pat}': {count} provisions")
        # Show sample
        cur.execute("""
            SELECT id, LEFT(provision_text, 200)
            FROM regulatory_provisions
            WHERE source_council = 'leichhardt' AND is_current = true
            AND provision_text ~ %s
            LIMIT 3
        """, (pat,))
        for r in cur.fetchall():
            print(f"  ID {r[0]}: {r[1][:150]}")
        print()

# Also check for any other backslash patterns
cur.execute("""
    SELECT COUNT(*) FROM regulatory_provisions
    WHERE source_council = 'leichhardt' AND is_current = true
    AND provision_text ~ '\\\\[a-zA-Z]'
""")
print(f"Any backslash+letter pattern: {cur.fetchone()[0]} provisions")

cur.close()
conn.close()
