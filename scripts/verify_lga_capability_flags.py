#!/usr/bin/env python3
"""Verify per-council capability flags in frontend-nextjs/lib/lga-data/ against
the live database.

scripts/verify_coverage_stats.py already reconciles the aggregate figures in
frontend-nextjs/lib/coverage.ts against the database. It does not, and was
never meant to, cover the ~10 files in frontend-nextjs/lib/lga-data/, each of
which carries a PER-COUNCIL array with per-council capability flags (e.g.
verify-lgas.ts's `hasDcpData: true` on each entry). A single council's flag can
go stale without moving any of coverage.ts's aggregate counts enough to trip
that check -- the site can then claim a capability for a council where the
data backing it is gone, and nothing says so.

Read-only. Safe to run any time:

    python scripts/verify_lga_capability_flags.py

Exit codes (same convention as verify_coverage_stats.py):
  0 = every checked flag is supported by the live database
  1 = a flag claims a capability the data does not support (drift)
  2 = database unreachable -- UNKNOWN, not the same as clean (#939)

prior-art-checked, 2026-09-10:
  - scripts/, src/, services/, enrichment/: grepped for "lga-data",
    "hasDcpData", "verify-lgas", "shadow-lgas", "flood-lgas" -- the only hits
    (scripts/json_to_ts_stats.py, scripts/refresh_stats_job.py) GENERATE
    secondary-dwelling-stats.ts, they do not verify any flag against the DB.
  - scripts/verify_dcp_formatting.py, lint_fabricated_verdicts.py,
    lint_hardcoded_zone_codes.py, doc_claims.py: reference other
    frontend-nextjs/lib paths, never lga-data.
  - No existing script reconciles any lga-data/*.ts file against the database.
    This script is new coverage, not a duplicate.

WHAT IS CHECKED, and why (see the per-flag functions below for the exact SQL):
  - verify-lgas.ts        hasDcpData    -- vs dcp_setback_controls/lga_registry
  - granny-flat-lgas.ts   hasFloodData  -- vs spatial_overlays (layer_type='flood')

Only flags claiming TRUE are checked. A flag claiming FALSE cannot overclaim a
capability, so it cannot produce the failure mode this script exists to catch
(same asymmetry verify_coverage_stats.py's GROWING set already relies on: a
published figure that undershoots reality is not the problem being guarded
against here).

WHAT IS NOT CHECKED, and why -- see NOT_CHECKED_FLAGS and the file-level note
below it. Each entry names the flag and the reason it was left out, per the
rule that a recorded gap is acceptable and a guessed check is not.

KNOWN RESULT ON TODAY'S DATA, recorded here so a red run is not mistaken for a
broken check: as of 2026-09-10, verify-lgas.ts claims hasDcpData: true for 8
councils (lane-cove, hawkesbury, wollongong, clarence-valley, yass-valley,
bathurst-regional, tamworth-regional, forbes) that have zero current rows in
dcp_setback_controls AND zero rows in regulatory_provisions under any
document_id naming for that council -- confirmed two independent ways. This is
real, pre-existing drift this script was built to catch, not a false positive.
"""
from __future__ import annotations

import os
import re
import sys

# Windows stdout is cp1252 and cannot encode every character this script might
# print (council names are ASCII today, but do not let a future one crash the
# run rather than reporting it). Same guard as verify_coverage_stats.py.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LGA_DATA_DIR = os.path.join(REPO_ROOT, "frontend-nextjs", "lib", "lga-data")
VERIFY_LGAS_TS = os.path.join(LGA_DATA_DIR, "verify-lgas.ts")
GRANNY_FLAT_LGAS_TS = os.path.join(LGA_DATA_DIR, "granny-flat-lgas.ts")

# verify-lgas.ts (and every other lga-data file) uses hyphenated slugs;
# lga_registry and dcp_setback_controls use underscored slugs. A plain
# s/-/_/ swap covers every council except this one, confirmed by querying
# lga_registry directly on 2026-09-10: The Hills Shire's registry slug is
# 'the_hills', not 'the_hills_shire'.
SLUG_OVERRIDE = {"the-hills-shire": "the_hills"}


