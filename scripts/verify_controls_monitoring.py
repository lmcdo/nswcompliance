#!/usr/bin/env python3
"""
End-to-end verification of the DCP controls monitoring chain.

Tests (all read-only, no writes):
  1. Migration 037 columns exist
  2. source_chapter_key backfill coverage
  3. Change-triggered flagging query is valid SQL
  4. Watchdog queries all execute without error
  5. Cross-check: control rows with source_chapter_key match real registry entries

Usage:
    python scripts/verify_controls_monitoring.py
"""
import os, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  PASS: {name}")
        passed += 1
    else:
        print(f"  FAIL: {name} — {detail}")
        failed += 1


# ── Test 1: Migration 037 columns ────────────────────────────────────────────
print("\n=== Test 1: Migration 037 columns ===")
cur.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'dcp_setback_controls'
      AND column_name IN ('source_chapter_key', 'needs_review', 'review_reason', 'reviewed_at')
    ORDER BY column_name
""")
cols = [r["column_name"] for r in cur.fetchall()]
check("source_chapter_key exists", "source_chapter_key" in cols, f"found: {cols}")
check("needs_review exists", "needs_review" in cols, f"found: {cols}")
check("review_reason exists", "review_reason" in cols, f"found: {cols}")
check("reviewed_at exists", "reviewed_at" in cols, f"found: {cols}")

# ── Test 2: source_chapter_key coverage ──────────────────────────────────────
print("\n=== Test 2: source_chapter_key coverage ===")
cur.execute("""
    SELECT
        count(*) as total,
        count(source_chapter_key) as linked,
        count(*) - count(source_chapter_key) as unlinked
    FROM dcp_setback_controls
    WHERE is_current = TRUE
""")
r = cur.fetchone()
total, linked, unlinked = r["total"], r["linked"], r["unlinked"]
print(f"  Total: {total}, Linked: {linked}, Unlinked: {unlinked}")
check("At least some rows are linked", linked > 0, "no rows have source_chapter_key")
check("Unlinked rows < 20%", unlinked < total * 0.2 if total > 0 else True,
      f"{unlinked}/{total} unlinked ({100*unlinked/total:.0f}%)" if total > 0 else "")

# ── Test 3: Flagging query is valid SQL ──────────────────────────────────────
print("\n=== Test 3: Flagging query syntax ===")
try:
    # Use a council/chapter that won't match — just testing SQL validity
    cur.execute("""
        EXPLAIN
        UPDATE dcp_setback_controls
        SET needs_review   = TRUE,
            review_reason  = 'chapter_pdf_changed',
            reviewed_at    = NULL
        WHERE lga               = '__test__'
          AND source_chapter_key = '__test__'
          AND is_current         = TRUE
          AND needs_review       = FALSE
    """)
    check("Flagging UPDATE query is valid SQL", True)
except Exception as e:
    check("Flagging UPDATE query is valid SQL", False, str(e))
    conn.rollback()

# ── Test 4: Watchdog queries all execute ─────────────────────────────────────
print("\n=== Test 4: Watchdog queries ===")

watchdog_queries = {
    "stuck chapters": """
        SELECT council, chapter_key, url_last_changed
        FROM dcp_chapter_registry
        WHERE needs_extraction = TRUE
          AND (last_extracted_at IS NULL OR url_last_changed > last_extracted_at)
          AND url_last_changed < NOW() - INTERVAL '25 hours'
        ORDER BY council, chapter_key
    """,
    "failing chapters": """
        SELECT council, chapter_key, check_failures, url_last_checked
        FROM dcp_chapter_registry
        WHERE check_failures >= 3
          AND is_active = TRUE
        ORDER BY check_failures DESC, council, chapter_key
    """,
    "needs_review (change-triggered)": """
        SELECT lga, source_chapter_key, review_reason,
               count(*) as rows
        FROM dcp_setback_controls
        WHERE is_current = TRUE
          AND needs_review = TRUE
        GROUP BY lga, source_chapter_key, review_reason
        ORDER BY lga, source_chapter_key
    """,
    "stale controls (time-based)": """
        SELECT lga, dev_type, extraction_method,
               count(*) as rows,
               max(COALESCE(reviewed_at, created_at)) as last_verified
        FROM dcp_setback_controls
        WHERE is_current = TRUE
          AND needs_review = FALSE
          AND COALESCE(reviewed_at, created_at) < NOW() - INTERVAL '180 days'
        GROUP BY lga, dev_type, extraction_method
        ORDER BY last_verified
    """,
    "unlinked controls": """
        SELECT lga, count(*) as rows
        FROM dcp_setback_controls
        WHERE is_current = TRUE
          AND source_chapter_key IS NULL
        GROUP BY lga
        ORDER BY lga
    """,
}

for name, sql in watchdog_queries.items():
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        check(f"Query '{name}' executes", True)
        if rows:
            print(f"    ({len(rows)} results)")
    except Exception as e:
        check(f"Query '{name}' executes", False, str(e))
        conn.rollback()

# ── Test 5: Cross-check chapter_keys against registry ────────────────────────
print("\n=== Test 5: source_chapter_key references valid registry entries ===")
cur.execute("""
    SELECT DISTINCT sc.lga, sc.source_chapter_key
    FROM dcp_setback_controls sc
    WHERE sc.source_chapter_key IS NOT NULL
      AND sc.is_current = TRUE
      AND NOT EXISTS (
          SELECT 1 FROM dcp_chapter_registry cr
          WHERE cr.council = sc.lga
            AND cr.chapter_key = sc.source_chapter_key
      )
""")
orphans = cur.fetchall()
if orphans:
    for o in orphans:
        print(f"    Orphan: [{o['lga']}] → {o['source_chapter_key']} (not in registry)")
    # Orphans for Tier 2 councils (not yet in registry) are expected
    tier2_orphans = [o for o in orphans if o["lga"] not in ("marrickville", "leichhardt", "ashfield", "woollahra", "waverley", "ku_ring_gai", "city_of_sydney")]
    inner_orphans = [o for o in orphans if o["lga"] in ("marrickville", "leichhardt", "ashfield", "woollahra", "waverley", "ku_ring_gai", "city_of_sydney")]
    check("No orphans for registered councils", len(inner_orphans) == 0,
          f"{len(inner_orphans)} orphans in registered councils")
    if tier2_orphans:
        print(f"    ({len(tier2_orphans)} Tier 2 orphans — expected until registry is populated)")
else:
    check("No orphan source_chapter_keys", True)

# ── Summary ──────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
if failed > 0:
    print("Fix failures before deploying.")
    sys.exit(1)
else:
    print("All checks passed.")
    sys.exit(0)

cur.close()
conn.close()
