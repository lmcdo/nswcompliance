#!/usr/bin/env python3
"""How many stored flood reports served a False that was never actually assessed.

prior-art-checked: reuse not viable because no script measures this. Four sweeps
2026-08-08 against origin/main f5acb080: (1) `git ls-files scripts/ | grep -i
flood` returns nothing that reads property_reports; (2) `git grep -ln
"in_100yr_flood_zone" -- scripts/` returns only brief_field_coverage_baseline.json,
a field list; (3) scripts/measure_shadow_calibration_damage.py and
measure_granny_confidence_states.py are the closest siblings and both measure a
different product's outputs; (4) plan §4a/§4b describe flood data ops and
calibration, neither of which counts this. Same shape as the shadow census, so
the idiom is copied deliberately: predict, count, print, write nothing.

READ ONLY. It issues one SELECT and no UPDATE, INSERT or DELETE. Nothing here
repairs anything — the user's instruction was measure, do not repair, and a
repair pass needs its own authorisation and its own backup.

WHAT COUNTS AS "NEVER ASSESSED"
-------------------------------
The stored `outputs` hold what each source returned at the time. A False was
only defensible if every source that could have said "yes" was actually asked:

  * NSW EPI flood overlay      — `epi_flood_class` is null, or `data_currency`
                                 is "query_failed" (the module's own marker for
                                 a service that did not respond)
  * Council/SES flood extent   — `ses_in_flood_planning_area` is null, which
                                 flood_truth.py already documents as "table
                                 empty or unavailable (distinct from False = no
                                 match)"

A configured-but-absent flood study (the Tweed/Wollongong case) CANNOT be
recovered from stored rows: `flood_studies_absent` did not exist when they were
written, so an empty `flood_studies` list is indistinguishable from "no study
covers this point". Those rows are counted separately as UNKNOWABLE rather than
folded into either bucket — the count below is therefore a FLOOR, not a total.

Usage:
    python scripts/measure_flood_zone_unassessed.py
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
# services/ imports its siblings by bare name (`from audit_trail import ...`),
# which is how the container runs it. Mirror that rather than editing the module.
sys.path.insert(0, str(_ROOT / "services"))


def main() -> int:
    try:
        from dotenv import load_dotenv
        load_dotenv(_ROOT / ".env")
        # A git worktree has no .env of its own; the credentials live beside the
        # main checkout. Resolved via git rather than a hardcoded "../.." so this
        # works from a normal clone too. GIT_* is scrubbed because a hook exports
        # GIT_DIR and it overrides cwd — DQ-54, and the wrong repo here means
        # the wrong database.
        if not (os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")):
            import subprocess
            env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
            common = subprocess.run(
                ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                cwd=str(_ROOT), capture_output=True, text=True, timeout=10, env=env,
            ).stdout.strip()
            if common:
                load_dotenv(Path(common).parent / ".env")
    except ImportError:
        pass

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("psycopg2 not installed — cannot measure. This is UNKNOWABLE, not zero.")
        return 2

    dsn = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not dsn:
        print("No DATABASE_URL/SUPABASE_DB_URL — cannot measure. UNKNOWABLE, not zero.")
        return 2

    conn = psycopg2.connect(dsn, connect_timeout=30)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET statement_timeout = 30000")
            cur.execute(
                """
                SELECT id, address, run_date, outputs
                FROM property_reports
                WHERE product = 'flood'
                ORDER BY run_date
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    # The field is DERIVED on read, not stored: the cache-hit path re-runs
    # _normalise_outputs over the stored raw outputs (flood_truth.py:1985). So
    # every one of these rows re-serves its verdict on the next request, and the
    # three-state fix reaches them all without a data repair. What follows is
    # therefore not "damage in the table" but "what these rows SERVED, and what
    # they will serve now" — computed from the same stored inputs both ways.
    from services.flood_truth import _normalise_outputs

    old_false = old_true = 0
    unparsed: list[tuple[str, str]] = []
    now_none = now_false = now_true = 0
    reasons: Counter = Counter()
    changed_examples: list[tuple[str, str]] = []

    for row in rows:
        out = row["outputs"]
        if isinstance(out, str):
            out = json.loads(out)
        out = out or {}

        # OLD derivation, reproduced exactly: start False, four ways to say True.
        epi_class = out.get("epi_flood_class")
        ses_class = out.get("ses_flood_class") or ""
        old = False
        if epi_class and epi_class not in ("none", ""):
            old = True
        if "1%" in ses_class or "1AEP" in ses_class.upper() or "100" in ses_class:
            old = True
        for study in out.get("flood_studies") or []:
            if (study.get("design") or {}).get("1pct") is not None:
                old = True
                break
        if out.get("hawkesbury_flood_level_100aep") is not None:
            old = True

        try:
            new = _normalise_outputs(out)
        except Exception as exc:  # noqa: BLE001
            # NOT a silent skip. A row we cannot parse is excluded from both
            # sides of the comparison, which understates the count — so it is
            # reported and the exit code changes. A census that quietly drops
            # its hard cases reports a flattering number.
            unparsed.append((str(row['id']), type(exc).__name__))
            continue
        verdict = new.get("in_100yr_flood_zone")

        old_true += 1 if old else 0
        old_false += 0 if old else 1
        if verdict is True:
            now_true += 1
        elif verdict is False:
            now_false += 1
        else:
            now_none += 1
            for src in new.get("in_100yr_flood_zone_unconsulted") or []:
                reasons[src] += 1
            if not old and len(changed_examples) < 3:
                changed_examples.append((str(row["address"])[:46], str(row["run_date"])))

    total = len(rows)
    flipped = now_none if not old_true else now_none
    print("=" * 74)
    print("STORED FLOOD REPORTS — was the served 'not in a flood zone' earned?")
    print("=" * 74)
    print(f"  flood rows in property_reports                 : {total}")
    print("  The verdict is DERIVED ON READ, so no row stores it and no repair")
    print("  is required — every row re-serves through the fixed code.")
    print("  " + "-" * 68)
    print(f"  WAS served: True {old_true:>4}   False {old_false:>4}")
    print(f"  NOW serves: True {now_true:>4}   False {now_false:>4}   Not assessed {now_none:>4}")
    print("  " + "-" * 68)
    if old_false:
        pct = 100.0 * flipped / old_false
        print(f"  {flipped} of {old_false} reports ({pct:.1f}%) that served "
              f"'not in a flood zone'")
        print("  had not established it. Those now read 'Not assessed'.")
    if reasons:
        print("\n  Which source was unreachable (counts overlap — a row can have several):")
        for src, n in reasons.most_common():
            print(f"    {src:<46} {n}")
    if changed_examples:
        print("\n  Examples that flip from 'No' to 'Not assessed':")
        for addr, run_date in changed_examples:
            print(f"    {addr:<48} {run_date}")
    print("=" * 74)
    if unparsed:
        print(f"\n  UNPARSEABLE rows excluded from BOTH sides: {len(unparsed)}")
        for rid, err in unparsed[:5]:
            print(f"    {rid}  {err}")
        print("  The split above therefore understates the count.")
    print("\n  LIMIT: rows written before flood_studies_absent existed carry no")
    print("  marker for a silently skipped council study, and FLOOD_STUDIES has no")
    print("  bounds field, so a Tweed or Wollongong row cannot be escalated")
    print("  retrospectively. The figure counts EPI and SES gaps only — a FLOOR.")
    print("  READ ONLY — nothing was modified.")
    return 2 if unparsed else 0


if __name__ == "__main__":
    sys.exit(main())
