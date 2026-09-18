#!/usr/bin/env python3
# prior-art-checked: reuse not viable because nothing writes currency_confirmed_plan. Four
# sweeps, 2026-09-18: (1) grep currency_confirmed_plan across the repo returns
# scripts/outreach_claim_checks.py (reads it) and migrations/073 (adds it) and nothing else;
# (2) frontend renders currency, never confirms it; (3) scripts/ holds writers for
# currency_date/label/evidence but none for the confirmation; (4) the SPEC and MEMORY.md
# record the check (#1115) and no writer. The plan NAME is derived from the check's own CTE
# rather than retyped, so the written value cannot drift from what the check compares.
"""Record that the plan a council's served numbers come from is the plan in force.

`every_served_council_has_a_current_plan_check` (OC-17) needs, per served council, a
confirmation no older than 90 days naming the plan its numbers trace to. 21 councils have
none.

WHAT A CONFIRMATION MAY AND MAY NOT REST ON
-------------------------------------------
This field means a check was performed, so it is written ONLY where one was, and the
evidence already sits in `dcp_plan_as_at.currency_evidence`: an amendment stamp inside our
own copy, or a sha256 equal to the file the council links today. Five councils are excluded
by MEASUREMENT, not by opinion:

  city_of_sydney, georges_river, ku_ring_gai, woollahra
      Chapters whose content_hash no longer equals provisions_extracted_from_hash (DQ-70,
      11 chapters). Confirming "the plan in force" while serving numbers read out of a
      document we no longer hold would attest to the wrong version. All are flagged
      needs_extraction and are re-read on the nightly run; they can be confirmed after.

  northern_beaches
      The monitored URL is pinned to "Warringah DCP 2011 - as amended 7 May 2016" on a
      frozen S3 bucket, so its hash can never change and its unchanged status means
      nothing. The council commenced Part G10 (Low and Mid-Rise Housing) on 15 September
      2025 and now publishes the plan as an online book with no PDF. The plan itself is
      still in force; our copy is behind it, which is a source problem to fix, not a
      confirmation to record.

Dry run by default; --apply writes, after a CSV backup of every row it touches.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from outreach_claim_checks import SERVED  # noqa: E402  (the check's own serve filter)

# Each name carries the reason it is held back, so this list cannot quietly become a
# convenience. Adding a council here without clearing its reason is the failure mode.
HELD_BACK = {
    "city_of_sydney": "source moved since extraction (DQ-70) — re-read pending",
    "georges_river": "source moved since extraction (DQ-70) — re-read pending",
    "ku_ring_gai": "8 chapters moved since extraction (DQ-70) — re-read pending",
    "woollahra": "source moved since extraction (DQ-70) — re-read pending",
    "northern_beaches": "our copy predates Part G10, in force 15 Sep 2025; monitored URL is "
                        "pinned to the 2016 file and can never change",
}

# The plan name is taken from the same CTE the check uses, never retyped: a confirmation
# that names a plan the check does not derive fails as loudly as no confirmation at all,
# and would be harder to see.
PLAN_SQL = f"""
WITH served AS (
    SELECT lga, source_chapter_key FROM dcp_setback_controls
     WHERE {SERVED} AND COALESCE(source_chapter_key, '') NOT LIKE '\\_external\\_%'
), traced AS (
    SELECT s.lga, r.id AS registry_id, COALESCE(r.dcp_name, '(no plan name)') AS plan
      FROM served s
      LEFT JOIN dcp_chapter_registry r
        ON r.council = s.lga AND r.chapter_key = s.source_chapter_key AND r.is_active
)
SELECT t.lga,
       count(*) FILTER (WHERE registry_id IS NULL) AS untraced,
       count(DISTINCT plan) FILTER (WHERE registry_id IS NOT NULL) AS plans,
       min(plan) FILTER (WHERE registry_id IS NOT NULL) AS plan,
       a.currency_date, a.currency_label, a.currency_evidence, a.currency_confirmed_at
  FROM traced t
  LEFT JOIN dcp_plan_as_at a ON a.lga = t.lga
 GROUP BY t.lga, a.currency_date, a.currency_label, a.currency_evidence, a.currency_confirmed_at
 ORDER BY t.lga
"""


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    env = REPO / ".env"
    if not env.exists():  # a worktree has no .env of its own
        env = Path(str(REPO).split(".claude")[0]) / ".env"
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no DATABASE_URL")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write; omit for a dry run")
    args = ap.parse_args()

    conn = psycopg2.connect(_dsn(), connect_timeout=20)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30s'")
            cur.execute(PLAN_SQL)
            rows = cur.fetchall()

            to_write, skipped = [], []
            for lga, untraced, plans, plan, cdate, label, evidence, confirmed in rows:
                if lga in HELD_BACK:
                    skipped.append((lga, HELD_BACK[lga]))
                elif confirmed is not None:
                    skipped.append((lga, "already confirmed"))
                elif untraced or plans != 1:
                    skipped.append((lga, f"{untraced} untraced, {plans} plan name(s)"))
                elif not evidence:
                    # No recorded evidence means no check was performed, whatever the
                    # date says. A confirmation resting on nothing is the thing this
                    # field exists to prevent.
                    skipped.append((lga, "no recorded evidence"))
                else:
                    to_write.append((lga, plan, cdate, label))

            print(f"{len(rows)} served councils | to confirm: {len(to_write)} | "
                  f"skipped: {len(skipped)}\n")
            for lga, plan, cdate, label in to_write:
                print(f"  CONFIRM  {lga:<20} {plan}")
                print(f"           as-at {cdate} — {(label or '')[:96]}")
            print()
            for lga, why in skipped:
                print(f"  skip     {lga:<20} {why}")

            if not to_write:
                conn.rollback()
                return 0

            stamp = f"{datetime.now(timezone.utc):%Y-%m-%d_%H%M}"
            suffix = "" if args.apply else "_dryrun"
            path = (REPO / "data" / "db_rollback_backups"
                    / f"dcp_plan_as_at_pre_confirm_plan_in_force_{stamp}{suffix}.csv")
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["lga", "confirmed_at_before", "confirmed_plan_after",
                            "currency_date", "currency_label"])
                w.writerows([[lga, "", plan, cdate, label] for lga, plan, cdate, label in to_write])
            print(f"\nbackup {path}")

            if args.apply:
                for lga, plan, _cdate, _label in to_write:
                    cur.execute(
                        "UPDATE dcp_plan_as_at SET currency_confirmed_at = NOW(), "
                        "currency_confirmed_plan = %s WHERE lga = %s "
                        "AND currency_confirmed_at IS NULL", (plan, lga))
                conn.commit()
                print(f"APPLIED — {len(to_write)} council(s) confirmed.")
            else:
                conn.rollback()
                print("DRY RUN — no writes. Re-run with --apply to commit.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
