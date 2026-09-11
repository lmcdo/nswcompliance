#!/usr/bin/env python3
"""Verify published coverage stats against the live database.

The marketing site publishes corpus/coverage figures from a single source of
truth: frontend-nextjs/lib/coverage.ts. Those numbers drift as coverage grows.
This script re-runs the canonical query behind each DB-backed figure and reports
any that no longer match, so a "never a guess" product never publishes a stale
number it can't trace.

Read-only. Safe to run any time:

    python scripts/verify_coverage_stats.py

Exit code 0 = all DB-backed figures current; 1 = drift found (or DB unreachable).
Editorial/config-derived fields in coverage.ts (dcpFullCouncils, floodLgas, etc.)
have no query here and are not checked.

prior-art-checked: reuse not viable because no coverage-stat drift-checker exists.
  /api/dcp/coverage returns the council list (not the marketing counts);
  api/db-verify is a connection health-check; sepp .../05_verify_completeness.py
  checks SEPP text extraction; drawdown_verify.py is an unrelated service. This
  script uniquely reconciles frontend-nextjs/lib/coverage.ts against the live DB.
"""
from __future__ import annotations

import os
import re
import sys

# See dq_check.py: Windows stdout is cp1252 and cannot encode every character
# this script prints, which aborts the run instead of printing them.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERAGE_TS = os.path.join(REPO_ROOT, "frontend-nextjs", "lib", "coverage.ts")

# key in COVERAGE  ->  (human label, SQL). Must mirror the header of coverage.ts.
QUERIES: dict[str, tuple[str, str]] = {
    "provisionsTotal": (
        "Total provisions",
        "SELECT COUNT(*) FROM regulatory_provisions",
    ),
    "dcpActionableProvisions": (
        "Actionable DCP provisions",
        "SELECT COUNT(*) FROM regulatory_provisions "
        "WHERE v2_is_actionable = TRUE AND v2_dcp_layer IS NOT NULL",
    ),
    "dcpNumericCouncils": (
        "Councils with DCP numeric controls",
        # Matches /api/dcp/coverage/route.ts exactly (fixed 2026-09-07,
        # corrected same day after Sol cross-review HIGH 0.96 caught a
        # first-attempt overcount): Ashfield/Leichhardt/Marrickville
        # (abolished pre-2016-merger councils, parent_lga='inner_west')
        # are aggregated under Inner West's CURRENT display name via
        # COALESCE, not counted as three separate councils, and the
        # needs_review guard is included -- an earlier version of this
        # exact query claimed to "match the route exactly" while actually
        # missing that guard (Sol HIGH 0.99, same review round).
        "SELECT COUNT(DISTINCT COALESCE(parent.display_name, r.display_name)) "
        "FROM dcp_setback_controls c "
        "JOIN lga_registry r ON r.slug = c.lga "
        "LEFT JOIN lga_registry parent ON parent.slug = r.parent_lga "
        "WHERE c.is_current = TRUE "
        "AND (c.needs_review IS NULL OR c.needs_review = FALSE) "
        "AND r.slug != 'nsw_statewide' "
        "AND r.is_active = TRUE "
        "AND (r.parent_lga IS NULL OR parent.is_active = TRUE)",
    ),
    "dcpSetbackRows": (
        "DCP setback/control rows",
        "SELECT COUNT(*) FROM dcp_setback_controls",
    ),
    "heritageAreas": (
        "Heritage conservation areas",
        "SELECT COUNT(*) FROM heritage_conservation_areas",
    ),
    "regulatoryDefinitions": (
        "Regulatory definitions",
        "SELECT COUNT(*) FROM regulatory_definitions",
    ),
    # Added 2026-08-24. Both were classed "editorial" and therefore checked by
    # NOTHING, which is how "130+ LGAs covered" -- more councils than NSW has --
    # sat on the homepage. An editorial exemption is not a reason a number cannot
    # be verified; it is only a reason nobody wrote the query.
    "lgasCovered": (
        "LGAs covered (statewide layer)",
        "SELECT COUNT(DISTINCT lga_name) FROM spatial_overlays WHERE layer_type = 'zone'",
    ),
    "dcpSetbackTripleCouncils": (
        "Councils w/ front+side+rear setback",
        "WITH t AS (SELECT lga, "
        "  COUNT(*) FILTER (WHERE control_type = 'front_setback') AS f, "
        "  COUNT(*) FILTER (WHERE control_type = 'side_setback')  AS s, "
        "  COUNT(*) FILTER (WHERE control_type = 'rear_setback')  AS r "
        "FROM dcp_setback_controls WHERE is_current "
        "  AND (needs_review IS NULL OR needs_review = FALSE) "
        "  AND lga <> 'nsw_statewide' AND lga <> 'inner_west' GROUP BY lga) "
        "SELECT COUNT(*) FROM t WHERE f > 0 AND s > 0 AND r > 0",
    ),
}

