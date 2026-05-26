#!/usr/bin/env python3
"""Check that DB-sourced regulatory constants are present and current.

Exits 0 if all checks pass, 1 if any warnings found.
Designed for Railway cron via run_monitors.py.
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Allow import from scripts/
sys.path.insert(0, os.path.dirname(__file__))
from conveyancing_db import check_regulatory_freshness


def main() -> int:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("CRITICAL: DATABASE_URL not set")
        return 1

    try:
        conn = psycopg2.connect(db_url, connect_timeout=10)
    except Exception as e:
        print(f"CRITICAL: cannot connect to DB — {e}")
        return 1

    warnings = check_regulatory_freshness(conn)
    conn.close()

    if warnings:
        print(f"Regulatory freshness: {len(warnings)} warning(s)")
        for w in warnings:
            print(f"  - {w}")
        return 1

    print("Regulatory freshness: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
