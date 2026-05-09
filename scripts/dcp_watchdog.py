#!/usr/bin/env python3
"""
DCP Watchdog — checks for stuck or repeatedly failing chapters,
and detects structured control rows that need human review.

Three check categories:
  1. Stuck chapters — needs_extraction=TRUE for >25 hours
  2. Failing chapters — 3+ consecutive download failures
  3. Control rows needing review — flagged by chapter change OR time-based fallback

Exit codes:
    0 = all clear
    1 = issues found (also sends Telegram alert)
"""

import os
import sys
import psycopg2
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL        = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
    except Exception:
        pass


conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# ── Check 1: Chapters flagged for extraction but not processed in >25 hours ──
cur.execute("""
    SELECT council, chapter_key, url_last_changed
    FROM dcp_chapter_registry
    WHERE needs_extraction = TRUE
      AND (last_extracted_at IS NULL OR url_last_changed > last_extracted_at)
      AND url_last_changed < NOW() - INTERVAL '25 hours'
    ORDER BY council, chapter_key
""")
stuck = cur.fetchall()

# ── Check 2: Chapters with repeated download failures ────────────────────────
cur.execute("""
    SELECT council, chapter_key, check_failures, url_last_checked
    FROM dcp_chapter_registry
    WHERE check_failures >= 3
      AND is_active = TRUE
    ORDER BY check_failures DESC, council, chapter_key
""")
failing = cur.fetchall()

# ── Check 3a: Control rows flagged for review (change-triggered) ─────────────
# These were flagged by dcp_extract_changed.py when a source chapter PDF changed.
cur.execute("""
    SELECT lga, source_chapter_key, review_reason,
           count(*) as rows
    FROM dcp_setback_controls
    WHERE is_current = TRUE
      AND needs_review = TRUE
    GROUP BY lga, source_chapter_key, review_reason
    ORDER BY lga, source_chapter_key
""")
needs_review = cur.fetchall()

# ── Check 3b: Time-based fallback — all extraction methods, 180 days ─────────
# Safety net: catches rows where no hub scraper monitors the source council,
# or where source_chapter_key was never set (so change-triggered flagging missed them).
cur.execute("""
    SELECT lga, dev_type, extraction_method,
           count(*) as rows,
           max(COALESCE(reviewed_at, created_at)) as last_verified
    FROM dcp_setback_controls
    WHERE is_current = TRUE
      AND needs_review = FALSE
      AND COALESCE(reviewed_at, created_at) < NOW() - INTERVAL '180 days'
    GROUP BY lga, dev_type, extraction_method
    ORDER BY last_verified
""")
stale_setbacks = cur.fetchall()

# ── Check 3c: Control rows with no source_chapter_key (unlinked) ─────────────
# These rows can't be flagged by the change-triggered path — blind spot.
cur.execute("""
    SELECT lga, count(*) as rows
    FROM dcp_setback_controls
    WHERE is_current = TRUE
      AND source_chapter_key IS NULL
    GROUP BY lga
    ORDER BY lga
""")
unlinked = cur.fetchall()

cur.close()
conn.close()

issues = []

# ── Report ───────────────────────────────────────────────────────────────────

if stuck:
    chapter_list = "\n".join(f"  [{c}/{k}] changed {d}" for c, k, d in stuck)
    issues.append(f"{len(stuck)} chapters stuck (needs_extraction=TRUE >25h):\n{chapter_list}")
    print(f"STUCK CHAPTERS: {len(stuck)}")
    for c, k, d in stuck:
        print(f"  [{c}] {k} — changed {d}")

if failing:
    fail_list = "\n".join(f"  [{c}/{k}] {f} failures" for c, k, f, _ in failing)
    issues.append(f"{len(failing)} chapters with repeated download failures:\n{fail_list}")
    print(f"FAILING CHAPTERS: {len(failing)}")
    for c, k, f, checked in failing:
        print(f"  [{c}] {k} — {f} failures, last checked {checked}")

if needs_review:
    review_list = "\n".join(
        f"  [{lga}/{chk or 'unknown'}] {n} rows — {reason}"
        for lga, chk, reason, n in needs_review
    )
    total_review = sum(n for _, _, _, n in needs_review)
    issues.append(
        f"{total_review} control rows need review (chapter changed):\n{review_list}\n"
        f"  Action: verify values against updated DCP, then SET needs_review=FALSE, reviewed_at=now()"
    )
    print(f"CONTROLS NEEDING REVIEW: {total_review} rows")
    for lga, chk, reason, n in needs_review:
        print(f"  [{lga}/{chk or 'unknown'}] {n} rows — {reason}")

if stale_setbacks:
    stale_list = "\n".join(
        f"  [{lga}/{dt}] {n} rows ({method}), last verified {last.strftime('%Y-%m-%d')}"
        for lga, dt, method, n, last in stale_setbacks
    )
    issues.append(
        f"{len(stale_setbacks)} control groups not verified in >180 days:\n{stale_list}"
    )
    print(f"STALE CONTROLS: {len(stale_setbacks)} groups")
    for lga, dt, method, n, last in stale_setbacks:
        print(f"  [{lga}/{dt}] {n} rows ({method}), last verified {last.strftime('%Y-%m-%d')}")

if unlinked:
    unlinked_list = "\n".join(f"  [{lga}] {n} rows" for lga, n in unlinked)
    total_unlinked = sum(n for _, n in unlinked)
    # Only alert if significant — a few unlinked rows during backfill is expected
    if total_unlinked > 5:
        issues.append(
            f"{total_unlinked} control rows have no source_chapter_key (blind spot):\n{unlinked_list}\n"
            f"  Action: run backfill_source_chapter_key.py to link them"
        )
    print(f"UNLINKED CONTROLS: {total_unlinked} rows")
    for lga, n in unlinked:
        print(f"  [{lga}] {n} rows — no source_chapter_key")

if issues:
    send_telegram("DCP Watchdog alert\n\n" + "\n\n".join(issues))
    sys.exit(1)
else:
    print("Watchdog: all clear.")
    sys.exit(0)