def db_slug(ts_slug: str) -> str:
    return SLUG_OVERRIDE.get(ts_slug, ts_slug.replace("-", "_"))


# Flags recorded as deliberately NOT checked here, with why. Do not add a flag
# to the checks below without either moving its entry out of this list or
# adding a matching new entry when a new flag is discovered.
NOT_CHECKED_FLAGS = [
    ("granny-flat-lgas.ts", "hasAriData",
     "No independent live-database source was found for this flag. "
     "flood-lgas.ts's ariScenarios array -- the closest DB-shaped relative -- "
     "does not derive from services/flood_truth.py's FLOOD_STUDIES dict (that "
     "dict has exactly 4 entries, keyed to a different and smaller set of "
     "councils than the ones carrying non-empty ariScenarios), and no "
     "spatial_overlays column was found that enumerates a per-feature AEP/ARI "
     "scenario list. Rather than guess at a query, this flag is left unchecked."),
    ("threat-radar-lgas.ts", "hasGrannyFlatPage",
     "Claims a page exists in granny-flat-lgas.ts, not a database fact. "
     "A cross-file consistency check is a different kind of check to the "
     "live-database checks this script performs, and was not built here."),
    ("threat-radar-lgas.ts", "hasFloodPage",
     "Same reasoning as hasGrannyFlatPage: claims a page exists in "
     "flood-lgas.ts, not a database fact."),
]

# Files in lga-data/ with per-council data but no per-council BOOLEAN
# capability flag to check against the database (numbers, strings, or arrays
# instead) -- read in full or in relevant part on 2026-09-10:
#   bushfire-lgas.ts        bfplCoveragePct is a percentage, not a flag
#   conveyancing-lgas.ts    no capability fields at all (name/slug/faqs only)
#   flood-lgas.ts           floodFeatureCount/ariScenarios/floodStudyName are
#                           numbers/arrays/strings, not flags. floodFeatureCount
#                           is exactly the figure hasFloodData is checked against
#                           below, via granny-flat-lgas.ts's own flag.
#   pre-da-history-lgas.ts  riskFactors is a string array
#   secondary-dwelling-stats.ts  a per-YEAR stats shape (YearlyStats), not a
#                           per-council flag array; generated by
#                           scripts/json_to_ts_stats.py / refresh_stats_job.py
#   shadow-lgas.ts          heritageCount is a number
#   solar-lgas.ts           sunshineHoursPerYear/bomStation/heritageCount/
#                           refPaybackYears are numbers/strings


def parse_flag_entries(path: str, flag_names: list[str]) -> list[dict]:
    """Extract {name, slug, <flag>: bool, ...} for each object literal in a
    *_LGAS array.

    Each array entry is matched by its own `name: '...'`, `slug: '...'`, and
    one `flag: true|false` line per requested flag, found independently within
    the object's own text block (not assumed adjacent or ordered) so reordering
    fields in the source file does not silently break parsing.
    """
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    entries: list[dict] = []
    # Every top-level array entry starts with a line of exactly `  {` followed
    # by a `name:` line -- matches the formatting of every *_LGAS.ts file in
    # this repo (verified against verify-lgas.ts and granny-flat-lgas.ts in
    # full, and the interface header of the other eight).
    blocks = re.split(r"\n  \{\n", text)[1:]
    for block in blocks:
        name_m = re.search(r"name:\s*'([^']*)'", block)
        slug_m = re.search(r"slug:\s*'([^']*)'", block)
        if not name_m or not slug_m:
            continue
        flags: dict[str, bool] = {}
        complete = True
        for flag in flag_names:
            fm = re.search(rf"\b{re.escape(flag)}:\s*(true|false)\b", block)
            if not fm:
                complete = False
                break
            flags[flag] = fm.group(1) == "true"
        if not complete:
            continue
        entries.append({"name": name_m.group(1), "slug": slug_m.group(1), **flags})
    return entries


