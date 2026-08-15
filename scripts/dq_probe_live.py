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
    "DQ-68": (
        "Served provisions carrying no topic, across every document",
        # Opened 2026-08-14 because the ledger was narrower than the defect it
        # described. DQ-24 counts 523 of these — the ones from one SEPP — and
        # scoping it that way was defensible, but it left 2,674 rows in exactly
        # the same state with nothing tracking them.
        #
        # Same served-set scope as DQ-24 (is_current AND v2_is_actionable) so
        # the two numbers are comparable and DQ-24 is a strict subset of this
        # one. 16.0% of the served corpus, concentrated in statewide instruments
        # (2,530) and the Inner West former councils (marrickville 475,
        # leichhardt 123).
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable AND v2_topic IS NULL",
        (),
        "Each row is a provision the product will serve with no topic on it, so "
        "it cannot be routed to the right section of a report or filtered by "
        "topic. Measured 3,197 of 19,957 served provisions on 2026-08-14 — "
        "16.0%. DQ-24 is the Transport & Infrastructure SEPP slice of this "
        "same number (523) and closing that one alone would leave 2,674 here.",
    ),
    "DQ-24": (
        "Served Transport & Infrastructure SEPP provisions with no topic tag",
        # The row read "Transport & Infrastructure SEPP v2_topic retag" and sat
        # in backlog with no check, so nobody could say whether it was still
        # true. It is: 523 provisions that ARE served carry no v2_topic.
        #
        # Scoped to the SERVED set (is_current AND v2_is_actionable) on purpose.
        # 1,248 more non-actionable rows are also untagged, but those are not
        # shown to anyone, and counting them would make the number look four
        # times worse than the exposure while moving for reasons no reader
        # cares about.
        #
        # The pattern needs BOTH 'Transport' and 'Infrastructure': '%Transport%'
        # alone also matches Penrith_DCP_2014__c10_transport_access_parking,
        # which is a council DCP chapter and nothing to do with this row.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE document_id ILIKE %s "
        "  AND is_current AND v2_is_actionable AND v2_topic IS NULL",
        ("%Transport%Infrastructure%2021%",),
        "Each row is a provision the product will serve with no topic on it, so "
        "it cannot be routed to the right section of a report or filtered by "
        "topic. Measured 523 on 2026-08-14, out of 1,076 served provisions from "
        "this SEPP across its two document rows. Not a Transport-only problem: "
        "the same query without the document filter returns 3,197, which is a "
        "separate and larger row to open if anyone wants it.",
    ),
    "DQ-61": (
        "Served councils with no record of WHICH VERSION of the plan we hold",
        # DQ-60 settled that stated_date is the plan's commencement. It says
        # nothing about whether our extract reflects the current text, so a
        # council can be perfectly dated and years stale at once and nothing
        # would show it.
        #
        # The portal_* columns are NOT this fact: they record what the Planning
        # Portal advertises, parsed from planName, and are set on 1 of 28 rows
        # (measured 2026-08-13). currency_* records what OUR COPY is, read from
        # the document. The two disagreeing is the staleness signal -- liverpool
        # is the live case, portal says 'as amended Dec 2019' while one of our
        # source PDFs is named ...2017.
        "SELECT count(DISTINCT d.lga) FROM dcp_setback_controls d "
        "LEFT JOIN dcp_plan_as_at a ON a.lga = d.lga "
        "WHERE d.is_current AND NOT COALESCE(d.needs_review, false) "
        "  AND a.currency_date IS NULL",
        (),
        "Each council serves controls extracted from a document whose version "
        "we never recorded, so no check can tell whether the council has since "
        "amended it. Measured 27 on 2026-08-13, against 2 councils that now "
        "carry a currency date (wingecarribee from its version table, "
        "parramatta from its List of Amendments).",
    ),
    "DQ-62": (
        "Stored commencements that postdate their own plan's name by 3+ years",
        # A plan named 'Strathfield DCP 2005' cannot have commenced in 2020.
        # Where the gap is this wide the stored date is an amendment or a
        # consolidation stamp, which is exactly what DQ-60 forbids in this
        # column.
        #
        # The ledger said this could not be counted -- that a probe "would have
        # to read stated_evidence and judge whether it describes a commencement
        # clause or an amendment table, a text judgement, not a count". It does
        # not: the plan's own NAME carries the year, so the gap is arithmetic.
        #
        # max() over the council's plan names, not min(), so a council holding
        # two plans is measured against the later one -- waverley carries both
        # 'Waverley DCP 2012' and 'Waverley DCP 2022' and its 2022-12-08 date
        # is correct against the 2022 plan. min() would report it as a 10-year
        # gap and the probe would be measuring its own bug.
        "WITH plan_year AS ("
        "  SELECT council AS lga,"
        "         max(substring(dcp_name from '(?:19|20)[0-9]{2}')::int) AS py"
        "    FROM dcp_chapter_registry"
        "   WHERE is_active AND dcp_name IS NOT NULL"
        "   GROUP BY council) "
        "SELECT count(*) FROM dcp_plan_as_at a "
        "JOIN plan_year p ON p.lga = a.lga "
        "WHERE a.stated_date IS NOT NULL "
        "  AND extract(year from a.stated_date) - p.py >= 3",
        (),
        "Each row serves an amendment or consolidation date as the plan's "
        "commencement, which is the date that decides WHICH plan governs an "
        "application. Measured 4 on 2026-08-13: strathfield (DCP 2005 -> "
        "2020-09-08), burwood (2013 -> 2026-03-05), fairfield (2013 -> "
        "2024-08-22), the_hills (2012 -> 2022-05-06). All four were written by "
        "extract_dcp_stated_dates.py from a cover-page 'Effective:' line; every "
        "manually-read council is correct. The WRITER is fixed -- it no longer "
        "takes the latest of several dates, and amendment tables now write "
        "currency_* -- but these four values predate the fix and each needs its "
        "real commencement located before it can be replaced. Clearing them "
        "instead would raise the dateless count the as-at ratchet guards.",
    ),
    "DQ-66": (
        "Controls served shire-wide but cited to a plan covering one town",
        # Wingecarribee publishes its DCP as separate town plans. Three are
        # registered active -- Bowral, Mittagong, Moss Vale -- and only Bowral
        # has been extracted, so every citation we serve for the shire names
        # the Bowral plan.
        #
        # What this does NOT measure is wrong numbers. Part C Sections 2-4,
        # which back all 32 stored controls, are numerically IDENTICAL across
        # the three plans (verified 2026-08-13 against all three PDFs, each
        # hash-matched to dcp_chapter_registry.content_hash: 100/40/16 numeric
        # tokens per section, zero differences in all six pairwise
        # comparisons). A Moss Vale property gets the right number with a
        # citation into a plan that does not govern it, and the table numbering
        # differs between the plans -- Bowral's Table C2.2 is Table C2.1 in
        # Moss Vale -- so the reference does not even resolve.
        #
        # Counts rows, not councils, because the fix is per-plan extraction and
        # the count falls as each sibling plan lands.
        "SELECT count(*) FROM dcp_setback_controls d "
        "JOIN dcp_chapter_registry r "
        "  ON r.council = d.lga AND r.chapter_key = d.source_chapter_key "
        " AND r.is_active "
        "WHERE d.is_current AND NOT COALESCE(d.needs_review, false) "
        "  AND r.chapter_label ~* '(town|village|locality|precinct)[[:space:]]+plan' "
        "  AND EXISTS (SELECT 1 FROM dcp_chapter_registry s "
        "               WHERE s.council = r.council AND s.dcp_name = r.dcp_name "
        "                 AND s.chapter_key <> r.chapter_key AND s.is_active "
        "                 AND s.chapter_label ~* "
        "                     '(town|village|locality|precinct)[[:space:]]+plan' "
        # `NOT COALESCE(needs_review, false)` here too, matching the outer
        # query. Without it "the sibling has controls" would be satisfied by
        # rows that are FLAGGED and therefore never served: the sibling plan
        # would still contribute nothing to any property, the mis-citation
        # would be exactly as unresolved, and the probe would stop counting.
        # A check that goes quiet while the defect stands is the silent-pass
        # shape this ledger exists to remove (caught by the pre-push
        # reviewer, 2026-08-13).
        "                 AND NOT EXISTS (SELECT 1 FROM dcp_setback_controls e "
        "                                  WHERE e.lga = s.council "
        "                                    AND e.source_chapter_key = s.chapter_key "
        "                                    AND e.is_current "
        "                                    AND NOT COALESCE(e.needs_review, false)))",
        (),
        "Each row is served to a whole council area while citing a plan that "
        "covers one town, because sibling town plans exist in the registry with "
        "nothing extracted from them. Measured 30 on 2026-08-13 (wingecarribee, "
        "all from the Bowral Town Plan). The label regex matches 3 of 655 "
        "registry rows and all 3 are these; leichhardt's Balmain and Birchgrove "
        "rows and the_hills' Showground Precinct rows are place-scoped too but "
        "SELF-DISCLOSING -- each names its locality in its own condition text -- "
        "so they are not this defect and are not registered chapters anyway.",
    ),
    "DQ-69": (
        "Active NSW instruments the legislation monitor has not checked in 14 days",
        # LIVENESS, not data quality. The monitor is a 7-day sleep loop on Fly
        # (deploy/flyio-legislation-monitor/run_loop.sh) whose failure branch is
        # `|| echo "will retry next cycle"` -- a permanently broken monitor and a
        # healthy one look identical from outside, and did for 67 days. Nothing
        # read the healthchecks.io ping, and no alert fires on silence.
        #
        # ⚠ This probe's original premise was WRONG and the gate caught it.
        # It assumed last_checked was written on both the change and no-change
        # paths. It was not: check_instrument returned early whenever the source
        # gave no version, which on the PCO path is the NORMAL case, so a run
        # that reported "Checked: 26" wrote zero rows (observed 2026-08-14).
        # The gate therefore could not tell a dead monitor from a healthy quiet
        # one -- the exact confusion it exists to remove. Fixed in the same
        # change: PCO's export lists every amended instrument, so absence is an
        # affirmative confirmation and is now recorded, but ONLY for instruments
        # carrying a pco_instrument_id (one without can never appear, so silence
        # about it means nothing and stamping it would fabricate a check).
        #
        # last_checked is now a true liveness signal and CANNOT be satisfied by
        # editing code -- only by the monitor actually running. 14 days = 2x the
        # 7-day loop period.
        "SELECT count(*) FROM instrument_registry "
        "WHERE is_active AND (last_checked IS NULL "
        "                     OR last_checked < NOW() - INTERVAL '14 days')",
        (),
        "Each row is a SEPP or LEP whose amendments we would not have seen. "
        "Measured 26 of 26 on 2026-08-14: max(last_checked) = 2026-06-08, i.e. "
        "67 days blind, and 1 instrument has never been checked at all. A "
        "residual of 1-2 means those specific instruments fail at the source "
        "(PCO 403 / AustLII Cloudflare) and belongs in notes, not in a retry "
        "loop; a residual of 26 means the monitor is not running.",
    ),
    "DQ-70": (
        "Served provisions whose source PDF has CHANGED since they were extracted",
        # THE OUTCOME SIGNAL, not a mechanism one. Every other gate in this file
        # asks whether some machinery ran. This asks whether what we SERVE still
        # corresponds to the document it came from -- and answers it exactly,
        # with no PDF read, no LLM and no golden set.
        #
        # dcp_chapter_registry carries both halves already:
        #   content_hash                   = the PDF we hold NOW
        #   provisions_extracted_from_hash = the PDF the served rows came FROM
        # When they differ we are knowingly serving an older extraction of a
        # document that has since moved. docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md
        # calls this "the precise unused signal" -- recorded since June, read by
        # nothing.
        #
        # AFFIRMATIVE wrongness, unlike a missing check: we hold the file, we
        # hold a different hash, we still serve the old rows. A code edit cannot
        # move it; only a re-extraction can. Mutation-checked: flipping <> to =
        # returns 12,069, so the comparison is doing the discriminating.
        #
        # Deliberately EXCLUDES the 348 chapters that never recorded a hash, so
        # the number stays a defect count rather than a blend of defect and
        # ignorance. That gap is real and larger -- see the note.
        "SELECT count(*) FROM regulatory_provisions p "
        "  JOIN dcp_chapter_registry r "
        "    ON r.council = p.source_council AND r.chapter_key = p.source_chapter_key "
        " WHERE p.is_current AND p.v2_is_actionable AND r.is_active "
        "   AND r.provisions_extracted_from_hash IS NOT NULL "
        "   AND r.content_hash IS NOT NULL "
        "   AND r.content_hash <> r.provisions_extracted_from_hash",
        (),
        "Each row is a control we serve today that was read out of a version of "
        "the document we no longer hold. We cannot say it reflects the current "
        "text, and we would not know if it had changed. Measured 595 across 10 "
        "chapters on 2026-08-14 (564 active: 206 hash-matched, 10 drifted). "
        "Clears only by re-extracting those chapters -- not by editing code. "
        "SEPARATE AND LARGER: 348 active chapters never recorded which version "
        "their provisions came from at all (25 served provisions among them), so "
        "for those the question cannot even be asked; that gap is not counted "
        "here and needs its own row.",
    ),
    "DQ-71": (
        "Provisions awaiting human approval with NO check against the source document",
        # The reviewer's exposure, not the pipeline's. Each row is a provision a
        # human is being asked to approve into the served corpus with nothing
        # having confirmed its text appears in the council's own PDF.
        #
        # fidelity_status is NOT this check. 19,199 of 19,649 queue rows carry
        # one, but it is a cheap inline heuristic -- garbled glyphs, junk ref,
        # emptied, oversize -- and it never opens the PDF. fidelity_source_quote
        # is the real thing: the passage from the source document that grounds
        # the row. 12 rows in the table's history have one. 0.06%.
        #
        # Cause was a coupling, not an absence: dcp_fidelity_gate.gate_chapter
        # was gated on AI_EXTRACTION, a flag that ALSO swaps the whole
        # deterministic extractor for an LLM (~L1130 of dcp_extract_changed).
        # Nobody was going to enable that in production to get verification, so
        # verification never ran. Decoupled 2026-08-14 behind its own opt-OUT
        # control, fidelity_gate_enabled().
        #
        # Scoped to what the grader can actually grade: 'removed' rows have no
        # new_text to ground, so counting them would inflate this with rows no
        # amount of grading could ever clear.
        "SELECT count(*) FROM dcp_review_queue "
        " WHERE status IN ('pending', 'in_progress') "
        "   AND change_type <> 'removed' AND new_text IS NOT NULL "
        "   AND fidelity_source_quote IS NULL",
        (),
        "Each row is a provision a reviewer is asked to approve on trust. "
        "Measured 3,741 of 3,741 gradeable pending rows on 2026-08-14 -- 100%, "
        "and 0 of all 8,693 pending rows carry a source quote. Clears as the "
        "decoupled gate runs over each chapter; a residual means the grader read "
        "the PDF and could not find the text, which is a FINDING, not a gap.",
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
    "DQ-41": (
        "Setback controls still carrying a manufactured 1 January date",
        # Migration 040's parser built effective_date out of the dcp_version
        # LABEL, so "v2016-current" became 2016-01-01 and
        # "v2014-amended-feb-2026" became 2014-01-01 -- contradicting its own
        # label. 528 of 893 rows were dated this way.
        #
        # Zero is the right target here, unlike DQ-33 below, because no real
        # commencement in this corpus fell on 1 January: every one of the 528
        # was manufactured. A genuine 1 January date arriving later would be a
        # false positive worth one row's adjudication, not a reason to soften
        # this into a ratchet.
        #
        # NULL is deliberately NOT counted. 706 of 1,071 rows have no
        # effective_date and that is the correct state -- "we do not know" is
        # honest, a manufactured date is not. Counting NULLs here would create
        # pressure to invent dates, which is the defect itself.
        "SELECT count(*) FROM dcp_setback_controls "
        "WHERE EXTRACT(MONTH FROM effective_date) = 1 "
        "AND EXTRACT(DAY FROM effective_date) = 1",
        (),
        "Each row dates a setback control from a version label rather than "
        "from the plan, so the date contradicts the document it cites. "
        "Measured 0 of 1,071 on 2026-08-15, down from 528 of 893.",
    ),
    "DQ-33": (
        "Served rows falling through to ALL with no config, ABOVE the recorded floor",
        # A ratchet, not a zero-check, and the subtraction is the whole point.
        # The repair took no_config on served rows 9,854 -> 1,278, and that
        # 1,278 is DELIBERATE: retag_applicability_slug_docids.py resolves a
        # slug only to a key the council's config already declares and leaves
        # anything unrecognised as ALL/no_config rather than guessing a part to
        # improve the number. Probing for zero would demand the one behaviour
        # that repair was written to refuse.
        #
        # Direction of risk, from that script: narrowing HIDES controls, and a
        # hidden binding control is the liability. So the floor may fall only
        # by a council gaining real config, never by invention. GREATEST keeps
        # 0 meaning clean in the runner's contract.
        "SELECT GREATEST(count(*) - 1278, 0) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable "
        "AND v2_dev_type_source = 'no_config'",
        (),
        "no_config on served rows has risen above the 1,278 left deliberately "
        "by the 2026-08-01 retag, so document_ids are failing to resolve "
        "against council config again and those rows silently apply to ALL "
        "development types. SEPARATE AND LARGER: 10,103 served rows carry a "
        "NULL v2_dev_type_source and were never tagged at all, so the question "
        "cannot be asked of them; that gap is not counted here and needs its "
        "own row.",
    ),
    "DQ-73": (
        "Dated setback controls falling on the 1st of a month",
        # CANDIDATES, not confirmed defects -- the same framing as DQ-29, and
        # for the same reason: a real commencement CAN fall on the 1st, so this
        # number is an upper bound that needs adjudication, not 301 things to
        # go and change.
        #
        # What makes it worth a row is the SHAPE, not the count. 301 of 365
        # dated rows is 82%, and the values cluster one per council:
        # canterbury_bankstown 40 rows all on 2025-08-01, bayside 32 all on
        # 2026-04-01, hornsby 30 all on 2025-06-01. Chance does not do that.
        # It is the signature of a month ("August 2025") being stored as a day.
        #
        # Found on 2026-08-15 while PROVING DQ-41's zero was a measurement
        # rather than a query that cannot match. DQ-41 removed the January
        # instances; this asks whether the same manufacturing simply moved to
        # other months.
        #
        # NULL effective_date is deliberately excluded. 706 rows have none and
        # that is the honest state; counting it here would push toward
        # inventing dates, which is the defect.
        "SELECT count(*) FROM dcp_setback_controls "
        "WHERE effective_date IS NOT NULL "
        "AND EXTRACT(DAY FROM effective_date) = 1",
        (),
        "Each row may be claiming day precision for a date we only know to the "
        "month, so a served control is dated more precisely than the evidence "
        "supports. Measured 301 of 365 dated rows on 2026-08-15. This is an "
        "upper bound: adjudicate per council against the plan's own text "
        "before changing any value, and set NULL rather than guess.",
    ),
    "DQ-74": (
        "Served provisions with no applicability provenance recorded at all",
        # SEPARATE FROM DQ-33 and larger. DQ-33 counts rows whose
        # v2_dev_type_source is the literal 'no_config' (1,278) -- rows the
        # tagger looked at and could not resolve. These 10,103 have NULL: the
        # tagger never looked. The two sets are disjoint and must not be added.
        #
        # This is the DQ-68/DQ-24 pattern for the third time: an existing row
        # was scoped to the slice someone happened to measure, leaving the
        # larger population in the same state with nothing watching it. DQ-33
        # cannot see these because its own WHERE clause requires the column to
        # be populated.
        #
        # Opened 2026-08-15 while wiring DQ-33's probe, by reading the full
        # distribution of the column rather than only the value being counted.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable "
        "AND v2_dev_type_source IS NULL",
        (),
        "Each row is served with no record of how -- or whether -- its "
        "applicability was ever decided, so it cannot be told apart from a row "
        "deliberately left as ALL. Measured 10,103 of 19,957 served provisions "
        "on 2026-08-15, against DQ-33's 1,278 no_config rows, which are a "
        "DISJOINT set: do not add the two numbers.",
    ),
    "DQ-76": (
        "Served provisions carrying PDF-extraction residue in place of the text",
        # DQ-27 is NOT reopened by this and must not be. Its scope was
        # marrickville and its fix held perfectly: 36 -> 0, verified at ANY
        # status against this same predicate. This is the SAME corruption in a
        # different part of the corpus that was never looked at.
        #
        # Fourth instance of the row-scoped-to-the-slice-someone-measured
        # pattern (after DQ-24/DQ-68 and DQ-33/DQ-74). Every affected row is a
        # STATEWIDE instrument, where source_council IS NULL -- so DQ-27's
        # council-scoped query could not have found them however carefully it
        # was written. The lesson is about the WHERE clause, not the effort.
        #
        # Found on 2026-08-15 by writing a check for a row whose ledger entry
        # said only "Historic." rather than trusting that status.
        #
        # WIDENED 2026-08-15 after the first version was shown unfit. It listed
        # five macros I had happened to see (mathsf, mathfrak, mathtt, mathrm,
        # pmb) and so counted 10 while reporting CLEAN on 89 rows carrying the
        # identical fault -- a row with only \dag, \bullet, \div, \frac or
        # \lambda scored green. A check that cannot fail on most of its own
        # defect class is the DQ-30 "0% drift" shape, which passed while 241
        # rows stayed broken.
        #
        # The predicate now describes the FAULT -- pdfplumber emitting TeX
        # math-mode residue instead of the rendered glyph -- through three
        # signatures, each validated by reading every row it uniquely
        # contributes rather than by sampling:
        #
        #   1. \word   any TeX control sequence. Justified by enumerating the
        #      backslash tokens actually present: mathfrak, dag, mathbf,
        #      bullet, pmb, mathtt, div, phantom, ast, cdots, zeta, begin/end,
        #      textrm, pounds, frac, ell, tau, overbar, nu, ddot, vec, sf,
        #      overline, lambda, operatorname, Delta, scriptstyle. All TeX.
        #   2. $ NOT followed by a digit. 94 rows carry $ before a digit and
        #      are money; this catches none of them. The 18 it uniquely finds
        #      are '$L_{A10}$', '1 in 20 $( 5 % )', '$F o o d A c t 2003'.
        #   3. a brace group wrapping a single symbol. The 24 it uniquely
        #      finds are the worst of the set: '12 00 { m } 2' for 1,200 m2,
        #      '4 {} 000 m 2 { - } 15 m' for a 4,000 m2 lot and a 15 m
        #      setback, '3.6 { m } above ground level' for a height limit.
        #
        # TWO SIGNATURES WERE MEASURED AND REJECTED, on evidence not hunch.
        # Digit-spacing ([0-9] [0-9] [0-9], 87 rows) matches "100 Year ARI
        # Flood Level" and "1% AEP". Superscript-brace ([\^_]\s*\{, 8 rows)
        # matches markdown section ids like 14e_3. Keeping either for coverage
        # would make the number unfallable, which is how a check gets ignored.
        #
        # Regexes rather than LIKE: psycopg2 reads % as a parameter placeholder
        # even when params is empty, so the LIKE form raised IndexError before
        # reaching the database. DQ-29 uses ~ for the same reason.
        # Signature 3 was WIDENED AGAIN on 2026-08-15, after the first repair
        # pass took the count to 0 while 103 rows still carried braces. The
        # character class [-A-Za-z0-9] could not see an EMPTY group '{}', nor
        # '{ : }', nor a multi-character one like '{ t h }' or '{ a m }'. So the
        # metric read clean over '1 {} 200 m m' (1,200mm), '20 { t h } century',
        # '7 { : } 00 p m' and '2 {} 300 {} 000 m 3'.
        #
        # It is now ANY brace. Checked before widening rather than assumed:
        # every one of the 103 rows containing a brace was sampled and none was
        # legitimate. A curly brace has no place in NSW planning text.
        #
        # The lesson is the same one this row keeps teaching: a predicate that
        # enumerates the forms someone has already seen reports clean on the
        # ones they have not. Describe the fault, not the examples.
        r"SELECT count(*) FROM regulatory_provisions "
        r"WHERE is_current AND v2_is_actionable AND ("
        r"provision_text ~ '\\[A-Za-z]{2,}' "
        r"OR (provision_text LIKE '%%$%%' AND provision_text !~ '\$[0-9]') "
        r"OR provision_text LIKE '%%{%%' OR provision_text LIKE '%%}%%')",
        (),
        "Each row shows a reader extraction residue where a regulated value "
        "belongs. Measured 99 served rows on 2026-08-15 (the earlier figure of "
        "10 was the narrow metric, not a smaller defect). Not cosmetic: the "
        "affected text includes '12 00 { m } 2' for 1,200 m2, "
        "'4 {} 000 m 2 { - } 15 m' for a 4,000 m2 lot with a 15 m setback, "
        "'3.6 { m } above ground level' for a height limit, and "
        "'Omit 666 m { - } 18 m 3 from clause 3C.28(4)' for an amendment "
        "instruction. Clears only by repairing the text at source; editing the "
        "predicate to make it fall would be the defect this row is about.",
    ),
    "DQ-77": (
        "Served provisions whose units are split by a space (900 m m, 7 p m)",
        # The other half of the extractor fault DQ-76 measures. Found because
        # the DQ-76 repair stripped the '$' from '$F o o d A c t 2003' -- the
        # markup went, the corruption stayed, and the metric could no longer
        # see it. A repair blinding its own metric is worth its own row.
        #
        # Every signature was sampled before inclusion, not assumed:
        #   '900 m m of a side boundary', '600 m m', '150 m m diameter sewer
        #   main', '7 { : } 00 p m', '20 t h century'. A space inside a unit is
        #   never correct here.
        #
        # NOT included: the 4+-spaced-letters signature. It conflates this
        # class with DQ-78's scrambled map text, and a metric that mixes two
        # remedies cannot be driven to zero by either.
        #
        # Deliberately NOT repaired in the same pass as DQ-76. Joining '900 m m'
        # to '900mm' deletes a space between characters, which is safe, but
        # joining 'F o o d A c t' to 'Food Act' requires deciding where the word
        # boundaries are. Those are different risks and want different review.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable AND ("
        r"provision_text ~ '[0-9]\s+m\s+m\M' "
        r"OR provision_text ~ '[0-9]\s+m\s+[23]\M' "
        r"OR provision_text ~ '[0-9]\s+[ap]\s+m\M' "
        r"OR provision_text ~ '[0-9]\s+t\s+h\M')",
        (),
        "Each row shows a measurement whose unit has been split by the PDF "
        "extractor, so '900mm' reaches the reader as '900 m m' and '7pm' as "
        "'7 p m'. Measured 581 across the four signatures on 2026-08-15 "
        "(228 of them the m-m form). The 738 figure recorded while exploring "
        "this was the union INCLUDING the letter-spacing signature, which is "
        "excluded here because it belongs to DQ-78. The value is not wrong, "
        "but the text a planner quotes is not what the instrument says.",
    ),
    "DQ-78": (
        "Served provisions that are scrambled MAP LABELS, not controls at all",
        # Not a formatting defect. These rows are text lifted off a map IMAGE,
        # where labels at different angles interleaved into nonsense:
        #   'Go wrie Street Uni B o D n St r r e ee a t R v o y i c n h f S e
        #    ord S tre t e S t re t e'
        # There is no control in there to repair. The row should not be served.
        #
        # Signature: the fraction of whitespace-separated tokens that are a
        # single letter. Real prose sits near zero -- only 'a' and 'I' -- while
        # interleaved map text is dominated by them.
        #
        # The two thresholds were read off the DISTRIBUTION, not chosen:
        # >=0.50 gives 34, >=0.30 gives 83, >=0.20 gives 128, >=0.10 gives 663.
        # The >=100-token floor is what separates this class from DQ-77: it
        # drops the 31-token 's o o m m' rows, which score 0.29 but are a unit
        # defect, not a map. At tokens>=100 and ratio>=0.20 the result is 111
        # rows and 110 of them are one council, which is the shape of a single
        # broken document rather than a threshold artefact.
        r"SELECT count(*) FROM ("
        r"SELECT cardinality(regexp_split_to_array(btrim(provision_text), '\s+')) AS n, "
        r"(SELECT count(*) FROM unnest(regexp_split_to_array(btrim(provision_text), '\s+')) w "
        r"WHERE w ~ '^[A-Za-z]$') AS singles "
        r"FROM regulatory_provisions "
        r"WHERE is_current AND v2_is_actionable AND length(provision_text) > 80) x "
        r"WHERE n >= 100 AND singles::numeric / n >= 0.20",
        (),
        "Each row is served to a planner as a development control and contains "
        "no control -- it is street names lifted off a map figure and "
        "interleaved into nonsense. Measured 111 on 2026-08-15, of which 110 "
        "are city_of_sydney Section 2 precinct pages and 1 is ku_ring_gai. "
        "Clears by excluding figure pages at extraction, NOT by repairing the "
        "text: there is nothing in these rows to recover.",
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
