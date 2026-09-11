#!/usr/bin/env python3
# prior-art-checked: extracted from scripts/check_council_completeness.py in the
# same change that created it -- not a new surface. Split because the file hit the
# 500-line ceiling and because the judgement and the measurement are already
# tested separately: this half has no database, no clock and no subprocess, so it
# can be exercised against numbers production has never produced.
"""Thresholds and comparison rules for the per-council completeness check.

Pure functions only. scripts/check_council_completeness.py does the measuring,
recording and alerting; everything here decides what counts as a finding.

Both halves ship in Dockerfile.monitors and both are imported by the commit job.
"""
from __future__ import annotations

#: source_council is NULL for statewide instruments (7,268 served rows, 2026-09-11);
#: one losing its citations is the same defect, so NULL is recorded under this
#: sentinel. Verified the same day: ZERO served rows carry an empty-string
#: source_council, so it cannot collide with a real slug.
STATEWIDE = "(statewide)"

#: field name -> the SQL predicate meaning "this row populates the field". These
#: are OUR OWN identifiers, interpolated into the SELECT because a column name
#: cannot be a bind parameter; --council, the one value from outside, is bound.
#: Adding a field here costs nothing because `counts` is JSONB, and that
#: cheapness is the point -- a field expensive to start watching does not get
#: watched. v2_applicable_dev_types is here because DQ-30 was a tagger defect.
WATCHED_FIELDS: dict[str, str] = {
    "v2_precinct_id": "v2_precinct_id IS NOT NULL",
    "ref_number": "ref_number IS NOT NULL AND ref_number <> ''",
    "pdf_page": "pdf_page IS NOT NULL",
    "v2_topic": "v2_topic IS NOT NULL AND v2_topic <> ''",
    "v2_provision_type": "v2_provision_type IS NOT NULL AND v2_provision_type <> ''",
    "v2_applicable_dev_types": (
        "v2_applicable_dev_types IS NOT NULL "
        "AND array_length(v2_applicable_dev_types, 1) > 0"
    ),
}

#: A fill ratio falling by this many percentage points is a finding. Calibrated
#: against the defect this exists to catch, not picked round: Ashfield's precinct
#: fill went 35.9% -> 5.8% (30.1pp) and Marrickville's 32.7% -> 1.5% (31.2pp).
#: 5pp is far enough below both to catch a partial version of the same failure,
#: and far enough above the movement a normal re-extraction produces.
MATERIAL_DROP_PP = 5.0
#: A fall this large is not a regression, it is a field being emptied.
CRITICAL_DROP_PP = 25.0
#: Served rows legitimately move on re-extraction (a chapter re-extracted to 739
#: live rows from 680 is normal). A tenth of a council disappearing is not.
SERVED_DROP_PCT = 10.0
#: Below this many served rows a single row is worth several percentage points,
#: so ratios are noise. Small councils are compared on absolute counts instead.
#: inner_west serves 11 rows; one row there is 9.1pp.
MIN_SERVED_FOR_RATIO = 20

CRITICAL, STANDARD, INFO = "CRITICAL", "STANDARD", "INFO"


def compare(council: str, prev: dict | None, now: dict) -> list[dict]:
    """Findings for one council. Empty list means nothing went backwards."""
    findings: list[dict] = []
    served_now = now["served"]

    if prev is None:
        findings.append({
            "severity": INFO, "council": council, "field": "-", "state": "NO_BASELINE",
            "message": f"first recording ({served_now} served rows) -- nothing to compare yet",
        })
        return findings

    served_before = prev["served"]

    # A council that served rows and now serves none is the largest possible drop,
    # and it is reported before any per-field comparison: every ratio below would
    # be 0/0, which must not read as "no change".
    if served_before > 0 and served_now == 0:
        findings.append({
            "severity": CRITICAL, "council": council, "field": "served", "state": "DROP",
            "message": f"served {served_before} -> 0 -- this council serves nothing",
        })
        return findings

    if served_before > 0:
        pct = 100.0 * (served_before - served_now) / served_before
        if pct > SERVED_DROP_PCT:
            findings.append({
                "severity": CRITICAL if pct >= 50 else STANDARD,
                "council": council, "field": "served", "state": "DROP",
                "message": f"served {served_before} -> {served_now} ({pct:.1f}% fewer)",
            })

    for field in WATCHED_FIELDS:
        before = prev["counts"].get(field)
        after = now["counts"].get(field)
        # Absent from the older snapshot means it was not measured then. It does
        # NOT mean zero, and treating it as zero would manufacture a 100% "gain"
        # now and a false drop the moment the field is removed from the watch list.
        if before is None or after is None:
            findings.append({
                "severity": INFO, "council": council, "field": field, "state": "NO_BASELINE",
                "message": f"not measured in the previous snapshot (now {after})",
            })
            continue

        # Small councils: a single row is worth several points, so ratios are
        # noise. Compare absolute counts, and only when the denominator did not
        # itself shrink -- otherwise a legitimate smaller re-extraction reads as
        # a field loss.
        if served_before < MIN_SERVED_FOR_RATIO or served_now < MIN_SERVED_FOR_RATIO:
            if after < before and served_now >= served_before:
                findings.append({
                    "severity": STANDARD, "council": council, "field": field, "state": "DROP",
                    "message": (f"{before} -> {after} rows carry it, while served held at "
                                f"{served_now} (small council -- absolute comparison)"),
                })
            continue

        ratio_before = 100.0 * before / served_before
        ratio_after = 100.0 * after / served_now
        fall = ratio_before - ratio_after
        if fall >= MATERIAL_DROP_PP:
            findings.append({
                "severity": CRITICAL if fall >= CRITICAL_DROP_PP else STANDARD,
                "council": council, "field": field, "state": "DROP",
                "message": (f"{ratio_before:.1f}% -> {ratio_after:.1f}% of served rows "
                            f"({before}/{served_before} -> {after}/{served_now}, -{fall:.1f}pp)"),
            })
    return findings


def parse_exposed(out: str) -> set[str] | None:
    """LGA names from audit_precinct_keying_coverage.py's summary line.

    Returns None when the output matches NEITHER known ending. That third state
    is the point: an empty set means "the audit ran and found nothing exposed",
    and if an unrecognised format collapsed to the same value, a change to that
    script's wording would silently switch precinct-exposure detection off and
    overwrite the stored set with an empty one -- so the exposure would never be
    reported again, by a check that reports growth. The caller turns None into a
    finding and leaves the stored set alone.

    Read from the SUMMARY line, not the per-LGA table. The table left-justifies
    the name into a fixed-width column, so taking the first token off a row turns
    "City of Parramatta" into "City" -- a name that matches nothing, which would
    read as a NEW exposure on the next run and a disappearance on the one after.

        >>> 1 LGA(s) EXPOSED (keyed, no reproducible rule): Woollahra
        All keyed LGAs have a reproducible rule.
    """
    for line in out.splitlines():
        if line.startswith(">>>") and "EXPOSED" in line and ":" in line:
            return {n.strip() for n in line.split(":", 1)[1].split(",") if n.strip()}
    if "All keyed LGAs have a reproducible rule" in out:
        return set()
    return None