def find_drift(entries: list[dict], flag_name: str, live_counts: dict[str, int]) -> list[str]:
    """Pure comparison: which TRUE claims of `flag_name` in `entries` are
    unsupported by `live_counts`?

    No database connection here -- `live_counts` is a plain {key: count} dict
    the caller has already fetched (keyed however that flag's check keys it,
    e.g. by slug for hasDcpData, by name for hasFloodData). This is the piece
    tests/test_verify_lga_capability_flags.py exercises directly, so the
    decision logic is tested without a live database.

    A key ABSENT from live_counts (the council has no matching database row at
    all) and a key present with count 0 are both treated as unsupported --
    from a flag's perspective "no matching council" and "matching council,
    zero rows" are the same failure: the claim has nothing behind it. A
    council in live_counts that no entry claims the flag for is simply never
    looked at, by design: this script checks the file against the database in
    one direction only (does what the file claims exist?), not the reverse.

    Returns a list of human-readable drift descriptions, empty if every TRUE
    claim is supported.
    """
    drift: list[str] = []
    for e in entries:
        if not e.get(flag_name):
            continue  # only a TRUE claim can overclaim a capability
        key = e["_live_key"]
        count = live_counts.get(key, 0) or 0
        if count <= 0:
            drift.append(
                f"'{e['name']}' ({e['slug']}) claims {flag_name}=true but "
                f"{count} live row(s) back it (key '{key}')"
            )
    return drift


def check_has_dcp_data(cur, slug: str) -> tuple[int, str]:
    """Ground truth for verify-lgas.ts's hasDcpData: at least one CURRENT,
    non-needs_review row in dcp_setback_controls for this council's own slug OR
    any council whose parent_lga is this slug.

    The parent/child half matters for merged councils: Inner West's own
    dcp_setback_controls rows are not current (0 of 29), because its current
    controls live under its absorbed former councils' own slugs (ashfield,
    leichhardt, marrickville) -- exactly the merger handling
    scripts/verify_coverage_stats.py's dcpNumericCouncils query already
    established and tested for the same reason.

    dcp_setback_controls + lga_registry was chosen over replaying the
    document_id regex the /planning-controls page itself uses to decide
    hasDcpData, because that regex is demonstrably unreliable as a ground
    truth: it already misses real data for at least one council (Northern
    Beaches' only matching document is named "Warringah_DCP_2011", which the
    page's own 'Northern_Beaches' pattern does not match), so treating it as
    the source of truth would make THIS check as fragile as the thing it is
    meant to catch drift in.
    """
    dbs = db_slug(slug)
    cur.execute(
        """SELECT COUNT(*) FROM dcp_setback_controls c
           JOIN lga_registry r ON r.slug = c.lga
           WHERE c.is_current = TRUE
             AND (c.needs_review IS NULL OR c.needs_review = FALSE)
             AND r.is_active = TRUE
             AND (r.slug = %s OR r.parent_lga = %s)""",
        (dbs, dbs),
    )
    cnt = cur.fetchone()[0]
    return cnt, f"{cnt} current dcp_setback_controls row(s) for lga_registry slug '{dbs}'"