FLOOD_TRUTH_PY = os.path.join(REPO_ROOT, "services", "flood_truth.py")


def live_flood_study_count() -> int:
    """How many council flood studies FLOOD_STUDIES actually declares.

    Not a DB fact, which is exactly why it went unchecked: floodStudies was
    published as `floodLgas: 71` and described as "LGAs with modelled flood-depth
    coverage". 71 is the flood OVERLAY council count -- the yes/no layer the depth
    claim explicitly said it was "not just". The real figure is the length of this
    dict, and it is four.
    """
    with open(FLOOD_TRUTH_PY, encoding="utf-8") as fh:
        text = fh.read()
    start = text.find("FLOOD_STUDIES: dict[str, dict] = {")
    if start == -1:
        raise RuntimeError("FLOOD_STUDIES not found in services/flood_truth.py")
    end = text.find(chr(10) + "}" + chr(10), start)
    block = text[start:end]
    return len(re.findall(r"^\s{4}[\"']\w+[\"']\s*:\s*\{", block, re.M))

def live_flood_depth_study_count() -> int:
    """How many studies can actually answer a DEPTH question.

    NOT the same as len(FLOOD_STUDIES), and the difference was a live overclaim.
    Five surfaces said "modelled flood depth ... 4 studies" and one named
    Hawkesbury among them, while Hawkesbury's entry carries has_depth=False --
    its rasters are water LEVEL only, with no pre-computed depth band. The
    published 4 was verified against the number of studies INGESTED, so the check
    passed while the claim it was supposed to protect was false. That is the
    "a check can PASS on the wrong artifact" failure, and this is the artifact it
    should have been reading.
    """
    with open(FLOOD_TRUTH_PY, encoding="utf-8") as fh:
        text = fh.read()
    start = text.find("FLOOD_STUDIES: dict[str, dict] = {")
    if start == -1:
        raise RuntimeError("FLOOD_STUDIES not found in services/flood_truth.py")
    end = text.find(chr(10) + "}" + chr(10), start)
    block = text[start:end]
    return len(re.findall(r'"has_depth":\s*True', block))


# Growing counts are published rounded DOWN (e.g. 53,716 -> "53,000+"). A live
# value ABOVE the stored integer is fine (the "+" still holds); only a live value
# BELOW the stored integer means the published claim is now overstated.
GROWING = {"provisionsTotal", "dcpActionableProvisions", "dcpSetbackRows",
           "regulatoryDefinitions"}


def parse_coverage_ts() -> dict[str, int]:
    """Extract the COVERAGE {...} integer block from coverage.ts."""
    with open(COVERAGE_TS, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"export const COVERAGE\s*=\s*\{(.*?)\}\s*as const", text, re.S)
    if not m:
        print("ERROR: could not find the COVERAGE object in coverage.ts", file=sys.stderr)
        sys.exit(1)
    body = m.group(1)
    return {k: int(v.replace(",", "")) for k, v in re.findall(r"(\w+):\s*([\d,]+)", body)}


