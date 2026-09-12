#!/usr/bin/env python3
# prior-art-checked: reuses dq_db.session() (this project's one shared read-only
# DB helper) and reproduces the guard stack from scripts/conveyancing_db.py
# fetch_dcp_setbacks rather than inventing one -- that function is the single
# guarded read every surface proxies via frontend-nextjs/lib/dcp-controls-client.
# No new data source. Sweeps 2026-09-12: nothing in scripts/, services/ or
# frontend-nextjs/ measures whether a scope-limited control row is served outside
# its scope; validate_controls_provenance.py asserts provenance exists, and
# validate_control_source_values.py re-checks values against their quotes --
# neither looks at applicability.
"""DQ-99 probe: control rows whose scope says "one precinct" and which are
nonetheless served to every property in the LGA.

THE DEFECT
----------
`dcp_setback_controls.applicability` exists and has a CHECK constraint naming
`precinct_specific` as one of its seven values. Nothing reads it.

The single guarded read -- `scripts/conveyancing_db.fetch_dcp_setbacks`, which
every surface proxies through `frontend-nextjs/lib/dcp-controls-client.ts` (the
one module allowed to source these rows) -- filters on `lga`, `is_current` and
`needs_review`. It does not filter, partition or flag on `applicability`. A row
marked `precinct_specific` is therefore returned for every address in the
council, told apart from a general control by nothing but its `condition` prose.

WHY THAT IS THE DANGEROUS DIRECTION
-----------------------------------
A precinct control is usually MORE PERMISSIVE than the council's general rule --
that is often why the precinct exists. Measured 2026-09-12, leichhardt serves a
**1.0m** front setback to every dwelling house in the LGA, taken from the
Birchgrove and Balmain neighbourhood minimums. The general figure for that
council is several times larger. A consumer reads the smallest number in the
column and builds to it.

This is the same shape as DQ-40, which is why `secondary_street_setback` exists
at all: 20 rows served a 2-4m secondary setback as the 4.5-6m primary. There the
wrong CONTROL TYPE carried a number out of context; here the wrong SCOPE does.

WHAT THE FIX IS NOT
-------------------
Not "delete the rows". A precinct control is real regulatory data and the right
answer inside its precinct. The fix is for the guarded read to carry scope --
either excluding `precinct_specific` from the LGA-wide answer, or returning it
marked so a surface can render it as scoped rather than general. Until then this
count stands at the number of rows being served outside their own scope.

MARKING SCOPE IN A COLUMN NOBODY READS DOES NOT CONTAIN THE SCOPE.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import dq_db  # noqa: E402

# Reproduced from scripts/conveyancing_db.fetch_dcp_setbacks. If that guard
# changes, this probe measures a population no user sees -- the exact failure
# DQ-97 hit on 2026-09-10, when its count went to zero because the rows moved
# rather than because anything was repaired.
_SERVED_GUARD = "is_current = TRUE AND (needs_review IS NULL OR needs_review = FALSE)"

_SCOPED = ("precinct_specific",)


def run() -> int:
    with dq_db.session() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT lga, dev_type, control_type, value_min, unit, section_ref, "
            "       left(coalesce(condition, ''), 70) "
            "FROM dcp_setback_controls "
            "WHERE " + _SERVED_GUARD + " AND applicability = ANY(%s) "
            "ORDER BY lga, control_type, section_ref",
            (list(_SCOPED),),
        )
        rows = cur.fetchall()
    if not rows:
        print("PASSED: no scope-limited control row passes the served guard.")
        return 0
    print(str(len(rows)) + " scope-limited row(s) are SERVED LGA-wide "
          "(DQ-99, not yet fixed -- the guarded read does not carry scope):")
    for lga, dev, ctl, vmin, unit, ref, cond in rows:
        print("  %-14s %-26s %-22s %s%-6s %-28s" % (
            lga, dev, ctl, vmin, unit or "", str(ref)[:28]))
        print("      scope: " + str(cond))
    return 1


if __name__ == "__main__":
    sys.exit(run())
