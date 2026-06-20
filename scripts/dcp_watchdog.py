#!/usr/bin/env python3
"""
DCP Watchdog — checks for stuck or repeatedly failing chapters,
and detects structured control rows that need human review.

Alert severity tiers:
  CRITICAL — numeric values changed, stuck chapters >48h
  STANDARD — structural changes, stuck chapters >25h
  INFO     — stale controls, unlinked rows (suppressed from Telegram)

Checks:
  1. Stuck chapters — needs_extraction=TRUE for >25 hours
  2. Failing chapters — 3+ failures spanning 3+ days (grace period)
  3. Control rows needing review — severity depends on review_reason
  4. ePlanning MapServer layer health

Exit codes:
    0 = all clear
    2 = issues found — the run itself succeeded (also sends Telegram alert for
        CRITICAL/STANDARD). run_monitors.py treats exit 2 as a healthy run, matching
        r2_monitor / legislation_monitor / dcp_extract_changed. Exit 1 is reserved
        for genuine crashes (e.g. an unhandled exception or DB connection failure),
        which run_monitors reports as a real failure.
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

# Minimum age (days) for failing chapter URLs before alerting.
# Suppresses transient SharePoint / council website outages.
FAIL_GRACE_DAYS = 3


def send_telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[telegram] skipped — no token or chat_id")
        return
    # Telegram max message length is 4096 chars
    original_len = len(msg)
    if original_len > 4000:
        msg = msg[:3950] + "\n\n… (truncated — full output in Railway logs)"
    print(f"[telegram] sending message ({original_len} chars, truncated={original_len > 4000})")
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg},
            timeout=10,
        )
        if resp.ok:
            print(f"[telegram] sent OK ({resp.status_code})")
        else:
            print(f"[telegram] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[telegram] send failed: {exc}")


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

# ── Check 2: Chapters with repeated download failures (grace period) ────────
# The monitor runs daily, so check_failures >= 3 implies ~3+ days of failures.
# Only alert at >= FAIL_GRACE_DAYS failures to filter transient outages.
cur.execute("""
    SELECT council, chapter_key, check_failures, url_last_checked
    FROM dcp_chapter_registry
    WHERE check_failures >= %s
      AND is_active = TRUE
    ORDER BY check_failures DESC, council, chapter_key
""", (FAIL_GRACE_DAYS,))
failing = cur.fetchall()

# ── Check 3a: Control rows flagged for review (change-triggered) ─────────────
# With smart flagging, review_reason now indicates severity:
#   'numeric_value_changed'  → CRITICAL: a setback/height/area value may have changed
#   'structural_change'      → STANDARD: provisions added/removed in restructure
#   'chapter_pdf_changed'    → STANDARD: legacy reason (pre-smart-flagging)
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
cur.execute("""
    SELECT lga, dev_type, extraction_method,
           count(*) as rows,
           max(COALESCE(last_verified_at, reviewed_at, created_at)) as last_verified
    FROM dcp_setback_controls
    WHERE is_current = TRUE
      AND needs_review = FALSE
      AND COALESCE(last_verified_at, reviewed_at, created_at) < NOW() - INTERVAL '180 days'
    GROUP BY lga, dev_type, extraction_method
    ORDER BY last_verified
""")
stale_setbacks = cur.fetchall()

# ── Check 3c: Control rows with no source_chapter_key (unlinked) ─────────────
cur.execute("""
    SELECT lga, count(*) as rows
    FROM dcp_setback_controls
    WHERE is_current = TRUE
      AND source_chapter_key IS NULL
      AND section_ref NOT IN ('LEP', 'ADG', 'various')
    GROUP BY lga
    ORDER BY lga
