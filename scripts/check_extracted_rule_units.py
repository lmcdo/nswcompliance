#!/usr/bin/env python3
# prior-art-checked: no existing check compares a v2_extracted_rules value
# against the text it was matched from. Four sweeps, 2026-08-17 on origin/main
# dac0f5e1: (1) DB — the ledger has ZERO rows mentioning v2_extracted_rules;
# (2) python — validate_control_source_values.py does exactly this idea but for
# dcp_setback_controls (1,069 rows) and never reads this column, and
# services/extracted_data_integrity.py flags digits absent from source without
# comparing units; (3) frontend — no reader of v2_extracted_rules performs
# arithmetic on units; (4) plans/memory — CURRENT-AIM names the gap outright,
# "v2_extracted_rules (19,957 served) has no equivalent. Sixth instance of:
# right check, scoped to one slice."
"""A stored length must equal the number and unit in the text it came from.

WHY
---
Two of seventeen unit patterns in numeric_extractor listed `m` before `mm`, so
"600 mm" matched the leading `m` and recorded 600 METRES — a thousandfold error
in a value the product does arithmetic with, not merely displays. The reader was
fixed in #968. Nothing checks what was already stored.

WHAT THIS FOUND, which is not what it was written to find
---------------------------------------------------------
Nothing. Measured 2026-08-17 across every version: 1,101 rules carry both a
length value and the raw text it was matched from, and all 1,101 agree. The 21
known bad values lived in dcp_setback_controls and were repaired there. #968's
note — "values already persisted in v2_extracted_rules ... stay wrong until a
re-extraction runs" — does not hold for this column, and re-deriving 19,957 rows
on the strength of it would have fixed nothing.

So this exists as a GUARD, not a repair: the number is 0 and must stay 0.

THE FIRST VERSION OF THIS CHECK WAS WRONG
-----------------------------------------
Comparing the stored UNIT against the unit in the text flagged 29 rows, and
every one was a legitimate conversion — "350mm wide" stored as 0.35 with unit
"m" is correct. A flag list where most entries are fine trains you to ignore
the list, which is how a real mismatch survives inside it; that is
validate_control_source_values.py's own stated reason for separating derivation
from mismatch, and it applies here unchanged.

The test that discriminates is arithmetic, not vocabulary: convert BOTH sides to
metres and compare. A conversion agrees. A misread is out by exactly the unit
factor.

COVERAGE IS REPORTED, NOT IMPLIED
---------------------------------
Only rules carrying BOTH a numeric value and a raw_match can be checked — 432 of
8,340 served rules. The rest have one or neither and this check says nothing
about them. The denominator is printed on every run so a future run over zero
checkable rows cannot be read as a pass.

Exit 0 = ran and found none. Exit 1 = at least one inconsistency. Exit 2 = could
not measure, which is never a pass.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Unit written in the text -> factor converting it INTO metres. Longest token
# first is irrelevant here because the regex alternation is explicit, but the
# ORDER of that alternation is precisely what caused the original bug, so it is
# written mm|cm|m and must stay that way.
TO_METRES = {"mm": 0.001, "cm": 0.01, "m": 1.0}
LENGTH_IN_TEXT = re.compile(r"(\d+(?:\.\d+)?)\s*(mm|cm|m)\b", re.I)
TOLERANCE_M = 1e-6


def inconsistency(raw_match: str, value: float | None, unit: str | None):
    """Return (stored_m, expected_m) when a rule contradicts its own text.

    None means "consistent, or not checkable". Pure, so the rule can be tested
    without a database — the thing that decides whether the build goes red
    should not need one.
    """
    if value is None or not raw_match:
        return None
    u = (unit or "").strip().lower()
    if u not in TO_METRES:
        return None
    m = LENGTH_IN_TEXT.search(raw_match)
    if not m:
        return None
    expected_m = float(m.group(1)) * TO_METRES[m.group(2).lower()]
    stored_m = float(value) * TO_METRES[u]
    if abs(stored_m - expected_m) < TOLERANCE_M:
        return None
    return stored_m, expected_m


def main() -> int:  # pragma: no cover - CLI entry point
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all-versions", action="store_true",
                    help="include superseded provisions, not just the served set")
    ap.add_argument("--show", type=int, default=15)
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv()
    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        print("ERROR: DATABASE_URL not set — nothing was measured, which is "
              "not a pass. Exiting 2.", file=sys.stderr)
        return 2
    import psycopg2

    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '180000'")
        # prior-art-checked: no new data source — same read, same table, scope
        # written inline instead of interpolated. An earlier version built
        # `WHERE {where}` from a variable that could hold "TRUE", and the DB
        # guard rejected it on exactly that ground: a scope you have to read
        # another line to know is a scope that can quietly widen. --all-versions
        # is now a bound parameter, so widening it is deliberate and the default
        # stays the served set.
        cur.execute("""
            SELECT id, source_council, v2_extracted_rules
              FROM regulatory_provisions
             WHERE (is_current AND v2_is_actionable OR %(all_versions)s)
               AND v2_extracted_rules IS NOT NULL
               AND jsonb_array_length(v2_extracted_rules) > 0
        """, {"all_versions": bool(args.all_versions)})
        rows = cur.fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001 - any failure here is UNKNOWN
        print(f"ERROR: could not measure — {exc}. Exiting 2, which is not a "
              f"pass.", file=sys.stderr)
        return 2

    total_rules = checkable = 0
    bad = []
    for pid, council, rules in rows:
        for r in rules or []:
            if not isinstance(r, dict):
                continue
            total_rules += 1
            verdict = inconsistency(r.get("raw_match") or "",
                                    r.get("value_exact"), r.get("unit"))
            if verdict is None:
                if (r.get("value_exact") is not None and r.get("raw_match")
                        and (r.get("unit") or "").strip().lower() in TO_METRES
                        and LENGTH_IN_TEXT.search(r.get("raw_match"))):
                    checkable += 1
                continue
            checkable += 1
            stored_m, expected_m = verdict
            bad.append((pid, council, r.get("raw_match"), stored_m, expected_m))

    scope = "all versions" if args.all_versions else "served"
    print("=" * 72)
    print(f"EXTRACTED-RULE UNIT CONSISTENCY — {scope}")
    print("=" * 72)
    print(f"provisions with rules : {len(rows)}")
    print(f"rules                 : {total_rules}")
    print(f"CHECKABLE (value + text + length unit): {checkable}")
    print(f"INCONSISTENT          : {len(bad)}")
    print()
    print("A rule is checkable only when it carries BOTH a numeric value and the")
    print("text it was matched from. The rest are not evidence of correctness.")

    if bad:
        print()
        print("Each of these stores a length its own quoted text contradicts:")
        for pid, council, raw, stored_m, expected_m in bad[:args.show]:
            factor = (stored_m / expected_m) if expected_m else 0
            print(f"  id={pid} {council or '(statewide)'}: {raw!r}")
            print(f"     stored {stored_m} m, text says {expected_m} m "
                  f"({factor:.0f}x out)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
