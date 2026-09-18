#!/usr/bin/env python3
# prior-art-checked: no existing script repairs plan-name tracing. Four sweeps, 2026-09-18:
#  (1) DB content -- dcp_chapter_registry.dcp_name and dcp_setback_controls.source_chapter_key
#      read directly below; the `_external_lep` convention already carries 18 controls across
#      9 councils, so this REUSES it rather than inventing a key.
#  (2) Frontend -- source_chapter_key is rendered and linked in the DCP surfaces; nothing
#      re-keys a control.
#  (3) Python -- scripts/backfill_source_chapter_key.py fills a MISSING key from the
#      registry; it never corrects one that is present and wrong, which is both cases here.
#      repair_control_pdf_pages.py repairs pages, not keys.
#  (4) Plans + memory -- ce-outreach-readiness-benchmark-SPEC section 0 and MEMORY.md record
#      the confirmation check (#1115) but no repair for what it found.
"""Two councils fail the plan-in-force check before any confirmation is looked at.

`every_served_council_has_a_current_plan_check` (scripts/outreach_claim_checks.py, OC-17)
requires every served number to trace to ONE plan name. Measured 2026-09-18: 26 of 28
served councils do; two do not, for different reasons, and neither is a confirmation
decision -- they are data defects that make the confirmation unanswerable.

  cumberland        ONE plan, two spellings in the registry. Part B is registered as
                    "Cumberland DCP Part B - Residential Zones 2021" and Part G as
                    "Cumberland DCP 2021". They are parts of the same plan, so the check
                    reads two plans where there is one.

  sutherland_shire  Seven controls cite "Sutherland Shire LEP 2015 cl 6.14" but are keyed
                    to a council chapter, so an LEP reads as a second council plan. State
                    instruments are keyed `_external_lep` everywhere else (18 controls, 9
                    councils) and their currency belongs to DQ-88, not to a DCP
                    confirmation -- the check's own comment says exactly this.

Dry run by default; --apply required to write, and every changed row is written to a CSV
under data/db_rollback_backups/ first.
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

CUMBERLAND_WRONG = "Cumberland DCP Part B — Residential Zones 2021"
CUMBERLAND_RIGHT = "Cumberland DCP 2021"
SUTHERLAND_WRONG_KEY = "sutherland-lep-2015-schedule-3"
EXTERNAL_LEP = "_external_lep"

# id=606 is HELD BACK from the re-key, not fixed here. It cites this LEP chapter and stores
# a 5.5m primary street setback; Sutherland Shire LEP 2015 (in force 2026-06-04) page 109
# says "at least 7.5m, or the average distance of the setbacks of the nearest 2 dwelling
# houses". Its stored quote is that same sentence with the distance removed, so the row
# states a number its own source does not.
#
# That is not the LEP-versus-DCP difference it resembles. Schedule 3 is the COMPLYING
# DEVELOPMENT pathway and a DCP may well set a different front setback for a merit DA -- but
# then the row's source would be the DCP, not this chapter. Either the value came from the
# DCP and the key is wrong, or the value is wrong; both need a reading, not a re-key.
# Moving it under _external_lep would file a number the LEP does not contain as an LEP
# number and hand its currency to DQ-88, which checks the LEP text it does not match.
#
# It is not served (needs_review), so nothing is live. Left where it is, and printed.
HELD_BACK = {606}


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


def _backup(rows: list[list], header: list[str], slug: str, apply: bool) -> Path:
    stamp = f"{datetime.now(timezone.utc):%Y-%m-%d_%H%M}"
    name = f"{slug}_{stamp}{'' if apply else '_dryrun'}.csv"
    path = REPO / "data" / "db_rollback_backups" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def repair_cumberland(cur, apply: bool) -> int:
    cur.execute(
        "SELECT id, council, chapter_key, dcp_name FROM dcp_chapter_registry "
        "WHERE council = 'cumberland' AND dcp_name = %s", (CUMBERLAND_WRONG,))
    rows = cur.fetchall()
    print(f"\ncumberland: {len(rows)} registry row(s) naming the plan differently")
    for r in rows:
        print(f"    {r[2]:<40} {r[3]!r}  ->  {CUMBERLAND_RIGHT!r}")
    if not rows:
        return 0
    path = _backup([[r[0], r[1], r[2], r[3], CUMBERLAND_RIGHT] for r in rows],
                   ["id", "council", "chapter_key", "dcp_name_before", "dcp_name_after"],
                   "dcp_chapter_registry_pre_cumberland_plan_name", apply)
    print(f"    backup {path}")
    if apply:
        cur.execute("UPDATE dcp_chapter_registry SET dcp_name = %s "
                    "WHERE council = 'cumberland' AND dcp_name = %s",
                    (CUMBERLAND_RIGHT, CUMBERLAND_WRONG))
        return cur.rowcount
    return 0


def repair_sutherland(cur, apply: bool) -> int:
    cur.execute(
        "SELECT id, lga, control_type, source_chapter_key, left(coalesce(source_text,''), 70) "
        "FROM dcp_setback_controls WHERE source_chapter_key = %s ORDER BY id",
        (SUTHERLAND_WRONG_KEY,))
    rows = cur.fetchall()
    print(f"\nsutherland_shire: {len(rows)} control(s) citing the LEP but keyed to a chapter")
    for r in rows:
        print(f"    id={r[0]} {r[2]:<24} {r[4]}")
    if not rows:
        return 0
    # prior-art-checked: reuse not viable because this reads dcp_chapter_registry.dcp_name to
    # decide whether a chapter is a state instrument, which no existing module does.
    # citation-instrument-urls.ts and app/api/instrument-currency BUILD LINKS for an
    # instrument already identified; dq_probe_live.py MEASURES currency; neither classifies a
    # registry row, and none may write to dcp_setback_controls.
    #
    # The chapter itself must be the LEP, checked in the registry rather than in each
    # control's prose. An earlier version of this guard required every control's source_text
    # to mention "LEP" and refused: the three SERVED rows (607 secondary frontage 3m, 608
    # side 1.5m, 609 rear 6m) carry no citation in their text at all. They were instead
    # checked against the instrument itself -- Sutherland Shire LEP 2015 as in force
    # 2026-06-04, page 109, Schedule 3: "a setback from any secondary frontage of at least
    # 3m", "a setback from the rear boundary of at least 6m", "a setback from the side
    # boundaries of at least 1.5m". Word-for-word matches.
    #
    # (The same page puts the PRIMARY street setback at 7.5m, while id=606 holds 5.5m. That
    # row is not served, so it is not a live defect and is not touched here -- but it is
    # wrong, and it is written down rather than quietly carried across.)
    cur.execute("SELECT dcp_name FROM dcp_chapter_registry "
                "WHERE council = 'sutherland_shire' AND chapter_key = %s",
                (SUTHERLAND_WRONG_KEY,))
    registered = cur.fetchone()
    if not registered or "lep" not in (registered[0] or "").lower():
        shown = registered[0] if registered else None
        print(f"    REFUSED: chapter {SUTHERLAND_WRONG_KEY} is registered as {shown!r}, "
              f"not a state instrument")
        return 0
    print(f"    chapter is registered as {registered[0]!r} — a state instrument, so these "
          f"belong under {EXTERNAL_LEP}, where DQ-88 tracks their currency")
    held = [r for r in rows if r[0] in HELD_BACK]
    movable = [r for r in rows if r[0] not in HELD_BACK]
    for r in held:
        print(f"    HELD BACK id={r[0]} {r[2]} — states a number its own source does not; "
              f"needs a reading, not a re-key")
    if not movable:
        return 0
    path = _backup([[r[0], r[1], r[2], r[3], EXTERNAL_LEP, r[4]] for r in movable],
                   ["id", "lga", "control_type", "key_before", "key_after", "source_text"],
                   "dcp_setback_controls_pre_sutherland_lep_key", apply)
    print(f"    backup {path}  ({len(movable)} to re-key, {len(held)} held back)")
    if apply:
        cur.execute("UPDATE dcp_setback_controls SET source_chapter_key = %s "
                    "WHERE source_chapter_key = %s AND NOT (id = ANY(%s))",
                    (EXTERNAL_LEP, SUTHERLAND_WRONG_KEY, sorted(HELD_BACK)))
        return cur.rowcount
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="write; omit for a dry run")
    args = ap.parse_args()

    conn = psycopg2.connect(_dsn(), connect_timeout=20)
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30s'")
            changed = repair_cumberland(cur, args.apply) + repair_sutherland(cur, args.apply)
        if args.apply:
            conn.commit()
            print(f"\nAPPLIED — {changed} row(s) updated.")
        else:
            conn.rollback()
            print("\nDRY RUN — no writes. Re-run with --apply to commit.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