def main() -> int:
    try:
        from dotenv import load_dotenv
        import psycopg2
    except ImportError as exc:  # pragma: no cover
        print(f"ERROR: missing dependency ({exc}). pip install psycopg2-binary python-dotenv", file=sys.stderr)
        return 1

    load_dotenv(os.path.join(REPO_ROOT, ".env"), override=True)
    published = parse_coverage_ts()

    # prior-art-checked: reuse IS viable and is what this now does. This script
    # demanded PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD, which nothing in the
    # repo sets -- every other consumer reads DATABASE_URL -- so it exited 1 on
    # "cannot reach the database: 'PGHOST'" wherever it ran. That is why it was
    # never wired into CI or a hook, and why the marketing site's published
    # coverage figures could drift from the database without one failing check.
    # scripts/dq_db.py already resolves DATABASE_URL from the main checkout's
    # .env and returns a read-only connection with a 30s statement timeout,
    # which is exactly this script's requirement, so it replaces the hand-built
    # connect rather than sitting beside it. The PG* path stays as a fallback
    # for anyone who does set those.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from dq_db import connect as _dq_connect
        conn = _dq_connect()
    except Exception as exc:  # noqa: BLE001
        try:
            conn = psycopg2.connect(
                host=os.environ["PGHOST"], port=os.environ["PGPORT"],
                dbname=os.environ["PGDATABASE"], user=os.environ["PGUSER"],
                password=os.environ["PGPASSWORD"], connect_timeout=15,
            )
            conn.set_session(readonly=True)
        except Exception:  # noqa: BLE001
            # Exit 2, not 1: unreachable is UNKNOWN, not "the figures disagree".
            # Collapsing those two turned main red on 2026-08-12 (#939).
            print(f"ERROR: cannot reach the database: {exc}", file=sys.stderr)
            return 2
    cur = conn.cursor()

    drift: list[str] = []
    print(f"Coverage stat verification  (source: {os.path.relpath(COVERAGE_TS, REPO_ROOT)})\n")
    print(f"  {'stat':<34}{'published':>11}{'live':>10}   status")
    print("  " + "-" * 66)
    for key, (label, sql) in QUERIES.items():
        want = published.get(key)
        if want is None:
            print(f"  {label:<34}{'—':>11}{'—':>10}   MISSING from coverage.ts")
            drift.append(f"{key}: absent from COVERAGE object")
            continue
        cur.execute(sql)
        live = cur.fetchone()[0]
        if key in GROWING:
            ok = live >= want                      # "+" claim: live may exceed, not fall below
            status = "OK" if ok else "OVERSTATED"
        else:
            ok = live == want                      # exact figure
            status = "OK" if ok else "DRIFT"
        if not ok:
            drift.append(f"{key}: published {want:,} vs live {live:,}")
        print(f"  {label:<34}{want:>11,}{live:>10,}   {status}")

    # --- non-DB invariants -------------------------------------------------
    # floodStudies: parsed from services/flood_truth.py, not the database.
    want_fs = published.get("floodStudies")
    try:
        live_fs = live_flood_study_count()
    except Exception as exc:  # noqa: BLE001
        print(f"  {'Council flood studies':<34}{'—':>11}{'—':>10}   UNREADABLE ({exc})")
        drift.append(f"floodStudies: cannot read FLOOD_STUDIES ({exc})")
    else:
        ok = want_fs == live_fs
        print(f"  {'Council flood studies':<34}{want_fs if want_fs is not None else '—':>11}"
              f"{live_fs:>10}   {'OK' if ok else 'DRIFT'}")
        if not ok:
            drift.append(f"floodStudies: published {want_fs} vs FLOOD_STUDIES {live_fs}")

    # floodDepthStudies: the subset that can answer DEPTH. Separate from the
    # count above ON PURPOSE -- any copy making a depth claim must read this one.
    want_fd = published.get("floodDepthStudies")
    try:
        live_fd = live_flood_depth_study_count()
    except Exception as exc:  # noqa: BLE001
        print(f"  {'  ...of those, with DEPTH':<34}{'—':>11}{'—':>10}   UNREADABLE ({exc})")
        drift.append(f"floodDepthStudies: cannot read FLOOD_STUDIES ({exc})")
    else:
        ok = want_fd == live_fd
        print(f"  {'  ...of those, with DEPTH':<34}{want_fd if want_fd is not None else '—':>11}"
              f"{live_fd:>10}   {'OK' if ok else 'DRIFT'}")
        if not ok:
            drift.append(
                f"floodDepthStudies: published {want_fd} vs has_depth=True count {live_fd}")
    if (want_fd is not None and want_fs is not None) and want_fd > want_fs:
        drift.append(
            f"floodDepthStudies {want_fd} exceeds floodStudies {want_fs} — "
            "more studies answer depth than exist")

    # lgasCovered can never exceed the number of councils in NSW. This is the
    # check that "130+" needed and did not have.
    total = published.get("totalNswCouncils")
    covered = published.get("lgasCovered")
    if total is not None and covered is not None and covered > total:
        drift.append(
            f"lgasCovered: {covered} exceeds totalNswCouncils {total} — "
            "claims more councils than NSW has"
        )

    conn.close()
    print()
    if drift:
        print("DRIFT DETECTED — update frontend-nextjs/lib/coverage.ts:")
        for d in drift:
            print(f"  - {d}")
        return 1
    print("All DB-backed coverage stats are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
