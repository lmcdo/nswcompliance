#!/usr/bin/env python3
"""Live read-only measurements for the DB-dependent DQ rows.

prior-art-checked: reuse not viable because each existing measurement script
answers ONE defect and prints prose (measure_control_type_mismatch.py for
DQ-40, measure_flood_zone_unassessed.py for the flood rate). Sweeps 2026-08-12
on origin/main fe7859b6 found no script that measures a DQ row on demand by id
and returns an exit code, which is what dq_check.py needs to enforce a status.

EVERY NUMBER CARRIES ITS QUERY. That is CLAUDE.md's standing rule -- "a number
without its query is how this section was wrong for months" -- applied to the
defect ledger rather than to a doc, so a reader can re-run any figure rather
than trust it.

A probe is CLEAN (exit 0) only when its count is 0. Anything else exits 1 and
prints the count, the query, and what the count means. An unreachable database
exits 2: UNKNOWN is never reported as clean, because that is the silent-pass
shape this whole effort exists to remove.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dq_db  # noqa: E402

SAR_SOURCE = "Microsoft Planetary Computer S1 RTC"

#: id -> (headline, sql, params, what a non-zero count MEANS)
PROBES: dict[str, tuple[str, str, tuple, str]] = {
    "DQ-50": (
        "Cached reports naming a satellite source that was never queried",
        "SELECT count(*) FROM property_reports WHERE %s = ANY(data_sources)",
        (SAR_SOURCE,),
        "Each row serves a data-source credit for an analysis that never ran. "
        "The cache path returns stored data_sources verbatim, so these keep "
        "being served on every cache hit.",
    ),
    "DQ-50-window": (
        "...of those, still inside the 90-day cache window",
        "SELECT count(*) FROM property_reports "
        "WHERE %s = ANY(data_sources) AND run_date > NOW() - INTERVAL '90 days'",
        (SAR_SOURCE,),
        "These are the ones a user can still be served today.",
    ),
    "DQ-40": (
        "Setback controls still flagged for review",
        "SELECT count(*) FROM dcp_setback_controls WHERE needs_review IS TRUE",
        (),
        "Rows whose control_type or value could not be confirmed against the "
        "source. Not all are defects -- some are deliberate fail-closed flags.",
    ),
    "DQ-32": (
        "Served controls the capacity engine cannot disambiguate by zone",
        # The engine picks a setback/landscaping number per (lga, dev_type,
        # control_type). Where that key holds MORE THAN ONE distinct value the
        # choice is not determined by the data, so a different zone's number can
        # be returned -- a wrong feasibility figure shown to a real user, not a
        # display bug.
        #
        # A partial fix exists (scripts/conveyancing_db.py:413) but only fires
        # on applicability='zone_specific', which is why the count below stays
        # high: it can act on ~24 of these rows.
        "SELECT count(*) FROM dcp_setback_controls d "
        "WHERE d.is_current AND NOT COALESCE(d.needs_review, false) "
        "AND EXISTS (SELECT 1 FROM dcp_setback_controls e "
        "            WHERE e.lga = d.lga AND e.dev_type = d.dev_type "
        "              AND e.control_type = d.control_type "
        "              AND e.is_current AND NOT COALESCE(e.needs_review, false) "
        "              AND COALESCE(e.value_min, -1) <> COALESCE(d.value_min, -1))",
        (),
        "Each row sits in a group where the same council + development type + "
        "control holds more than one value, so the engine's choice is arbitrary "
        "rather than determined. Measured 562 across 171 groups on 2026-08-12. "
        "The 560/168 recorded on 2026-07-31 carries NO query, so the two are "
        "not comparable and no trend can be read from them: the table gained "
        "exactly 2 rows in August (ryde 1175, burwood 1176) and NEITHER sits "
        "in an ambiguity group.",
    ),
    "DQ-32c": (
        "Rows sharing a control slot while stating no condition at all",
        # Under the present-all ruling (user, 2026-08-13) several values for one
        # (lga, dev_type, control_type) is CORRECT -- councils really do set a
        # different parking rate per bedroom count. What is not acceptable is a
        # row a reader cannot attribute: it sits beside two other numbers and
        # says nothing about which case it covers.
        #
        # This replaces the raw 562 as DQ-32's measure. 562 counted rows in
        # ambiguous groups and treated every one as a defect; 556 of them
        # already state their case and are fine. Counting those was what made
        # DQ-32 look like weeks of adjudication when it was six rows.
        "SELECT count(*) FROM dcp_setback_controls d "
        "WHERE d.is_current AND NOT COALESCE(d.needs_review, false) "
        "AND COALESCE(TRIM(d.condition), '') = '' "
        "AND EXISTS (SELECT 1 FROM dcp_setback_controls e "
        "            WHERE e.lga = d.lga AND e.dev_type = d.dev_type "
        "              AND e.control_type = d.control_type "
        "              AND e.is_current AND NOT COALESCE(e.needs_review, false) "
        "              AND COALESCE(e.value_min, -1) <> COALESCE(d.value_min, -1))",
        (),
        "Each row shares a control slot with a different value while stating "
        "nothing about when it applies, so no reader can tell which of them is "
        "theirs and the condition text cannot be shown because there is none. "
        "Measured 6 on 2026-08-13, against 556 rows in the same groups that DO "
        "state their case. Fixing these needs a source lookup per row, not a "
        "presentation change.",
    ),
    "DQ-32b": (
        "Rows naming a zone that the zone filter can never act on",
        # The filter at conveyancing_db.py:413 is gated on
        # applicability='zone_specific'. A row whose CONDITION names a zone but
        # whose applicability is anything else is invisible to it.
        #
        # 59 of the original 76 were tagged on 2026-08-12. The remaining 17 are
        # excluded BY ID because tagging them would delete a correct control --
        # the regex finds a zone code, but the row is not zone-specific:
        #   815-818, 823-826  canada_bay: "within 800m station or 400m B3/B4" is
        #                     PROXIMITY to a zone, not membership in one.
        #   1104-1107, 1153, 13  clause/table references -- (C1.1.9(e)),
        #                     Table C2.2, (B3.8 s3.8.2 C1) -- not zones at all.
        #   71                "major road frontage (C1)": a road classification.
        #   944               has an explicit fallback ("otherwise prevailing");
        #                     tagging would drop the fallback outside R3.
        #   1059              the zone qualifies a SUB-case only; the general
        #                     60% would be lost outside E4.
        # An ID allowlist, not a looser regex: a NEW untagged zone-naming row
        # still fails this check, which a widened pattern would have hidden.
        "SELECT count(*) FROM dcp_setback_controls "
        "WHERE is_current AND NOT COALESCE(needs_review, false) "
        "AND condition ~* '\m(R[1-6]|E[1-4]|C[1-4]|MU1|RU[1-6]|B[1-8]|IN[1-4]|SP[1-3]|W[1-4])\M' "
        "AND COALESCE(applicability, '') <> 'zone_specific' "
        "AND id <> ALL(%s)",
        ([815, 816, 817, 818, 823, 824, 825, 826,
          1104, 1105, 1106, 1107, 1153, 13, 71, 944, 1059],),
        "Rows that ARE zone-dependent but invisible to the zone filter. 59 of "
        "76 tagged on 2026-08-12 (backup dcp_setback_controls_dq32b_backup_"
        "20260812); the other 17 are adjudicated non-defects, excluded by id "
        "and listed in the comment above. Any NEW row naming a zone without "
        "the tag fails this check.",
    ),
    "DQ-57": (
        "Flood reports whose SES study lookup returned no council name",
        # ses_study_lga is NOT a column anywhere -- it is nested inside
        # property_reports.outputs, which is why an earlier attempt to check
        # this looked for a flood_assessments table and found nothing. Use
        # jsonb_path_* rather than a LIKE: no '%' to mis-escape when psycopg2
        # is also given params, and it reads the nested key directly.
        #
        # "needs a decision about what rate counts as fixed" was the stated
        # reason this row had no check for weeks. That was a dodge: for a row
        # declared OPEN the check only has to FAIL while the defect exists,
        # and > 0 does that. A target rate is needed to declare it fixed, not
        # to measure it.
        "SELECT count(*) FROM property_reports "
        "WHERE jsonb_path_exists(outputs::jsonb, '$.**.ses_study_lga') "
        "AND jsonb_path_query_first(outputs::jsonb, '$.**.ses_study_lga') = 'null'::jsonb",
        (),
        "The flood three-state fix scopes its answer by council, and this "
        "counts the reports where it had no council to scope by. Measured "
        "2026-08-12: 346 of 668 flood reports carrying an SES lookup (52%), "
        "against 109 of 151 (72%) recorded earlier -- the volume grew and the "
        "rate improved. Both figures now carry their query; the earlier one "
        "did not.",
    ),
    "DQ-30": (
        "SERVED provisions still tagged with a zone code NSW retired in 2022",
        # The Employment Zones reform replaced B1..B8 with E1/E2/MU1. A served
        # provision still keyed to a B-zone can never match a modern lookup, so
        # it is silently unreachable rather than visibly wrong.
        # is_current AND v2_is_actionable is the served set -- unfiltered this
        # reads 86, which counts superseded rows nobody sees.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable "
        "AND v2_applicable_zones && %s::text[]",
        # This is the RETIRED set, and naming it IS the probe. It is not a
        # lookup table of current zones -- importing the live taxonomy here
        # would defeat the check, because the taxonomy no longer contains these
        # codes. Deliberately frozen at what the 2022 Employment Zones reform
        # abolished. The suppression must sit on the offending line itself:
        # the linter matches per-line, so a comment above it does nothing.
        (["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"],),  # noqa: zone-codes
        "Each row is keyed to a zone code that no longer exists in any LEP, so "
        "it cannot be matched by a current-zone lookup. Measured 3 live on "
        "2026-08-12, against 14 recorded on 2026-08-01 -- the retag reduced it.",
    ),
    "DQ-39": (
        "Current setback controls flagged by a DQ derivability sweep",
        # review_reason carries the sweep tag, so this counts rows a human
        # already judged un-derivable from their own quote -- not a guess.
        "SELECT count(*) FROM dcp_setback_controls "
        "WHERE is_current AND review_reason IS NOT NULL "
        "AND (review_reason LIKE 'DQ %%' OR review_reason LIKE '[DQ-%%')",
        (),
        "Rows whose stored number a reviewer could not derive from the quoted "
        "source_text. The number IS the product, so each one is a served value "
        "with no evidence behind it.",
    ),
    "DQ-29": (
        "SERVED provisions matching the doubled-character OCR corruption pattern",
        # is_current AND v2_is_actionable IS the served set. Without that filter
        # this counts superseded rows nobody can be shown, which overstates the
        # defect -- the DB guard caught exactly that. A corruption count that
        # includes retired rows is not a measure of what a user sees.
        r"SELECT count(*) FROM regulatory_provisions "
        r"WHERE is_current AND v2_is_actionable "
        r"AND provision_text ~ '(([A-Za-z])\2){4,}'",
        (),
        "CANDIDATES, not confirmed defects. The pattern also matches legitimate "
        "text, so this number is an upper bound and needs adjudication before "
        "any repair. Recorded as measured rather than asserted.",
    ),
}


def run(dq_id: str) -> int:
    headline, sql, params, meaning = PROBES[dq_id]
    try:
        conn = dq_db.connect()
    except Exception as exc:  # noqa: BLE001 - any failure here means UNKNOWN
        print(f"{dq_id} UNKNOWN: {exc}")
        print("  UNKNOWN is not CLEAN. Exit 2.")
        return 2

    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        count = cur.fetchone()[0]
    finally:
        conn.close()  # every path, including an exception mid-query

    print(f"{dq_id}: {headline}")
    print(f"  count : {count}")
    print(f"  query : {' '.join(sql.split())}")
    if params:
        print(f"  params: {params}")
    if count:
        print(f"  means : {meaning}")
        return 1
    print("  CLEAN")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--id", required=True, choices=sorted(PROBES))
    args = ap.parse_args()
    return run(args.id)


if __name__ == "__main__":
    sys.exit(main())
