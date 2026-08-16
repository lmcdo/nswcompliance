#!/usr/bin/env python3
"""Fix final 3."""
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# 81482 - heritage control about street frontage - correct, just generic
# Add 'street frontage' to heritage keywords or keep as-is

# 80323, 83511 - "controls apply to all other development" - cross-reference, NOT_ACTIONABLE
not_actionable = [80323, 83511]

for pid in not_actionable:
    cur.execute(
        "UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s",
        (pid,)
    )

conn.commit()
print(f"Marked {len(not_actionable)} as not actionable")

cur.close()
conn.close()
