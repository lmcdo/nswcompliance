#!/usr/bin/env python3
# prior-art-checked: reuse not viable because no existing repair touches pdf_page.
# Four sweeps 2026-08-09 vs origin/main f5acb080: repair_camden_front_setbacks.py and
# repair_canada_bay_rear_setback.py repair VALUES on named rows and hardcode them;
# repair_missing_primary_controls.py inserts rows; repair_dq41_null_label_derived_dates.py
# nulls effective_date; update_needs_review_controls.py writes review flags. None reads a
# measured proposal file and none corrects a page citation. The guarded-write SHAPE is
# deliberately copied from repair_shadow_reports.py (predict to disk, per-row pre-state
# guard, verify after) because that pattern matched 519/519 rows on the shadow repair.
"""Correct pdf_page on the 8 controls whose real page was located unambiguously.

WRITE HALF of a measure-then-write split. It consumes
data/control_page_corrections_proposal.json and writes nothing that is not in it.

WHY ONLY 8 OF THE 42 WRONG-PAGE ROWS
------------------------------------
The measurement found 110 already correct, 8 with exactly one candidate page, 11 with
SEVERAL candidate pages and 12 whose value is not in the document at all. Only the 8 are
repaired here. Replacing a wrong page reference with a guessed one is worse than leaving
it: it looks repaired, so nobody checks it again. The 11 ambiguous rows sit in a 448-page
document where the same value and wording recur, and choosing among their candidates
needs a person reading, not a script.

SAFETY
------
* Every UPDATE carries `WHERE id = %s AND pdf_page = %s` -- the expected pre-state. A row
  that changed since the measurement is SKIPPED and reported, never overwritten.
* The complete pre-state of all 8 rows is written to data/db_rollback_backups/ BEFORE the
  first write, and the run aborts if that file cannot be written.
* The predicted after-state is written to disk before the first row changes, so the
  verification compares against a prediction that could have been wrong.
* Single-row UPDATEs by primary key. No DELETE, no TRUNCATE, no DDL, no CASCADE, and no
  statement without a WHERE clause.
* --apply is required. Without it the run is a dry run and touches nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2  # module scope: absent library must be RED

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_controls_against_source_pdf import connect  # noqa: E402

PROPOSAL = REPO_ROOT / "data" / "control_page_corrections_proposal.json"
# (--proposal overrides it, e.g. the --missing-page-only measurement's own file.)
BACKUP_DIR = REPO_ROOT / "data" / "db_rollback_backups"


def main() -> int:
    ap = argparse.ArgumentParser(description="Repair pdf_page from the measured proposal")
    ap.add_argument("--apply", action="store_true", help="perform the write (default: dry run)")
    ap.add_argument("--stamp", required=True, help="ISO date for the backup filename")
    ap.add_argument("--proposal", default=None, help="proposal file (default: the measured one)")
    args = ap.parse_args()
    global PROPOSAL
    if args.proposal:
        PROPOSAL = Path(args.proposal) if Path(args.proposal).is_absolute() else REPO_ROOT / args.proposal

    if not PROPOSAL.exists():
        sys.exit(f"FATAL: no proposal at {PROPOSAL}. Run measure_control_page_corrections.py first.")
    doc = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    proposals = doc["proposals"]
    if not proposals:
        print("proposal file contains no corrections; nothing to do.")
        return 0

    conn = connect()  # readonly for the read phase
    cur = conn.cursor()
    cur.execute("SET statement_timeout = '30s'")

    # Both figures, in one query, because they answer different questions: the total is
    # the blast-radius denominator and must not move; the current count is the served
    # population this repair is scoped to (the proposal itself comes from an
    # is_current = TRUE query).
    cur.execute("SELECT count(*) FILTER (WHERE is_current = TRUE), count(*) "
                "FROM dcp_setback_controls")
    current_before, total_before = cur.fetchone()
    print(f"dcp_setback_controls rows before: {total_before} total, "
          f"{current_before} is_current")
    print(f"proposals to apply: {len(proposals)} ({len(proposals) / total_before:.2%} of table)\n")

    ids = [p["id"] for p in proposals]
    cur.execute("""SELECT id, lga, control_type, pdf_page, section_ref, value_min, value_max,
                          source_chapter_key, is_current
                   FROM dcp_setback_controls WHERE id = ANY(%s) ORDER BY id""", (ids,))
    cols = [d[0] for d in cur.description]
    pre = [dict(zip(cols, r)) for r in cur.fetchall()]
    pre_by_id = {r["id"]: r for r in pre}
    cur.close()
    conn.close()

    if len(pre) != len(proposals):
        sys.exit(f"FATAL: expected {len(proposals)} rows, found {len(pre)}. Aborting.")

    # Prediction BEFORE any write, so verification compares to something falsifiable.
    prediction = []
    for p in proposals:
        row = pre_by_id[p["id"]]
        if row["pdf_page"] != p["cited_page"]:
            print(f"  !! id={p['id']} moved since measurement "
                  f"(now {row['pdf_page']}, expected {p['cited_page']}) -- will be SKIPPED")
            continue
        prediction.append({"id": p["id"], "from": p["cited_page"], "to": p["proposed_page"]})

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / f"control_pdf_pages_pre_repair_{args.stamp}.json"
    backup.write_text(json.dumps(
        {"table": "dcp_setback_controls", "column": "pdf_page",
         # Scope recorded in the backup itself: every row here came from the proposal,
         # which is generated by a query filtered on is_current = TRUE, so this file
         # covers served rows only. A reader restoring from it should know that.
         "scope": "is_current = TRUE (the served population); superseded rows untouched",
         "taken_at": datetime.now(timezone.utc).isoformat(),
         "rollback": "UPDATE dcp_setback_controls SET pdf_page = <pdf_page> "
                     "WHERE id = <id> AND is_current = TRUE",
         "rows": pre}, indent=2, default=str), encoding="utf-8")
    print(f"backup written: {backup.relative_to(REPO_ROOT)} ({len(pre)} rows)")

    pred_file = BACKUP_DIR / f"control_pdf_pages_prediction_{args.stamp}.json"
    pred_file.write_text(json.dumps(prediction, indent=2), encoding="utf-8")
    print(f"prediction written: {pred_file.relative_to(REPO_ROOT)} ({len(prediction)} rows)\n")

    for p in sorted(proposals, key=lambda x: (x["lga"], x["id"])):
        print(f"  id={p['id']:<6} {p['lga']:<16} {p['control_type']:<22} "
              f"{p['cited_page']} -> {p['proposed_page']}  "
              f"({'new' if p['offset'] is None else format(p['offset'], '+d')})")

    if not args.apply:
        print("\nDRY RUN — nothing written. Re-run with --apply to perform the update.")
        return 0

    wconn = connect.__wrapped__() if hasattr(connect, "__wrapped__") else None
    # connect() pins readonly; open a separate writable session explicitly.
    import os
    wconn = psycopg2.connect(
        host=os.environ["PGHOST"], user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"], dbname=os.environ["PGDATABASE"],
        port=os.environ.get("PGPORT", "5432"),
        sslmode=os.environ.get("PGSSLMODE", "require"), connect_timeout=30)
    wconn.autocommit = False
    wcur = wconn.cursor()
    wcur.execute("SET statement_timeout = '30s'")

    applied, skipped = 0, 0
    try:
        for p in proposals:
            wcur.execute(
                "UPDATE dcp_setback_controls SET pdf_page = %s "
                # IS NOT DISTINCT FROM: a row with no page yet (NULL) must match its NULL
                # pre-state; `= NULL` never matches, so those rows were always skipped.
                "WHERE id = %s AND pdf_page IS NOT DISTINCT FROM %s",
                (p["proposed_page"], p["id"], p["cited_page"]))
            if wcur.rowcount == 1:
                applied += 1
            else:
                skipped += 1
                print(f"  SKIPPED id={p['id']}: pre-state guard did not match "
                      f"(rowcount {wcur.rowcount})")
        wconn.commit()
    except Exception:
        wconn.rollback()
        print("ROLLED BACK — no rows changed.")
        raise
    finally:
        wcur.close()
        wconn.close()

    print(f"\napplied {applied}, skipped {skipped}")

    vconn = connect()
    vcur = vconn.cursor()
    vcur.execute("SELECT count(*) FILTER (WHERE is_current = TRUE), count(*) "
                 "FROM dcp_setback_controls")
    current_after, total_after = vcur.fetchone()
    # Re-read scoped to the served population: a repaired row that somehow lost
    # is_current would drop out here and show as a prediction mismatch rather than
    # passing silently.
    vcur.execute("SELECT id, pdf_page FROM dcp_setback_controls "
                 "WHERE id = ANY(%s) AND is_current = TRUE", (ids,))
    after = dict(vcur.fetchall())
    vcur.close()
    vconn.close()

    print(f"row count before/after: {total_before} / {total_after}"
          f"  {'OK' if total_before == total_after else '!! CHANGED'}")
    print(f"is_current before/after: {current_before} / {current_after}"
          f"  {'OK' if current_before == current_after else '!! CHANGED'}")

    mismatches = [pr for pr in prediction if after.get(pr["id"]) != pr["to"]]
    print(f"prediction matched: {len(prediction) - len(mismatches)}/{len(prediction)}")
    for m in mismatches:
        print(f"  !! id={m['id']} expected {m['to']}, found {after.get(m['id'])}")
    unchanged = (total_before == total_after) and (current_before == current_after)
    return 0 if not mismatches and unchanged else 1


if __name__ == "__main__":
    raise SystemExit(main())