""")
unlinked = cur.fetchall()

cur.close()
conn.close()

# Severity-bucketed issues
critical_issues = []
standard_issues = []
info_issues = []

# ── Report ───────────────────────────────────────────────────────────────────

if stuck:
    now = datetime.now(timezone.utc)
    critical = [(c, k, d) for c, k, d in stuck if (now - d).total_seconds() > 48 * 3600]
    chapter_list = "\n".join(f"  [{c}/{k}] changed {d}" for c, k, d in stuck)
    if critical:
        critical_issues.append(
            f"{len(critical)} chapters stuck >48h — stale data may be served:\n"
            + "\n".join(f"  [{c}/{k}]" for c, k, _ in critical)
            + f"\n  Run: python scripts/dcp_extract_changed.py"
        )
    non_critical = [x for x in stuck if x not in critical]
    if non_critical:
        standard_issues.append(
            f"{len(non_critical)} chapters stuck >25h:\n"
            + "\n".join(f"  [{c}/{k}]" for c, k, _ in non_critical)
        )
    print(f"STUCK CHAPTERS: {len(stuck)} ({len(critical)} critical >48h)")
    for c, k, d in stuck:
        age_h = (now - d).total_seconds() / 3600
        tag = " [CRITICAL]" if age_h > 48 else ""
        print(f"  [{c}] {k} — changed {d} ({age_h:.0f}h ago){tag}")

if failing:
    fail_list = "\n".join(f"  [{c}/{k}] {f} failures" for c, k, f, _ in failing)
    standard_issues.append(
        f"{len(failing)} chapters failing downloads ({FAIL_GRACE_DAYS}+ consecutive):\n{fail_list}"
    )
    print(f"FAILING CHAPTERS: {len(failing)}")
    for c, k, f, checked in failing:
        print(f"  [{c}] {k} — {f} failures, last checked {checked}")

if needs_review:
    # Split by severity based on review_reason
    critical_reasons = {"numeric_value_changed"}
    standard_reasons = {"structural_change", "chapter_pdf_changed"}

    crit_rows = [(lga, chk, reason, n) for lga, chk, reason, n in needs_review
                 if reason in critical_reasons]
    std_rows = [(lga, chk, reason, n) for lga, chk, reason, n in needs_review
                if reason in standard_reasons]
    other_rows = [(lga, chk, reason, n) for lga, chk, reason, n in needs_review
                  if reason not in critical_reasons and reason not in standard_reasons]

    if crit_rows:
        # Group by council for compact display
        by_council: dict[str, list[tuple]] = {}
        for lga, chk, reason, n in crit_rows:
            by_council.setdefault(lga, []).append((chk, n))
        lines = []
        for lga, chapters in sorted(by_council.items()):
            total = sum(n for _, n in chapters)
            chk_list = ", ".join(chk or "?" for chk, _ in chapters)
            lines.append(f"  {lga}: {total} rows ({chk_list})")
        total_crit = sum(n for _, _, _, n in crit_rows)
        critical_issues.append(
            f"{total_crit} control rows have NUMERIC VALUE CHANGES:\n"
            + "\n".join(lines)
            + "\n  Action: verify values against updated DCP"
        )

    if std_rows:
        by_council_std: dict[str, list[tuple]] = {}
        for lga, chk, reason, n in std_rows:
            by_council_std.setdefault(lga, []).append((chk, reason, n))
        lines = []
        for lga, chapters in sorted(by_council_std.items()):
            total = sum(n for _, _, n in chapters)
            lines.append(f"  {lga}: {total} rows")
        total_std = sum(n for _, _, _, n in std_rows)
        standard_issues.append(
            f"{total_std} control rows flagged ({std_rows[0][2]}):\n"
            + "\n".join(lines)
        )

    if other_rows:
        total_other = sum(n for _, _, _, n in other_rows)
        standard_issues.append(
            f"{total_other} control rows flagged (other reasons):\n"
            + "\n".join(f"  [{lga}/{chk}] {n} rows — {r}"
                        for lga, chk, r, n in other_rows)
        )

    total_review = sum(n for _, _, _, n in needs_review)
    print(f"CONTROLS NEEDING REVIEW: {total_review} rows")
    for lga, chk, reason, n in needs_review:
        print(f"  [{lga}/{chk or 'unknown'}] {n} rows — {reason}")

if stale_setbacks:
    stale_list = "\n".join(
        f"  [{lga}/{dt}] {n} rows ({method}), last verified {last.strftime('%Y-%m-%d')}"
        for lga, dt, method, n, last in stale_setbacks
    )
    info_issues.append(
        f"{len(stale_setbacks)} control groups not verified in >180 days:\n{stale_list}"
    )
    print(f"STALE CONTROLS: {len(stale_setbacks)} groups")
    for lga, dt, method, n, last in stale_setbacks:
        print(f"  [{lga}/{dt}] {n} rows ({method}), last verified {last.strftime('%Y-%m-%d')}")

if unlinked:
    unlinked_list = "\n".join(f"  [{lga}] {n} rows" for lga, n in unlinked)
    total_unlinked = sum(n for _, n in unlinked)
    if total_unlinked > 5:
        info_issues.append(
            f"{total_unlinked} control rows have no source_chapter_key (blind spot):\n{unlinked_list}\n"
            f"  Action: run backfill_source_chapter_key.py to link them"
        )
    print(f"UNLINKED CONTROLS: {total_unlinked} rows")
    for lga, n in unlinked:
        print(f"  [{lga}] {n} rows — no source_chapter_key")

# ── Check 4: ePlanning MapServer layer ID health check ──────────────────────
EPLANNING_BASE = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning"

TEST_POINT = "151.2093,-33.8688"

EPLANNING_LAYERS = [
    # (label, service, layer_id, expected_field)
    ("Low/Mid-Rise Housing Exclusion", "Planning_Portal_SEPP", 776, "LAY_CLASS"),
    ("Complying Local Exclusion", "Planning_Portal_SEPP", 92, "LAY_CLASS"),
    ("Exempt Local Exclusion", "Planning_Portal_SEPP", 93, "LAY_CLASS"),
    ("Dual Occupancy Prohibition", "Planning_Portal_Local_Provisions", 452, "LAY_CLASS"),
    ("Flood Planning Map", "Planning_Portal_Hazard", 230, "LAY_CLASS"),
    ("Infrastructure Contribution Plan", "Planning_Portal_Development_Control", 219, "PLAN_NAME"),
    ("Sun Access Protection", "Planning_Portal_Local_Provisions", 572, "LAY_CLASS"),
    ("Accelerated TOD (existing)", "Planning_Portal_SEPP", 759, "LAY_CLASS"),
]

eplanning_issues = []
print(f"\nePLANNING LAYER HEALTH CHECK ({len(EPLANNING_LAYERS)} layers)")
for label, service, layer_id, expect_field in EPLANNING_LAYERS:
    url = (
        f"{EPLANNING_BASE}/{service}/MapServer/{layer_id}"
        f"?f=json"
    )
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            eplanning_issues.append(f"  {label} ({service}/{layer_id}): HTTP {resp.status_code}")
            print(f"  FAIL [{label}] HTTP {resp.status_code}")
            continue
        data = resp.json()
        if "error" in data:
            eplanning_issues.append(f"  {label} ({service}/{layer_id}): {data['error'].get('message', 'unknown error')}")
            print(f"  FAIL [{label}] {data['error'].get('message', 'unknown')}")
            continue
        field_names = [f["name"] for f in data.get("fields", [])]
        if expect_field not in field_names:
            eplanning_issues.append(
                f"  {label} ({service}/{layer_id}): expected field '{expect_field}' not found. "
                f"Fields: {', '.join(field_names[:5])}"
            )
            print(f"  DRIFT [{label}] field '{expect_field}' missing — layer ID may have shifted")
        else:
            print(f"  OK [{label}] {service}/{layer_id}")
    except Exception as exc:
        eplanning_issues.append(f"  {label} ({service}/{layer_id}): {exc}")
        print(f"  ERROR [{label}] {exc}")

if eplanning_issues:
    standard_issues.append(
        f"{len(eplanning_issues)} ePlanning layer(s) failed health check:\n"
        + "\n".join(eplanning_issues)
    )

# ── Final report — severity-tiered Telegram alert ─────────────────────────
# Only send Telegram for CRITICAL + STANDARD. INFO is logged but not pushed.
has_actionable = bool(critical_issues or standard_issues)

if critical_issues or standard_issues or info_issues:
    parts = []
    if critical_issues:
        parts.append("CRITICAL\n" + "\n\n".join(critical_issues))
    if standard_issues:
        parts.append("STANDARD\n" + "\n\n".join(standard_issues))

    if parts:
        send_telegram("DCP Watchdog alert\n\n" + "\n\n".join(parts))

    # INFO only to stdout
    if info_issues:
        print("\nINFO (not sent to Telegram):")
        for issue in info_issues:
            print(f"  {issue}")

    # Exit 2 (not 1) = "ran fine, found issues". run_monitors.py treats 0 and 2 as a
    # healthy run and pings the healthcheck as success; the Telegram alert above is the
    # signal. Exit 1 is left to Python for genuine crashes so the runner reports those
    # as real failures rather than double-alerting on every normal findings run.
    sys.exit(2)
else:
    print("\nWatchdog: all clear.")
    sys.exit(0)
