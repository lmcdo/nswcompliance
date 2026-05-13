#!/usr/bin/env python3
"""
Backfill effective_date on dcp_setback_controls from dcp_version strings.

Parses dates from patterns like:
  v2023-amendment-8-aug2025  → 2025-08-01
  v2015-amended-dec2024      → 2024-12-01
  Campbelltown SCDCP 2015 (updated 02/09/2024)  → 2024-09-02
  v1.0-2026-03-01            → 2026-03-01
  Blacktown DCP 2015         → 2015-01-01  (year-only fallback)

Usage:
    python scripts/backfill_effective_date.py --dry-run
    python scripts/backfill_effective_date.py
"""
import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_effective_date(version: str) -> date | None:
    """Extract the most specific date from a dcp_version string."""
    if not version:
        return None

    v = version.strip()

    # Pattern: v1.0-YYYY-MM-DD or v1.1-YYYY-MM-DD
    m = re.search(r"v\d+\.\d+-(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Pattern: DD/MM/YYYY (Australian date format)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", v)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))

    # Pattern: Month YYYY or MonYYYY at end — e.g. "amended May 2016", "apr2026"
    m = re.search(r"(\w+)\s*(\d{4})\s*\)?$", v)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        if month_str in MONTH_MAP and 2000 <= year <= 2030:
            return date(year, MONTH_MAP[month_str], 1)

    # Pattern: -monYYYY e.g. v2015-amended-dec2024, v2022-amendment-2-apr2026
    m = re.search(r"-([a-z]{3})(\d{4})$", v, re.IGNORECASE)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        if month_str in MONTH_MAP and 2000 <= year <= 2030:
            return date(year, MONTH_MAP[month_str], 1)

    # Pattern: Month YYYY in parentheses — e.g. "(April 2026)", "(June 2024)"
    m = re.search(r"\((\w+)\s+(\d{4})\)", v)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        if month_str in MONTH_MAP and 2000 <= year <= 2030:
            return date(year, MONTH_MAP[month_str], 1)

    # Pattern: -monYYYY in middle — e.g. v2013-amendment-13-nov2025
    m = re.search(r"-([a-z]{3})(\d{4})", v, re.IGNORECASE)
    if m:
        month_str = m.group(1).lower()
        year = int(m.group(2))
        if month_str in MONTH_MAP and 2000 <= year <= 2030:
            return date(year, MONTH_MAP[month_str], 1)

    # Pattern: vYYYY or vYYYY-current or vYYYY-suffix (no month info)
    m = re.match(r"^v(\d{4})(?:-.*)?$", v)
    if m:
        year = int(m.group(1))
        if 2000 <= year <= 2030:
            return date(year, 1, 1)

    # Fallback: extract the most recent 4-digit year from any format
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", v)]
    if years:
        return date(max(years), 1, 1)

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT DISTINCT dcp_version
        FROM dcp_setback_controls
        WHERE is_current = TRUE
          AND effective_date IS NULL
          AND dcp_version IS NOT NULL
        ORDER BY dcp_version
    """)
    versions = [r["dcp_version"] for r in cur.fetchall()]

    print(f"Distinct dcp_version values to parse: {len(versions)}\n")

    parsed = 0
    failed = []

    for v in versions:
        d = parse_effective_date(v)
        if d:
            parsed += 1
            print(f"  {v:55} → {d}")
            if not args.dry_run:
                cur.execute(
                    "UPDATE dcp_setback_controls SET effective_date = %s "
                    "WHERE dcp_version = %s AND is_current = TRUE AND effective_date IS NULL",
                    (d, v),
                )
        else:
            failed.append(v)
            print(f"  {v:55} → UNPARSEABLE")

    if not args.dry_run and parsed > 0:
        conn.commit()

    print(f"\nParsed: {parsed}")
    print(f"Unparseable: {len(failed)}")
    if failed:
        print("\nUnparseable versions (need manual effective_date):")
        for v in failed:
            print(f"  {v}")

    # Summary
    if not args.dry_run:
        cur.execute("""
            SELECT
                count(*) as total,
                count(effective_date) as has_date,
                count(*) - count(effective_date) as missing
            FROM dcp_setback_controls
            WHERE is_current = TRUE
        """)
        r = cur.fetchone()
        print(f"\nPost-backfill: {r['has_date']}/{r['total']} rows have effective_date "
              f"({r['missing']} missing)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
