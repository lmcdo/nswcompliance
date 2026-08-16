#!/usr/bin/env python3
"""
_check_latex.py — Count provisions with LaTeX artifacts still present in DB.

Checks for:
  1. LaTeX math tokens: \mathrm, \mathsf, \mathtt, \mathfrak, etc.
  2. LaTeX subscript/superscript: $_{, ^{
  3. LaTeX delimiters: { , } (thousands separator artifact)
  4. Spaced single-digit numbers: "9 0 0", "5 0 0", "1 0 0 0"
  5. \star_ pattern

Breaks down by source_council.
Read-only — no modifications.

Usage:
    python scripts/_check_latex.py
"""

import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Explicit .env path
ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_PATH)


def get_connection():
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(f"No DATABASE_URL or SUPABASE_DB_URL in {ENV_PATH}")
    return psycopg2.connect(url)


def main():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # --- 1. LaTeX math tokens ---
    print("=" * 70)
    print("1. LaTeX math tokens (\\mathrm, \\mathsf, \\mathtt, \\mathfrak, etc.)")
    print("=" * 70)
    cur.execute("""
        SELECT source_council, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND (provision_text LIKE '%\\mathrm%'
            OR provision_text LIKE '%\\mathsf%'
            OR provision_text LIKE '%\\mathtt%'
            OR provision_text LIKE '%\\mathfrak%'
            OR provision_text LIKE '%\\math%')
        GROUP BY source_council
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    total = sum(r["cnt"] for r in rows)
    for r in rows:
        print(f"  {r['source_council'] or '(null)':<30} {r['cnt']:>5}")
    print(f"  {'TOTAL':<30} {total:>5}")

    # --- 2. LaTeX subscript/superscript delimiters ---
    print()
    print("=" * 70)
    print("2. LaTeX subscript/superscript ($_{, ^{)")
    print("=" * 70)
    cur.execute("""
        SELECT source_council, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND (provision_text LIKE '%$_{%'
            OR provision_text LIKE '%^{%')
        GROUP BY source_council
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    total = sum(r["cnt"] for r in rows)
    for r in rows:
        print(f"  {r['source_council'] or '(null)':<30} {r['cnt']:>5}")
    print(f"  {'TOTAL':<30} {total:>5}")

    # --- 3. LaTeX thousands separator { , } ---
    print()
    print("=" * 70)
    print("3. LaTeX thousands separator artifact: { , }")
    print("=" * 70)
    cur.execute("""
        SELECT source_council, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND provision_text LIKE '%%{ , }%%'
        GROUP BY source_council
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    total = sum(r["cnt"] for r in rows)
    for r in rows:
        print(f"  {r['source_council'] or '(null)':<30} {r['cnt']:>5}")
    print(f"  {'TOTAL':<30} {total:>5}")

    # --- 4. Spaced single-digit number patterns ---
    print()
    print("=" * 70)
    print("4. Spaced single-digit numbers (e.g. '9 0 0', '5 0 0', '1 0 0 0')")
    print("=" * 70)
    # Use regex: digit space digit space digit (at least 3 consecutive spaced digits)
    cur.execute(r"""
        SELECT source_council, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND provision_text ~ '\d \d \d'
        GROUP BY source_council
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    total = sum(r["cnt"] for r in rows)
    for r in rows:
        print(f"  {r['source_council'] or '(null)':<30} {r['cnt']:>5}")
    print(f"  {'TOTAL':<30} {total:>5}")

    # --- 5. \star_ pattern ---
    print()
    print("=" * 70)
    print("5. \\star_ pattern (LaTeX annotation)")
    print("=" * 70)
    cur.execute(r"""
        SELECT source_council, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND provision_text LIKE '%\star_%'
        GROUP BY source_council
        ORDER BY cnt DESC
    """)
    rows = cur.fetchall()
    total = sum(r["cnt"] for r in rows)
    for r in rows:
        print(f"  {r['source_council'] or '(null)':<30} {r['cnt']:>5}")
    print(f"  {'TOTAL':<30} {total:>5}")

    # --- 6. Sample provisions with LaTeX for inspection ---
    print()
    print("=" * 70)
    print("6. Sample provisions with LaTeX artifacts (up to 5)")
    print("=" * 70)
    cur.execute(r"""
        SELECT id, source_council, LEFT(provision_text, 200) as snippet
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND (provision_text LIKE '%\math%'
            OR provision_text LIKE '%{ , }%')
        LIMIT 5
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"\n  ID: {r['id']}  Council: {r['source_council']}")
        print(f"  Snippet: {r['snippet']!r}")

    # --- 7. Sample provisions with spaced digits ---
    print()
    print("=" * 70)
    print("7. Sample provisions with spaced digits (up to 5)")
    print("=" * 70)
    cur.execute(r"""
        SELECT id, source_council, LEFT(provision_text, 200) as snippet
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND provision_text ~ '\d \d \d'
        LIMIT 5
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"\n  ID: {r['id']}  Council: {r['source_council']}")
        print(f"  Snippet: {r['snippet']!r}")

    # --- 8. Document breakdown for null source_council with LaTeX ---
    print()
    print("=" * 70)
    print("8. Document breakdown: NULL source_council provisions with LaTeX")
    print("=" * 70)
    cur.execute(r"""
        SELECT LEFT(document_id, 80) as doc_prefix, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND source_council IS NULL
          AND (provision_text LIKE '%\math%' OR provision_text LIKE '%{ , }%')
        GROUP BY LEFT(document_id, 80)
        ORDER BY cnt DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"  {r['cnt']:>5}  doc={r['doc_prefix']}")

    # --- 9. Document breakdown for null source_council with spaced digits ---
    print()
    print("=" * 70)
    print("9. Document breakdown: NULL source_council with spaced digits")
    print("=" * 70)
    cur.execute(r"""
        SELECT LEFT(document_id, 80) as doc_prefix, COUNT(*) as cnt
        FROM regulatory_provisions
        WHERE is_current = TRUE
          AND source_council IS NULL
          AND provision_text ~ '\d \d \d'
        GROUP BY LEFT(document_id, 80)
        ORDER BY cnt DESC
        LIMIT 15
    """)
    rows = cur.fetchall()
    for r in rows:
        print(f"  {r['cnt']:>5}  doc={r['doc_prefix']}")

    cur.close()
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
