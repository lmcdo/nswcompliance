#!/usr/bin/env python3
"""Fix the final 11 provisions - all are intro/context text, not actionable."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

# All 11 are intro/explanatory text, not actionable requirements
NOT_ACTIONABLE = [
    # Urban design intro/principles
    78312,  # "Urban design concerns the arrangement..."
    78313,  # "Urban design principles..."
    85854,  # Marrickville DCP urban design intro
    # Food production/community gardens intro text
    80347,  # Council sustainability commitment
    80349,  # Council encourages community...
    80351,  # Community garden spaces provide...
    80354,  # connecting people to each other...
    80355,  # industrial heritage/contamination context
    80357,  # precautions recommendation
    80359,  # list of strategies (a,b,c,d)
    80361,  # objectives about food production
]

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--execute', action='store_true')
args = parser.parse_args()

print(f"Marking {len(NOT_ACTIONABLE)} provisions as NOT actionable")

if args.execute:
    for pid in NOT_ACTIONABLE:
        cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = %s", (pid,))
    conn.commit()
    print("Done!")

cur.close()
conn.close()