def check_has_flood_data(cur, name: str) -> tuple[int, str]:
    """Ground truth for granny-flat-lgas.ts's hasFloodData: at least one row in
    spatial_overlays for layer_type='flood' under this council's ALL-CAPS name.

    Matches flood-lgas.ts's own doc comment on floodFeatureCount ("Total flood
    features in spatial_overlays"): every entry checked in granny-flat-lgas.ts
    on 2026-09-10 sets hasFloodData to exactly (that council's floodFeatureCount
    in flood-lgas.ts > 0), so this checks the same underlying claim directly
    against the table floodFeatureCount is itself drawn from.

    KNOWN GAP, left as a comment rather than a guessed fix: spatial_overlays.
    lga_name does not always match a council's display name -- it holds
    'CITY OF PARRAMATTA' and 'SYDNEY', not 'PARRAMATTA' or 'CITY OF SYDNEY'.
    Neither council currently claims hasFloodData: true in granny-flat-lgas.ts,
    so this does not affect today's result, but a future True on either would
    need a name override added here, not assumed to work.
    """
    cur.execute(
        """SELECT COUNT(*) FROM spatial_overlays
           WHERE layer_type = 'flood' AND lga_name = %s""",
        (name.upper(),),
    )
    cnt = cur.fetchone()[0]
    return cnt, f"{cnt} spatial_overlays flood row(s) for lga_name '{name.upper()}'"


def main() -> int:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from dq_db import connect
        conn = connect()
    except Exception as exc:  # noqa: BLE001 -- unreachable is exit 2, not 1 (#939)
        print(f"ERROR: cannot reach the database: {exc}", file=sys.stderr)
        return 2

    cur = conn.cursor()
    drift: list[str] = []

    print("LGA capability flag verification\n")
    print(f"  {'council':<24}{'file':<22}{'flag':<14}   status")
    print("  " + "-" * 78)

    verify_entries = parse_flag_entries(VERIFY_LGAS_TS, ["hasDcpData"])
    if len(verify_entries) < 30:
        print(
            f"ERROR: only parsed {len(verify_entries)} entries from "
            f"{os.path.relpath(VERIFY_LGAS_TS, REPO_ROOT)}, expected 30+ "
            "-- the parser may be out of sync with the file's format.",
            file=sys.stderr,
        )
        conn.close()
        return 1
    verify_live_counts: dict[str, int] = {}
    for e in verify_entries:
        e["_live_key"] = e["slug"]
        if not e["hasDcpData"]:
            continue
        cnt, detail = check_has_dcp_data(cur, e["slug"])
        verify_live_counts[e["slug"]] = cnt
        status = "OK" if cnt > 0 else "DRIFT"
        print(f"  {e['name']:<24}{'verify-lgas.ts':<22}{'hasDcpData':<14}   {status}  ({detail})")
    drift.extend(
        f"verify-lgas.ts: {d}"
        for d in find_drift(verify_entries, "hasDcpData", verify_live_counts)
    )

    granny_entries = parse_flag_entries(GRANNY_FLAT_LGAS_TS, ["hasFloodData", "hasAriData"])
    if len(granny_entries) < 15:
        print(
            f"ERROR: only parsed {len(granny_entries)} entries from "
            f"{os.path.relpath(GRANNY_FLAT_LGAS_TS, REPO_ROOT)}, expected 15+ "
            "-- the parser may be out of sync with the file's format.",
            file=sys.stderr,
        )
        conn.close()
        return 1
    granny_live_counts: dict[str, int] = {}
    for e in granny_entries:
        e["_live_key"] = e["name"]
        if not e["hasFloodData"]:
            continue
        cnt, detail = check_has_flood_data(cur, e["name"])
        granny_live_counts[e["name"]] = cnt
        status = "OK" if cnt > 0 else "DRIFT"
        print(f"  {e['name']:<24}{'granny-flat-lgas.ts':<22}{'hasFloodData':<14}   {status}  ({detail})")
    drift.extend(
        f"granny-flat-lgas.ts: {d}"
        for d in find_drift(granny_entries, "hasFloodData", granny_live_counts)
    )

    conn.close()

    print()
    print("NOT CHECKED (recorded gaps, not silent omissions):")
    for fname, flag, why in NOT_CHECKED_FLAGS:
        print(f"  - {fname} :: {flag}\n      {why}")

    print()
    if drift:
        print(f"DRIFT DETECTED ({len(drift)} flag(s)) -- update the source file(s):")
        for d in drift:
            print(f"  - {d}")
        return 1
    print("All checked capability flags are supported by the live database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
