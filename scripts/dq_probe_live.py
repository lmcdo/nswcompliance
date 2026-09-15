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

# See dq_check.py: Windows stdout is cp1252 and probe text carries characters
# it cannot encode, which aborts the run instead of printing them.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

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
        "Controls served shire-wide but cited to only one of a council's town plans",
        # Wingecarribee publishes its DCP as separate town plans -- Bowral,
        # Mittagong, Moss Vale -- each applying to the land edged on its own map,
        # not to a suburb. The served controls were read from Bowral's.
        #
        # What this does NOT measure is wrong numbers. Part C Sections 2-4 are
        # numerically IDENTICAL across the three plans (2026-08-13, hash-matched
        # PDFs), and on 2026-09-15 every served clause was located in the other
        # two with the same numbers. The defect is the citation: naming one
        # town's plan tells a Mittagong or Moss Vale owner nothing, and the
        # table numbering differs (Bowral's Table C2.2 is Table C2.1 there).
        #
        # Remedy chosen 2026-09-15 ("cite each town's plan"): every served
        # clause cites every town plan that publishes it, recorded per clause
        # and sibling in dcp_clause_sibling_citations (migration 074) and
        # rendered by conveyancing_db.cite_clause. This counts served rows whose
        # clause has no citation into some active sibling town plan of the same
        # DCP. It no longer accepts "the sibling plan has controls of its own":
        # extracting a sibling would triple-serve identical numbers while each
        # copy still cited one town. The citation must match the row's own
        # clause AND the specific sibling, or one citation would excuse them all.
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
        "                 AND NOT EXISTS (SELECT 1 FROM dcp_clause_sibling_citations c "
        "                                  WHERE c.council = r.council "
        "                                    AND c.chapter_key = r.chapter_key "
        "                                    AND c.section_ref = d.section_ref "
        "                                    AND c.sibling_chapter_key = s.chapter_key))",
        (),
        "Each row is served to a whole council area citing one town plan while a "
        "sibling town plan of the same DCP publishes the clause and no citation "
        "into it is recorded. Measured 30 on 2026-08-13 (wingecarribee, all from "
        "the Bowral Town Plan); 0 once dcp_clause_sibling_citations holds its 28 "
        "citations (14 served clauses x 2 sibling plans, 2026-09-15). The label regex matches 3 of 655 "
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
    "DQ-88": (
        "SEPP/LEP instruments flagged needs_review with nobody having cleared it",
        # Split out of DQ-69, deliberately: this does NOT check whether the
        # monitor runs (DQ-69 already does, and it does run) -- it checks
        # whether a HUMAN has looked at what the monitor flagged. A count-only
        # check cannot tell "correctly cleared" from "flag flipped without
        # reading the change", so it does not try.
        #
        # check_failures = 0 is deliberate, not decorative: without it, an
        # instrument whose last fetch FAILED (a source-side problem) would be
        # counted alongside one whose fetch SUCCEEDED and found a genuine
        # change awaiting review -- two different defects with two different
        # fixes, conflated into one count. Sol cross-review flagged this
        # 2026-09-01 before it shipped.
        #
        # Cannot currently distinguish "flagged three weeks ago, still
        # ignored" from "cleared last week, freshly re-flagged this run" --
        # updated_at is bumped on every monitor pass regardless of whether
        # needs_review changed, so age is NOT provable from this schema alone.
        # A count staying non-zero over repeated measurements is still real
        # signal (the backlog isn't clearing), but do not assert a specific
        # instrument's dwell time from this query.
        "SELECT count(*) FROM instrument_registry "
        "WHERE is_active AND needs_review AND check_failures = 0",
        (),
        "Each row is a SEPP or LEP the monitor successfully checked and "
        "deliberately did not auto-apply, waiting for a human to read it. "
        "Measured 7 on both 2026-08-14 and 2026-09-01 -- same count, not "
        "confirmed to be the same instruments, since nothing here timestamps "
        "when a flag was SET rather than merely last touched. Either way the "
        "monitor is correctly refusing to guess; the review step is not "
        "happening. This can rise legitimately as new changes are detected; "
        "it should never sit non-zero for weeks while the underlying "
        "instruments keep serving.",
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
        # fidelity_status is NOT the cheap heuristic this check used to be
        # confused with -- that confusion was about fidelity_status vs
        # fidelity_source_quote, and it ran the other way: 19,199 of 19,649
        # queue rows carry a *heuristic* status (garbled glyphs, junk ref,
        # emptied, oversize) that never opens the PDF. What THIS check counts
        # is dcp_fidelity_gate's own verdict column, fidelity_status, which
        # gate_chapter sets to 'grounded' or 'flagged' -- never left NULL --
        # for every row it actually opens the source PDF and grades.
        #
        # ⛔ CORRECTED 2026-09-05 -- the check itself was wrong, not just
        # unrun. The original query below tested fidelity_source_quote IS NULL
        # as a proxy for "never graded". That column is populated ONLY on a
        # subset of flagged rows (ground_row / _source_quote return a quote
        # only when something was absent AND a source sentence matched at
        # >=40% word overlap) -- a grounded row has nothing to quote, by
        # design, forever. Measured live after running the gate over every
        # then-outstanding chapter (4,742 rows, 9 councils, 186 chapters,
        # 0 left with fidelity_status IS NULL): the old query still read
        # 4,365 "red" -- 3,975 of those were the GROUNDED rows (checked, and
        # fine) plus 390 flagged rows whose quote-matcher didn't clear the
        # 40% bar. A check built to reach zero only when fidelity_source_quote
        # is universal can never pass, because the majority-case (grounded)
        # verdict has no quote to write. See
        # memory/feedback-a-check-can-watch-the-field-the-fix-abandoned.md --
        # ask "can this reach 0 at all" before trusting a red count.
        #
        # OLD query, kept here for the record (never reaches 0 by design):
        #   SELECT count(*) FROM dcp_review_queue
        #    WHERE status IN ('pending', 'in_progress')
        #      AND change_type <> 'removed' AND new_text IS NOT NULL
        #      AND fidelity_source_quote IS NULL
        #
        # Cause of the backlog (separate from the check bug above) was a
        # coupling, not an absence: dcp_fidelity_gate.gate_chapter was gated
        # on AI_EXTRACTION, a flag that ALSO swaps the whole deterministic
        # extractor for an LLM (~L1130 of dcp_extract_changed). Nobody was
        # going to enable that in production to get verification, so
        # verification never ran. Decoupled 2026-08-14 behind its own opt-OUT
        # control, fidelity_gate_enabled().
        #
        # Scoped to what the grader can actually grade: 'removed' rows have no
        # new_text to ground, so counting them would inflate this with rows no
        # amount of grading could ever clear.
        "SELECT count(*) FROM dcp_review_queue "
        " WHERE status IN ('pending', 'in_progress') "
        "   AND change_type <> 'removed' AND new_text IS NOT NULL "
        "   AND fidelity_status IS NULL",
        (),
        "Each row is a provision a reviewer is asked to approve on trust. "
        "Measured 4,705 of 4,705 gradeable pending rows red on 2026-09-04 "
        "(this check's OWN prior query never reaches 0 -- see the block "
        "comment above). Backfilled live 2026-09-05: 9 councils, 186 "
        "chapters, 4,742 rows graded (3,975 grounded, 767 flagged) -- 0 rows "
        "with fidelity_status IS NULL remain gradeable-but-unchecked. 390 of "
        "the 767 flagged rows have no fidelity_source_quote (the matcher "
        "found no source sentence at >=40% word overlap) -- those are still "
        "correctly flagged for human review, just without a one-line quote "
        "to compare against; that is a reviewer-convenience gap, not a "
        "verification gap, and is not what this check measures. Clears "
        "again as new chapters enter the queue and the gate has not yet run "
        "over them -- re-run dcp_fidelity_gate.py per council after each "
        "batch of new extractions, same as this session did.",
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
        "Flood reports the council lookup could have resolved and did not",
        # WAS: count of reports whose ses_study_lga is null. That measured the
        # WRONG FIELD, and it measured it for twelve days after the defect was
        # fixed.
        #
        # ses_study_lga is the LGA of a MATCHED flood study. It is null exactly
        # when no study matched, BY DESIGN, so the old query could never reach
        # 0 and DQ-57 could never close no matter what was repaired. Worse, the
        # fix it was supposed to be watching -- #897, merged 2026-08-10 --
        # deliberately STOPPED scoping on that field: flood_truth.py:1608 reads
        # address_council first and falls back to ses_study_lga only if it is
        # absent. So the probe watched the field the fix abandoned.
        #
        # This asks the question the row is actually about: when the council
        # lookup COULD have answered, did it? A point inside the height layer
        # is one lookup_lga can resolve, so a null council there is a real
        # failure. A point outside it is the coverage gap recorded as its own
        # row -- not this defect, and counting it here would make this row
        # unclosable all over again for a second, different wrong reason.
        #
        # DELIBERATELY NOT COUNTED, and the two places it went instead:
        #   - a point OUTSIDE the height layer            -> DQ-85 (53 councils)
        #   - a report with NO address_council key at all -> DQ-86 (81 servable)
        # The second was raised by cross-review as a hole in this probe, and the
        # exclusion is real: the population here is "key present AND null", so a
        # report predating #897 is not counted. Folding it back in would reopen
        # DQ-57 for rows written before its fix existed, which is how it became
        # unclosable the first time. Different remedy, different row.
        #
        # The second term is not decoration. Without it, address_council
        # vanishing from the outputs empties the population and the probe goes
        # CLEAN on a pipeline that stopped looking up councils entirely: a
        # check that passes hardest exactly when the thing it guards is gone.
        #
        # The third term exists because ST_Contains(geom, NULL) is NULL, not
        # false. A report with no coordinates therefore satisfies neither this
        # probe's EXISTS nor its negation cleanly: it would drop silently out of
        # term 1 and reappear inside DQ-85, reading as a coverage gap when it is
        # really a report the lookup was never given anything to resolve. 0 of
        # 102 today, and 0 rows in the whole table lack coordinates, so this is
        # a hole being closed rather than one being patched -- but the direction
        # it fails in is silent-green, which is the one worth spending a term on.
        #
        # Measured 2026-08-24, all live: 533 flood reports have run the lookup,
        # 431 carry a council and 102 do not; 0 of those 102 sit inside the
        # height layer and 102 sit outside it. The 109 pre-#897 reports that
        # never ran the lookup at all and DO sit inside the layer are the
        # historical value this query was forced red on.
        "SELECT ("
        "  SELECT count(*) FROM property_reports p"
        "   WHERE jsonb_path_exists(p.outputs::jsonb, '$.**.address_council')"
        "     AND jsonb_path_query_first(p.outputs::jsonb, '$.**.address_council')"
        "         = 'null'::jsonb"
        "     AND EXISTS (SELECT 1 FROM spatial_overlays s"
        "                  WHERE s.layer_type = 'height'"
        "                    AND ST_Contains(s.geom,"
        "                          ST_SetSRID(ST_MakePoint(p.lng, p.lat), 4326)))"
        ") + ("
        "  CASE WHEN (SELECT count(*) FROM property_reports"
        "              WHERE jsonb_path_exists(outputs::jsonb, '$.**.address_council')"
        "                AND jsonb_path_query_first(outputs::jsonb,"
        "                      '$.**.address_council') <> 'null'::jsonb) = 0"
        "       THEN 1 ELSE 0 END"
        ") + ("
        "  SELECT count(*) FROM property_reports p"
        "   WHERE jsonb_path_exists(p.outputs::jsonb, '$.**.address_council')"
        "     AND jsonb_path_query_first(p.outputs::jsonb, '$.**.address_council')"
        "         = 'null'::jsonb"
        "     AND (p.lat IS NULL OR p.lng IS NULL)"
        ")",
        (),
        "A flood report sits inside the height layer -- a point "
        "lga_lookup.lookup_lga CAN resolve -- and still carries no council, so "
        "the three-state scoping at flood_truth.py:1608 has nothing to scope "
        "by where it should have had something. Or, the second term, no report "
        "carries a council at all, which means the lookup stopped running "
        "rather than started failing. NOT counted here: the 102 reports whose "
        "point falls outside the height layer, because no council polygon "
        "exists there to find. That is a coverage gap, it is real, and it has "
        "its own row -- see DQ-85.",
    ),
    "DQ-85": (
        "NSW councils lookup_lga cannot resolve, because it reads a partial layer",
        # The residual DQ-57 leaves behind, split off rather than folded in.
        # DQ-57 is "did the lookup answer where it could". This is "where can it
        # not answer at all", and the two have different remedies. Folding them
        # together is how DQ-57 got a check that could never reach 0 first time.
        #
        # lga_lookup.lookup_lga reads spatial_overlays WHERE layer_type =
        # 'height'. Both the DQ-57 ledger row and ce-satellite-repair-PROMPT.md
        # describe that as resolving LGA "statewide". It does not, and the
        # module's own docstring has said "covers 75 LGAs" the whole time.
        #
        # THE BOUNDARIES ARE NOT MISSING. The SAME TABLE holds a 'zone' layer
        # covering 128 distinct lga_name -- every NSW council -- against
        # height's 75 (measured 2026-08-24). So this is not an ingestion
        # backlog, it is a lookup reading the narrower of two layers that sit
        # side by side. 80 of the 102 unresolved flood reports fall inside a
        # zone polygon and would resolve today.
        #
        # Counted as COUNCILS, not reports. The first version of this probe
        # counted the 102 affected reports, and cross-review was right that
        # such a count reaches 0 when those rows age out of the cache while all
        # 53 councils stay exactly as unresolvable -- a check passing because
        # the evidence expired. The council count is derived from the zone
        # layer inside the same table, so NSW's 128 is measured, never
        # hardcoded, and it falls to 0 only when a council actually becomes
        # resolvable.
        "SELECT count(*) FROM ("
        "  SELECT DISTINCT lga_name FROM spatial_overlays"
        "   WHERE layer_type = 'zone' AND lga_name IS NOT NULL"
        "  EXCEPT"
        "  SELECT DISTINCT lga_name FROM spatial_overlays"
        "   WHERE layer_type = 'height' AND lga_name IS NOT NULL"
        ") missing_from_height",
        (),
        "Each row is an NSW council that spatial_overlays can already draw "
        "(it has zone polygons) but which lga_lookup.lookup_lga will never "
        "name, because that function reads only the 'height' layer. Every "
        "satellite product that scopes by council is blind in these councils, "
        "not only flood. Measured 53 of 128 on 2026-08-24, with height at 75. "
        "The flood exposure this causes does NOT serve a false clear: "
        "flood_truth.py:1616 reports an absent study as unconsulted when the "
        "council is unknown, which under-reports deliberately. Remedy is a "
        "lookup change, not an ingestion: 80 of the 102 affected reports fall "
        "inside a zone polygon today.",
    ),
    "DQ-86": (
        "Servable cached flood reports written before the council lookup existed",
        # Raised by cross-review of the DQ-57 probe, and it was right: that
        # probe's population is "the address_council key is PRESENT and null",
        # so a report predating #897 carries no key at all and is excluded. It
        # is not counted by DQ-57 and it is not the DQ-85 coverage gap either --
        # these points sit INSIDE the height layer, so the lookup would answer
        # for every one of them if it were ever asked.
        #
        # Given its own row rather than folded into DQ-57, deliberately. DQ-57's
        # remedy was "call the real lookup", and that is done and verified;
        # reopening it for rows written before the fix existed would make it
        # unclosable for a second time, which is the exact failure being
        # repaired here. This row's remedy is different in kind: regenerate, or
        # wait for the cache window.
        #
        # Scoped to the 90-day cache window because that is the exposure. The
        # same query without the window returns 109; those older rows exist but
        # cannot be served, and counting them would make the number look worse
        # than the risk while moving for reasons nobody can act on. Same scoping
        # choice, same reason, as DQ-50-window.
        "SELECT count(*) FROM property_reports p"
        " WHERE jsonb_path_exists(p.outputs::jsonb, '$.**.ses_in_flood_planning_area')"
        "   AND NOT jsonb_path_exists(p.outputs::jsonb, '$.**.address_council')"
        "   AND p.run_date > NOW() - INTERVAL '90 days'"
        "   AND p.lat IS NOT NULL AND p.lng IS NOT NULL"
        "   AND EXISTS (SELECT 1 FROM spatial_overlays s"
        "                WHERE s.layer_type = 'height'"
        "                  AND ST_Contains(s.geom,"
        "                        ST_SetSRID(ST_MakePoint(p.lng, p.lat), 4326)))",
        (),
        "Each row is a flood report a user can still be served from cache "
        "today, written before #897 added the council lookup, at an address "
        "the lookup CAN resolve. The three-state scoping at "
        "flood_truth.py:1608 has no council for these, so an absent study is "
        "reported as unconsulted rather than scoped -- honest, but weaker than "
        "the answer a regenerated report would give. Measured 81 of 109 on "
        "2026-08-24; the other 28 are outside the cache window and cannot be "
        "served. Falls to 0 as the window rolls or on regeneration.",
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
        #
        # SERVED rows only, corrected 2026-09-14. The first version counted
        # every current row with a tag, and on that date its 38 were 20 rows
        # already held back (needs_review) -- never shown to anyone -- plus 18
        # served rows whose tag was the DQ-40 re-file NOTE ("re-filed
        # front_setback -> secondary_street_setback"), a record of a repair,
        # not a derivability flag. So it read 38 while no served number was
        # flagged, and could only fall by hiding or retiring rows nobody sees.
        # The held-back rows stay candidates for a source check; they are not
        # served values, which is what this row is about.
        "SELECT count(*) FROM dcp_setback_controls "
        "WHERE is_current AND NOT COALESCE(needs_review, false) "
        "AND review_reason IS NOT NULL "
        "AND (review_reason LIKE 'DQ %%' OR review_reason LIKE '[DQ-%%') "
        "AND review_reason NOT LIKE '[DQ-40 %%'",
        (),
        "Served rows whose stored number a reviewer could not derive from the "
        "quoted source_text. The number IS the product, so each one is a served "
        "value with no evidence behind it.",
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
        #
        # HORIZONTAL whitespace only (space or tab), never the regex class
        # \s -- narrowed 2026-09-10 after the ratchet went red with
        # declared=fixed and a count of 1. That one row was NOT a recurrence:
        # id 122374 (canterbury_bankstown riverwood-estate, committed to the
        # served set on 2026-09-09) is DQ-78's map scramble, and the '[ap] m'
        # signature fired on a '2' / 'a' / 'm' sitting on three CONSECUTIVE
        # LINES -- a fragment of '...boundary' interleaved off a map figure.
        # \s spans newlines, so any one-character-per-line scramble region can
        # manufacture a hit for a signature written for same-line prose
        # ('900 m m', '7 p m').
        #
        # MEASURED BEFORE NARROWING, not assumed, because a metric loosened to
        # go green is the exact failure this ledger exists to catch. Across the
        # whole table (superseded pre-repair rows included, so the population
        # the 2026-08-15 repair actually cleared): the old class matches 125
        # rows, space-or-tab matches 118, and all 7 dropped are visibly map
        # scramble -- six city_of_sydney Section 2 precinct pages plus 122374.
        # Zero genuine unit splits are lost. This implements the separation the
        # paragraph above already declares: DQ-77 owns the unit split, DQ-78
        # owns the map scramble, and a metric that mixes them can be driven to
        # zero by neither remedy.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable AND ("
        r"provision_text ~ '[0-9][ \t]+m[ \t]+m\M' "
        r"OR provision_text ~ '[0-9][ \t]+m[ \t]+[23]\M' "
        r"OR provision_text ~ '[0-9][ \t]+[ap][ \t]+m\M' "
        r"OR provision_text ~ '[0-9][ \t]+t[ \t]+h\M')",
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
        "DO NOT BULK-EXCLUDE OR DEACTIVATE THESE ROWS. The top of the "
        "distribution is pure figure text, but rows nearest the cut carry REAL "
        "CONTROLS with map labels interleaved - id 95870 'Ensure that the "
        "safety and amenity of pedestrians and cyclists is not compromised by "
        "off-street parking access points', id 95375 'This locality is bounded "
        "by Ashmore Street to the north', id 95887 'Building heights are to "
        "comply with Figure 6.1'. Dropping them would HIDE BINDING CONTROLS, "
        "which is the harmful direction. Clears by stripping figure text at "
        "extraction while keeping the prose, which needs the source PDF's "
        "layout - the information the extractor discarded. This metric finds "
        "affected rows; it cannot tell a pure-figure row from a mixed one, and "
        "that distinction is the whole remedy.",
    ),
    "DQ-79": (
        "Active chapters whose last fetch returned something too small to be the document",
        # A FETCH FAILURE RECORDED AS AN AMENDMENT. hornsby's part3-residential
        # chapter has url_content_length = 1 and check_failures = 0: the monitor
        # downloaded one byte, called the check successful, hashed it, and
        # stamped url_last_changed.
        #
        # The consequence is not cosmetic. DQ-70 counts a chapter as "source
        # changed since extraction" by comparing those hashes, so hornsby's 32
        # served provisions look amended when the document simply cannot be
        # fetched. The two want OPPOSITE remedies -- an amendment wants
        # re-extraction, a dead URL wants the URL fixed -- and re-extracting on
        # this signal would replace 32 live controls with nothing.
        #
        # download_pdf() already refused a non-PDF Content-Type, added after
        # "HTML error pages hashed as changes". A header is not a body: this
        # response passed that guard. r2_monitor now checks the %PDF- signature
        # and a length floor as well.
        #
        # NULL is excluded deliberately: a chapter never checked is a different
        # state from one checked and found empty, and counting them together
        # would hide which is which.
        "SELECT count(*) FROM dcp_chapter_registry "
        "WHERE is_active AND url_content_length IS NOT NULL "
        "AND url_content_length < 1000",
        (),
        "Each row is a chapter whose recorded 'current' content is too small to "
        "be the document, so its stored hash is a hash of the failure. Any "
        "check comparing that hash reads the chapter as amended. Measured 1 of "
        "524 on 2026-08-15 (hornsby part3-residential, 1 byte, 0 recorded "
        "failures); the next smallest genuine chapter is 277,208 bytes. Clears "
        "by fixing the URL and re-checking, NOT by resetting the hash -- that "
        "would hide the broken URL rather than repair it.",
    ),
    "DQ-80": (
        "Attached portal dates whose plan is no longer the plan we serve",
        # THE GUARD THAT WAS MISSING ON 2026-08-15. The only thing stopping a
        # portal date being attached across a plan-identity mismatch was
        # pick_dcp_result()'s token-subset rule -- a convention living inside
        # the one script it governs. Loosening it is a one-line edit, and
        # NOTHING would have caught the result: check_served_answer_quality
        # counts whether a served row HAS a dated basis, not whether the date
        # belongs to our plan, so attaching Bankstown DCP 2015's date to
        # Canterbury-Bankstown DCP 2023 would have made CURRENCY *fall* and
        # read as progress. Same shape as the caps that used to live in the
        # file they policed (#957).
        #
        # So this re-derives the subset test from what was actually STORED,
        # against the registry's CURRENT dcp_name. It cannot be satisfied by
        # editing the fetcher, and it fires on data drift with no commit --
        # the Hornsby class, where the registry moves 2013 -> 2024 while a
        # date attached under the old identity keeps serving.
        #
        # LEFT JOIN, and a NULL name array counts. The first draft inner-joined
        # the registry, which SILENTLY DROPS an attached date once a council's
        # chapters go inactive -- fail-open, reading CLEAN forever. Proven
        # read-only before shipping: with marrickville's registry removed the
        # inner form returns 0 and this one returns 1.
        #
        # WHOLE-TOKEN comparison on BOTH sides, splitting the portal name with
        # the same delimiter as the registry name. An earlier draft used
        # position(t IN portal_name) -- a substring test -- which reports a
        # match whenever a token merely occurs INSIDE a longer one:
        # position('2027' IN 'marrickville dcp 20270') is nonzero, so a
        # different plan would have satisfied the guard. Measured both forms on
        # the live rows before switching: they agree on every real case
        # (Marrickville 2011, Hornsby 2024 vs the portal's 2013, Inner West
        # Ashfield 2016) and disagree only on the 2027/20270 pair, so this is
        # strictly tighter with no change to today's answer.
        #
        # Stopwords match _name_tokens() in fetch_dcp_as_at_dates.py. Its ies/y
        # normalisation is NOT reproduced, which makes this guard stricter on
        # that one axis only -- a registry name using the 'ies' spelling would
        # read as a mismatch and go RED for a human to resolve, never CLEAN.
        "SELECT count(*) FROM dcp_plan_as_at p "
        "LEFT JOIN (SELECT council, ARRAY_AGG(DISTINCT dcp_name) AS names "
        "             FROM dcp_chapter_registry "
        "            WHERE is_active AND dcp_name IS NOT NULL "
        "            GROUP BY council) r ON r.council = p.lga "
        "WHERE p.portal_date IS NOT NULL "
        "  AND (r.names IS NULL OR NOT EXISTS ("
        "    SELECT 1 FROM unnest(r.names) AS n "
        "     WHERE NOT EXISTS ("
        "       SELECT 1 FROM regexp_split_to_table(lower(n), %s) AS t "
        "        WHERE t <> %s AND t NOT IN (%s,%s,%s,%s,%s,%s) "
        "          AND t NOT IN (SELECT pt FROM regexp_split_to_table("
        "                lower(coalesce(p.portal_plan_name,%s)), %s) AS pt))))",
        ("[^a-z0-9]+", "", "dcp", "development", "control", "plan",
         "comprehensive", "the", "", "[^a-z0-9]+"),
        "Each row serves a commencement date read off a DIFFERENT council "
        "plan than the one we hold -- a fabricated currency claim, which is "
        "worse than the missing date it replaced. Measured 0 of 2 attached "
        "rows on 2026-08-15 (ashfield, marrickville). Falsifiability proven "
        "read-only rather than asserted: a hypothetical registry name of "
        "'Marrickville DCP 2027' returns 1, moving both councils returns 2, "
        "and deleting a council's registry returns 1. Clears by detaching the "
        "date or correcting the registry name -- NEVER by widening the token "
        "match, which is the defect itself.",
    ),
    "DQ-81": (
        "Attached portal dates older than the document we actually hold",
        # THE PORTAL IS ITSELF A STALE SOURCE, and _plan_as_at ranks it FIRST.
        #
        # Confirmed against the councils on 2026-08-15. The NSW Planning Portal
        # reports Marrickville DCP 2011 "as amended 9 September 2022" -- that is
        # Amendment No. 15. Inner West Council's own page lists Amendment No. 18
        # in force since 31 July 2025, with 16 and 17 in between. It reports the
        # Ashfield 2016 plan at the same 2022 date while that plan's own
        # chapters are published Mar-2023 and Apr-2024.
        #
        # Our own registry already knew: the documents we hold last changed
        # 2026-06-22 (ashfield) and 2026-04-06 (marrickville), years after the
        # date the portal put on them. So this needs no new source -- the
        # contradiction is between two columns we already store.
        #
        # WHY DQ-80 DOES NOT COVER IT. That row checks the portal names the
        # right PLAN. This one checks the portal's date is not older than our
        # own copy of that same plan. Both were needed: the identity was
        # correct in both these rows, and the date was stale anyway.
        #
        # WHY IT MATTERS MORE THAN A MISSING DATE. A blank renders no claim. A
        # stale "as at" renders a currency assertion that is wrong, to a reader
        # who cannot tell, about a plan amended three times since -- and it
        # makes the CURRENCY metric FALL, so it books as progress.
        #
        # WHAT THIS PROVES, EXACTLY. url_last_changed records when OUR COPY of
        # the file changed. That is NOT proof the legal instrument was amended
        # -- a re-upload or a cosmetic edit moves it too. What the
        # contradiction does establish is narrower and still disqualifying:
        # the portal's date cannot describe the document we now hold, so it
        # cannot be served as that document's currency. The remedy is
        # adjudication against the plan's own version table, never an automatic
        # detach on this signal alone.
        #
        # SCOPED TO THE PLAN THE DATE IS ATTACHED TO, not merely to the
        # council. cumberland has two active dcp_names ('Cumberland DCP 2021'
        # and 'Cumberland DCP Part B - Residential Zones 2021'); on a
        # council-only join, a change to either would condemn a date belonging
        # to the other. The registry row must match the stored
        # portal_plan_name by the same whole-token rule as DQ-80.
        #
        # EXISTS, not JOIN: a council whose chapters all go inactive must not
        # quietly drop out of the count (the DQ-80 fail-open, same shape).
        "SELECT count(*) FROM dcp_plan_as_at p "
        "WHERE p.portal_date IS NOT NULL "
        "  AND EXISTS (SELECT 1 FROM dcp_chapter_registry r "
        "               WHERE r.council = p.lga AND r.is_active "
        "                 AND r.url_last_changed IS NOT NULL "
        "                 AND r.url_last_changed::date > p.portal_date "
        # A NOT EXISTS over zero tokens is vacuously TRUE, so a name that
        # yields no meaningful tokens would match every portal plan and let an
        # unrelated chapter condemn the date. dcp_name is NOT NULL in the
        # schema today, which makes the null half unreachable -- it is written
        # anyway because the all-stopword half is NOT unreachable ('DCP' alone
        # tokenises to nothing) and both are the same defect.
        "                 AND r.dcp_name IS NOT NULL "
        "                 AND EXISTS ("
        "                   SELECT 1 FROM regexp_split_to_table("
        "                          lower(r.dcp_name), %s) AS t0 "
        "                    WHERE t0 <> %s AND t0 NOT IN (%s,%s,%s,%s,%s,%s)) "
        "                 AND NOT EXISTS ("
        "                   SELECT 1 FROM regexp_split_to_table("
        "                          lower(r.dcp_name), %s) AS t "
        "                    WHERE t <> %s AND t NOT IN (%s,%s,%s,%s,%s,%s) "
        "                      AND t NOT IN (SELECT pt FROM "
        "                            regexp_split_to_table(lower(coalesce("
        "                              p.portal_plan_name,%s)), %s) AS pt)))",
        ("[^a-z0-9]+", "", "dcp", "development", "control", "plan",
         "comprehensive", "the",
         "[^a-z0-9]+", "", "dcp", "development", "control", "plan",
         "comprehensive", "the", "", "[^a-z0-9]+"),
        "Each row serves an 'as at' date that CANNOT describe the document we "
        "now hold, because our own copy changed after it. That disqualifies it "
        "as a currency claim; it is not by itself proof the legal instrument "
        "was amended, so the remedy is adjudication against the plan's own "
        "version table rather than an automatic detach. Measured 2 of 2 "
        "attached rows on 2026-08-15: ashfield portal 2022-09-09 vs document "
        "changed 2026-06-22, marrickville portal 2022-09-09 vs 2026-04-06 -- "
        "and marrickville's was confirmed independently against Inner West "
        "Council's own schedule as Amendment No. 15 where the council is on "
        "No. 18 (31 July 2025), so in that case the staleness is established "
        "and not merely suspected. NEVER clears by re-fetching the portal, "
        "which is the stale source.",
    ),
    "DQ-89": (
        "Active chapters flagged suspect (needs_extraction), most but not all with no served-data impact",
        # A backlog-SIZE check, deliberately not a correctness check -- see
        # DQ-78's own hard lesson: some rows near a suspect boundary carry
        # real controls interleaved with garbage, so a script that bulk-clears
        # this flag would risk hiding a live control, the exact liability
        # direction this project refuses to take. Clearing it needs a human
        # to read the flagged chapter.
        #
        # is_active stays TRUE while needs_extraction is TRUE -- that is the
        # review queue working as designed (hold last-known-good, do not
        # commit the suspect re-extraction) for chapters that HAVE a prior
        # accepted extraction. Sol cross-review caught that this probe's first
        # version asserted "no served-data impact" for the whole count without
        # checking that premise: is_active means "registered", not "serving
        # content" -- one of the 31 (hornsby/part-1-general) has
        # last_extracted_at IS NULL and zero currently-served provisions, i.e.
        # it has never had a successful extraction at all. This probe still
        # counts the whole backlog (that number is real and worth tracking
        # together), but no longer claims blanket safety for it.
        #
        # NOT fixed here, and deliberately not turned into a new sweeping row:
        # the same live check that found hornsby's gap also found 374 active
        # chapters registry-wide with last_extracted_at IS NULL (371 serving
        # zero current provisions) -- far larger and pre-existing, and almost
        # certainly a mix of genuine gaps and chapters (site-specific DCPs,
        # administrative parts) that legitimately need no provision
        # extraction. That population needs its own investigation to tell the
        # two apart before it can be honestly scoped as a defect count -- the
        # exact DQ-74/DQ-56 lesson about not turning an unadjudicated
        # population into a backlog number by assertion.
        "SELECT count(*) FROM dcp_chapter_registry "
        "WHERE is_active AND needs_extraction "
        "AND last_suspect_alert_key IS NOT NULL",
        (),
        "Each row is an active chapter the extraction pipeline flagged as "
        "suspect (two-column interleave, a schema failure, or a count drop "
        "against baseline) and refused to auto-commit. Measured 31 on "
        "2026-09-01/02: 29 new that day (woollahra 22, ku_ring_gai 7, all "
        "timestamped 2026-09-01 03:31 UTC, immediately after Woollahra's "
        "council host migrated every chapter's URL) plus 2 pre-existing and "
        "unrelated (city_of_sydney/section-3-general-provisions, "
        "hornsby/part-1-general, timestamped 2026-08-15, recurring since "
        "2026-08-03). 30 of the 31 have is_active=True AND a currently-served "
        "provision -- genuinely no served-content impact. hornsby/part-1-general "
        "is the exception: never successfully extracted, zero served "
        "provisions -- a real gap, not a stale-but-fine copy.",
    ),
    "DQ-90": (
        "Active, substantive chapters with zero served provisions and no extraction queued",
        # Scoped from a much cruder 374/371-chapter finding: "active chapters
        # registry-wide with no successful extraction" is not by itself a
        # defect count -- most of that population is legitimately excluded
        # (map sheets, covers, TOCs) and asserting the raw number as a defect
        # would be the exact DQ-74/DQ-56 mistake this project has already
        # made and corrected twice. is_spatial and is_inert already exist in
        # the schema for exactly this purpose; this probe is the first thing
        # to actually USE them to separate real gaps from legitimate
        # exclusions, rather than eyeballing chapter_key names.
        #
        # needs_extraction is excluded deliberately: a chapter already queued
        # is DQ-89's population (or DQ-78's), not a SILENT gap -- this probe
        # is specifically for chapters nothing is tracking at all.
        #
        # NOT a correctness check on served content quality (that is DQ-78's
        # job for what IS extracted) -- this is coverage-completeness only:
        # does a currently-served provision exist at all for this chapter.
        #
        # The NOT EXISTS join is scoped on p.source_council = r.council, not
        # chapter_key alone -- chapter_key is NOT unique across councils (e.g.
        # 'landscaping-controls' is reused by 5 councils; sampled and confirmed
        # 2026-09-02, Sol cross-review). Verified live this scoping does not
        # currently change the count (97 either way) but the unscoped join was
        # a latent false-negative risk -- a served chapter in one council could
        # silently mask an unserved chapter with the same key in another.
        #
        # 97 is derived from the 371-count base ("active chapters serving zero
        # current provisions"), NOT the 374-count base ("active chapters never
        # extracted", i.e. last_extracted_at IS NULL) -- the two are close but
        # not identical: 3 chapters have last_extracted_at IS NULL yet DO carry
        # a current provision (consistent with the chapter_key alias-map
        # recovery, PR ad1249a3), so 374-247-24-3=100 while 371-247-24-3=97.
        # Quoting 97 as "of the 374" conflates the two bases -- it is "of the
        # 371".
        "SELECT count(*) FROM dcp_chapter_registry r "
        "WHERE r.is_active AND NOT r.is_spatial AND NOT r.is_inert "
        "AND NOT r.needs_extraction "
        "AND NOT EXISTS (SELECT 1 FROM regulatory_provisions p "
        "                WHERE p.source_chapter_key = r.chapter_key "
        "                AND p.source_council = r.council "
        "                AND p.is_current)",
        (),
        "Each row is a registered, substantive DCP chapter (not a map sheet, "
        "not administrative/inert material, not already queued for "
        "extraction) with zero currently-served provisions -- a silent gap "
        "nothing is tracking. Measured 97 on 2026-09-02. 54 are one council: "
        "Canterbury-Bankstown -- confirmed as its ENTIRE non-spatial/"
        "non-inert active chapter set (68 active total, 14 spatial/inert, "
        "54 remaining, all 54 serving zero provisions), all correctly "
        "identified as the current 2023 DCP, most with the source PDF "
        "already fetched to R2, registered 2026-05-11 -- roughly four "
        "months with the source in hand and never extracted. "
        "dcp_setback_controls (a separate numeric-controls table) DOES have "
        "67 current rows for this council, so only the DCP text/TOC corpus "
        "is empty, not every surface. The remaining 43 are thin 1-3-chapter "
        "gaps scattered across 20 other councils/instruments (2 filed "
        "under council='state' -- Apartment Design Guide chapters, not "
        "a data error) -- consistent with the normal stragglers a "
        "multi-council pipeline carries, not individually investigated "
        "here.",
    ),
    "DQ-91": (
        "Tables a deployed service writes to that have never existed in the catalog",
        # Found in ce-verified-capability-statement-2026-08.md S4 item 11 via the
        # schema-contract gate's baseline (scripts/schema_contract_baseline.json),
        # which accepts these 4 refs as known-invalid so the gate can be enforced
        # today -- "accepted" there means "not blocking CI", not "fixed". None of
        # the 4 had a DQ row or a live check until now; the baseline file is a
        # gate exemption list, not a defect ledger, and nobody was re-reading it.
        #
        # drawdown_verify_audits is the one that matters: services/drawdown_verify.py
        # is registered as a live router in services/compliance_api_server.py (the
        # actual uvicorn entrypoint), and its audit-insert at line ~505 is wrapped
        # in `except Exception: ... # Job is submitted -- don't fail the response`.
        # So the write silently fails and the HTTP response still claims success --
        # CLAUDE.md's own definition of CRITICAL. No frontend caller was found in
        # this repo for the endpoint (2026-09-04 grep), so today's blast radius is
        # probably low, but "probably low because no caller was found" is not the
        # same as measured traffic. Migration 033 exists in migrations/ to create
        # the table and was never run against production.
        #
        # UPDATE 2026-09-05: the other 3 WERE individually re-verified, and it was
        # worse than "not yet checked" -- services/enhanced_compliance_api.py's
        # BASIX branch caught the guaranteed query failure (basix_provisions has
        # never existed) and FABRICATED a plausible-looking result (hardcoded
        # 'BASIX requirements apply for Climate Zone X' text with a hardcoded 90%
        # confidence), live on an unauthenticated page (/authoritative). The
        # special-provisions branch (sepp_provisions, special_provisions_registry)
        # silently dropped hazard/heritage/SEPP checks with no error at all. Fixed
        # by deletion, not migration: no real BASIX/SEPP source data exists to
        # populate these tables honestly, so the code that fabricated/hid the gap
        # was removed outright (see fix/fabricated-compliance-fallback) rather than
        # patched to lie more carefully. This probe's SQL is intentionally left
        # unchanged -- these 3 tables still do not exist, and that remains true
        # and worth tracking -- but the "means" text below no longer describes a
        # live silent-failure risk for them, only drawdown_verify_audits ever was.
        "SELECT count(*) FROM (VALUES "
        "('basix_provisions'),('drawdown_verify_audits'),"
        "('sepp_provisions'),('special_provisions_registry')) AS t(tbl) "
        "WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = t.tbl)",
        (),
        "drawdown_verify_audits was the confirmed silent-failure case and is now "
        "fixed (table created, code fails closed, real tests in CI) -- if this "
        "probe still counts it, that is a regression, not the original bug. "
        "basix_provisions/sepp_provisions/special_provisions_registry are "
        "expected to keep showing here: the code that queried them (and either "
        "fabricated a fake result or silently dropped the check) was deleted "
        "2026-09-05, not replaced with a real implementation, because no real "
        "BASIX/SEPP source data was available to populate them honestly. Their "
        "continued absence is now an unbuilt-feature fact, not a live danger -- "
        "confirm that reading by checking nothing imports the deleted files "
        "(services/enhanced_compliance_api.py, basix_compliance_checker.py, "
        "special_provisions_processor.py, special_provisions_integration.py, "
        "sepp_quantitative_extractor.py) before treating a nonzero count here as "
        "urgent. CAVEAT (Sol cross-review, 2026-09-04, predates the deletion): "
        "this checks EXISTENCE only, not whether an insert actually succeeds "
        "once a table exists -- still true for drawdown_verify_audits going "
        "forward if its schema ever drifts.",
    ),
    "DQ-94": (
        "drawdown_verify_audits exists -- dedicated, zero-tolerance (does not share a count with any other table)",
        # Sol cross-review (2026-09-05, on the push that split DQ-91's 3
        # deliberately-unbuilt tables from the 1 that was actually fixed):
        # DQ-91's probe adds 4 table-existence checks into ONE count. That is
        # fine for a human reading the printed breakdown, but it is exactly
        # the shape a machine ratchet must not rely on -- if drawdown_verify_
        # audits were EVER accidentally dropped again at the same moment one
        # of the 3 unbuilt tables (basix_provisions, sepp_provisions,
        # special_provisions_registry) happened to get created, DQ-91's count
        # would stay at 3 throughout, and a real regression on the one table
        # that matters would report as "unchanged, still open" rather than
        # "newly red". This probe checks drawdown_verify_audits BY NAME,
        # alone, so its result can never be masked by what happens to the
        # other 3. DQ-91 is left as-is (aggregate, informational, already
        # documents this exact caveat) -- this is the row dq_check.py's
        # declared/actual ratchet should actually trust for "is the audit
        # write path still safe".
        # count(*) here must be 0 when CLEAN (table exists) and 1 when RED
        # (missing), matching run()'s convention (nonzero -> red) -- a plain
        # "SELECT count(*) ... WHERE table_name = '...'" would return 1 when
        # the table EXISTS, which is the framework's contract inverted.
        "SELECT count(*) FROM (VALUES ('drawdown_verify_audits')) AS t(tbl) "
        "WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = t.tbl)",
        (),
        "drawdown_verify_audits does not exist. This is the table DQ-91 fixed "
        "end-to-end 2026-09-04 (migration 033 run against production, real "
        "insert/read/delete round-trip proven through the actual functions, "
        "fail-closed code, real-DB tests in CI). If this probe reads red, "
        "the audit write path is broken again -- treat as the original DQ-91 "
        "CRITICAL regardless of what DQ-91's own aggregate count currently "
        "shows.",
    ),
    "DQ-95": (
        "Canterbury-Bankstown DCP extraction attempted for real -- 11 of 52 processed chapters flagged by the artifact scanner, not 52",
        # 2026-09-05, acting on DQ-90 (item #2 of the user's own priority
        # list this session): flipped needs_extraction=TRUE on the 54
        # chapters DQ-90 found registered-but-never-queued (a real,
        # deliberate, backed-up production write -- explicit user
        # authorization given), then ran scripts/dcp_extract_changed.py
        # --council canterbury_bankstown --review (memory-only, no DB
        # writes) repeatedly to see what the pipeline would actually
        # produce before letting anything near regulatory_provisions.
        #
        # FIRST PASS, MISREAD: the CLI's "52 chapter(s) flagged SUSPECT"
        # banner and per-chapter preflight warnings made this look like a
        # total pipeline failure for this council. That banner is a crude,
        # PRE-extraction page-geometry heuristic ("does this page's word
        # layout look two-column") -- it does not look at the actual
        # extracted output at all, and over-triggers heavily. The review
        # file's own OVERALL SUMMARY, further down, carries a SEPARATE,
        # POST-extraction artifact scan ("CHAPTERS WITH EXTRACTION BUGS")
        # that is the real signal -- missed on the first read.
        #
        # CORRECTED, using that real signal: of 52 processed chapters (2 of
        # 54 have no PDF fetched at all yet), exactly **11** are listed
        # under CHAPTERS WITH EXTRACTION BUGS -- chapter-7-5-canterbury-
        # local-centre, chapter-3-4-sustainable-development, chapter-2-2-
        # flood-risk-management, chapter-6-2-bankstown-city-centre,
        # chapter-4-3-heritage-conservation-areas, chapter-11-14-riverwood-
        # estate, chapter-7-6-belmore-and-lakemba, chapter-11-12-445-
        # canterbury-road, chapter-11-9-revesby-hospital, chapter-11-13-
        # former-wsu-campus-milperra, chapter-1-1-introduction-and-
        # administration. 29 of 52 have ZERO artifacts detected
        # ("ARTIFACT CHECK: (none detected)"); the remaining 12 carry minor,
        # under-threshold artifacts, not blocking.
        #
        # Sol cross-review (2026-09-05, HIGH, real, on the push containing
        # this correction): only 1 of the 11 (chapter-7-5) was actually
        # opened and inspected -- real, visible corruption confirmed there
        # (a page number bled into a heading, bare_page_numbers scored 261%
        # of the provision count, several section labels are bare numbers
        # with no title). The other 10 are FLAGGED BY THE SCANNER, not
        # independently verified -- exactly the same shape of over-claim
        # this whole entry exists to correct on the preflight side (that
        # scanner over-triggered; this one has not been shown NOT to). Do
        # not read "11" as "11 manually confirmed" -- it is "11 the
        # post-extraction artifact scan flagged, 1 of which was checked by
        # hand and found real."
        #
        # ALSO TESTED AND REVERTED, same session: this repo already has a
        # working geometric two-column reader (commit 53b0c8ee, 2026-07-29,
        # proven on ashfield/marrickville/city_of_sydney/hornsby) --
        # GEOMETRIC_COLUMN_COUNCILS in scripts/dcp_extract_changed.py.
        # Adding "canterbury_bankstown" to it and re-running the FULL
        # 52-chapter batch produced the IDENTICAL 11-chapter bug list, and
        # 2 FEWER chapters with zero artifacts (27 vs 29) -- a controlled
        # before/after comparison, not a single-chapter spot check, proves
        # the existing fix does not transfer to this council and may make
        # it marginally worse. Reverted; not committed. (A single-chapter
        # test run in isolation had wrongly suggested the fix helped --
        # that chapter turned out to already be clean in the ORIGINAL,
        # pre-edit run too; the error was not checking the real baseline
        # before attributing an unrelated result to the edit.)
        #
        # docs/DCP_EXTRACTION_KNOWN_PATTERNS.md has zero mentions of
        # "two-column" (grepped). No documented, working fix exists for
        # THIS council's specific two-column geometry -- the existing
        # reader was verified, live, not to transfer.
        #
        # NOT committed to production. needs_extraction is correctly left
        # TRUE (these chapters DO still need extraction). No provisions
        # were written to regulatory_provisions in any of these runs; the
        # --review flag guarantees this.
        #
        # Sol cross-review (2026-09-05, MEDIUM, confidence 0.98, on the
        # rebase force-push): the original query here was
        # "WHERE council = 'canterbury_bankstown' AND needs_extraction = TRUE
        # AND last_extracted_at IS NULL" -- no is_active/is_spatial/is_inert/
        # dcp_name scope, so a FUTURE unrelated canterbury_bankstown
        # registry row (a superseded chapter re-added, a new spatial-only
        # chapter registered later) could silently change this count
        # without any connection to this specific extraction attempt.
        # Fixed per Sol's PREFERRED option (an immutable cohort over extra
        # WHERE columns, "because DQ-95 tracks a specific attempt"): scoped
        # to the exact 54 chapter_key values this session's flag flip
        # touched, read back verbatim from the committed pre-write backup
        # (data/db_rollback_backups/..._pre_flag_flip_2026-09-05.json) --
        # not re-derived from any live filter that could itself drift.
        "SELECT count(*) FROM dcp_chapter_registry "
        "WHERE chapter_key = ANY(%s) AND needs_extraction = TRUE "
        "AND last_extracted_at IS NULL",
        (
            [
                "cb-dcp-2023-ch5-1-bankstown",
                "cb-dcp-2023-ch5-2-canterbury",
                "chapter-1-1-introduction-and-administration",
                "chapter-10-1-child-care-centres",
                "chapter-10-2-schools",
                "chapter-10-3-home-businesses",
                "chapter-10-4-non-residential-land-uses",
                "chapter-10-5-places-of-public-worship",
                "chapter-10-6-commercial-land-uses",
                "chapter-10-7-sex-services-premises",
                "chapter-10-8-telecommunications-facilities",
                "chapter-11-1-milton-street",
                "chapter-11-10-chullora-marketplace",
                "chapter-11-11-brighton-avenue",
                "chapter-11-12-445-canterbury-road",
                "chapter-11-13-former-wsu-campus-milperra",
                "chapter-11-14-riverwood-estate",
                "chapter-11-15-marco-avenue",
                "chapter-11-2-undercliffe-bridge-precinct",
                "chapter-11-3-roberts-road",
                "chapter-11-4-croydon-street-precinct",
                "chapter-11-5-riverlands",
                "chapter-11-6-potts-hill",
                "chapter-11-7-auburn-road",
                "chapter-11-8-boorea",
                "chapter-11-9-revesby-hospital",
                "chapter-2-1-site-analysis",
                "chapter-2-2-flood-risk-management",
                "chapter-2-3-tree-management",
                "chapter-2-4-pipeline-corridors",
                "chapter-3-1-development-engineering-standards",
                "chapter-3-2-parking",
                "chapter-3-3-waste-management",
                "chapter-3-4-sustainable-development",
                "chapter-3-5-subdivision",
                "chapter-3-6-signs",
                "chapter-3-7-landscape",
                "chapter-4-1-introduction",
                "chapter-4-2-heritage-items",
                "chapter-4-3-heritage-conservation-areas",
                "chapter-4-4-vicinity-of-places-of-heritage-significance",
                "chapter-6-1-general-requirements",
                "chapter-6-2-bankstown-city-centre",
                "chapter-6-3-campsie-town-centre",
                "chapter-7-1-general-requirements",
                "chapter-7-2-city-west",
                "chapter-7-3-city-east",
                "chapter-7-4-neighbourhood-centres",
                "chapter-7-5-canterbury-local-centre",
                "chapter-7-6-belmore-and-lakemba",
                "chapter-8-1-general-requirements",
                "chapter-8-2-canterbury-road",
                "chapter-8-3-hume-highway",
                "chapter-9-1-general-requirements",
            ],
        ),
        "Chapters still queued for extraction (flag set) but never "
        "successfully extracted. Reads 54 today -- but only 11 of the 52 "
        "already-processed chapters are FLAGGED by the pipeline's own "
        "post-extraction artifact scan (29 read clean, 12 have minor "
        "under-threshold artifacts); only 1 of those 11 was manually "
        "opened and confirmed as a real defect, so 'flagged' is not the "
        "same claim as 'confirmed' for the other 10 -- see the header "
        "comment above. The crude preflight '52 flagged SUSPECT' banner "
        "is not evidence the other 41 are broken either -- do not assume "
        "a nonzero count here means the whole council needs a pipeline "
        "fix. Most of the drop this count needs could plausibly come from "
        "committing the clean/near-clean chapters after a human clears "
        "their (mostly false-positive) SUSPECT flags, matching the "
        "precedent already set for ashfield/marrickville/city_of_sydney/"
        "hornsby (#851) -- not from a pipeline change. The chapters the "
        "artifact scan flags and the 2 missing-PDF chapters are the "
        "candidates for real remaining work, pending per-chapter human "
        "review, not a pipeline-wide failure.",
    ),
    "DQ-96": (
        "housing_sepp_standards/cdc_eligibility_standards rows a KNOWN amendment should have staled, but never did",
        # 2026-09-05, investigating DQ-88 (item #3 of the user's own priority
        # list): DQ-88's own row claimed "SEPP (Housing) 2021 alone backs 241
        # served provisions" -- checked, not assumed: v2_marker ILIKE
        # '%housing%'/'%sepp%' = 0 rows, document_id-linked regulatory_provisions
        # = 12, ref_number text match = 1. None come close to 241 -- that figure
        # traces to an UNRELATED "241-row zone repair" elsewhere in the tracker
        # (line ~722, a DQ-30-adjacent DCP part-key fix), almost certainly copied
        # into DQ-88 by mistake. DQ-88's text is corrected accordingly.
        #
        # Also checked, not assumed: of the 7 instruments DQ-88 names, 4
        # (Canterbury-Bankstown LEP 2023, Parramatta LEP 2023, Sutherland Shire
        # LEP 2015, The Hills LEP 2019) have ZERO rows in `documents` by name,
        # document_type, or any pattern -- nothing was ever extracted from their
        # text, so nothing served can be citing a superseded version of them.
        # Their zoning/numeric standards are served live from the Planning
        # Portal API (services/nsw_planning_api.py), not from stored text, per
        # this repo's own regulatory-data rule. DQ-88's real scope is 3
        # instruments (Inner West LEP 2022, SEPP E&C 2008, SEPP Housing 2021),
        # not 7.
        #
        # The real finding, for the table that actually backs served content:
        # housing_sepp_standards drives CDC eligibility + ADG (real, if smaller
        # than claimed -- 45 rows, 43 tied to SEPP Housing/E&C by
        # source_document). The legislation monitor's W3 auto-stale mechanism
        # (#839, shipped 2026-07-29) is supposed to stamp stale_since/
        # stale_reason on these rows the moment it detects a version change --
        # but sepp_housing_2021's own detected change is dated 2026-04-24,
        # BEFORE #839 existed. The mechanism only fires on a fresh
        # needs_review=FALSE->TRUE transition; there is no backfill sweep for
        # an instrument that was ALREADY flagged when the feature shipped. 33
        # housing_sepp_standards rows (+2 tied to SEPP E&C) predate both the
        # detected amendment and the feature, and still read stale_since IS
        # NULL today -- serving as if current, with no notice, 4+ months after
        # a real, detected legislative amendment.
        #
        # A SECOND, independent gap, confirmed by reading the actual serving
        # code: services/cdc_screen.py already reads stale_since/stale_reason
        # from cdc_eligibility_standards and renders a notice (tests/
        # test_sepp_auto_stale.py::TestCdcEngineNotice pins this). The
        # equivalent path for Housing-SEPP eligibility,
        # services/housing_sepp_eligibility.py, never selected those two
        # columns from housing_sepp_standards at all -- so even a correctly-
        # fired stamp would have served silently, with zero surfaced notice,
        # for every CDC/ADG-eligibility answer this engine computes. FIXED on
        # this branch: _fetch_standards_grouped() now reads stale_since/
        # stale_reason (latest wins, paired with its own reason -- Sol #839's
        # exact finding on cdc_screen.py, replicated and avoided here), and
        # FormEligibility carries both fields through services/upzoning_
        # check.py's existing dataclasses.asdict() serialization with no
        # further wiring needed. 4 new tests (tests/test_housing_sepp_
        # eligibility.py), full suite green.
        #
        # NOT fixed on this branch, and it is a judgement call per instrument,
        # not a script (DQ-88's own note, still true): the 35 pre-existing
        # rows still need someone to actually read what changed on
        # legislation.nsw.gov.au for SEPP Housing 2021 / SEPP E&C 2008 and
        # either update the standard or dismiss with a reason via
        # scripts/update_instrument_provisions.py. This probe measures
        # whether that backfill (or the review closing) has happened --
        # it does not do the review itself.
        "SELECT "
        "  (SELECT count(*) FROM housing_sepp_standards h "
        "   JOIN instrument_registry ir ON ir.instrument_key = 'sepp_housing_2021' "
        "   WHERE ir.needs_review AND h.stale_since IS NULL "
        "     AND h.created_at < ir.last_changed "
        "     AND h.source_document ILIKE %s) "
        "  + "
        "  (SELECT count(*) FROM housing_sepp_standards h "
        "   JOIN instrument_registry ir ON ir.instrument_key = 'sepp_exempt_complying_2008' "
        "   WHERE ir.needs_review AND h.stale_since IS NULL "
        "     AND h.created_at < ir.last_changed "
        "     AND (h.source_document ILIKE %s OR h.source_document ILIKE %s)) "
        "  + "
        "  (SELECT count(*) FROM cdc_eligibility_standards c "
        "   JOIN instrument_registry ir ON ir.instrument_key = 'sepp_exempt_complying_2008' "
        "   WHERE ir.needs_review AND c.stale_since IS NULL "
        "     AND c.created_at < ir.last_changed)",
        ("%housing%", "%exempt%", "%e&c%"),
        "Reads 35 today (33 housing_sepp_standards rows predating the SEPP "
        "Housing 2021 amendment detected 2026-04-24, 2 more tied to SEPP E&C "
        "2008, 0 in cdc_eligibility_standards -- that table's own staling has "
        "worked correctly since #839). This is NOT '35 wrong values being "
        "served' -- the numeric standards may well still be correct; it is "
        "'35 rows serving with zero notice that the source law was amended "
        "and nobody has confirmed they still hold.' Falls to 0 either by a "
        "human completing the review (scripts/update_instrument_provisions.py "
        "clears needs_review, which removes these rows from scope) or by a "
        "backfill sweep stamping stale_since on rows #839 could not reach "
        "retroactively. The read-side half of this gap (services/housing_sepp_"
        "eligibility.py never selecting these columns at all) is fixed on "
        "this same branch -- this count is what remains: the write-side "
        "backfill, and the actual per-instrument legislative review DQ-88 "
        "already named as 'not yet done'.",
    ),
    "DQ-92": (
        "Review-queue rows TAGGED with a suspect extractor-bug signature (unconfirmed per chapter)",
        # Answers a direct question raised in session: how much of the review
        # backlog is a duplicate of a known extractor problem rather than
        # distinct human review volume? See
        # memory/project-dcp-review-queue-is-a-bug-report-2026-08.md for the
        # root cause of both tags.
        #
        # ⚠ TWO ROUNDS OF SOL CROSS-REVIEW BOTH CAUGHT THE SAME OVERCLAIM, so it
        # is written out in full rather than patched again: a suspect_reason of
        # count_drop or preflight_two_column is a SIGNATURE the extractor
        # writes about itself, not an independently confirmed defect. The fix
        # proven to actually correct count_drop covers 1 of the 28 chapters
        # that carry that tag (marrickville/part2-s11-fencing, 2026-08-14) --
        # the other 27, and all 85 preflight_two_column chapters, are UNCHECKED
        # per-chapter. A council whose DCP genuinely deleted provisions in a
        # real amendment would earn the identical count_drop tag and this probe
        # cannot tell the two apart. So: this count is a TRIAGE PRIORITISATION
        # signal (which chapters to open first), not a completed classification
        # of "bug, skip" vs "real change, review". Do not exclude these rows
        # from review planning on this tag alone, and do not call the untagged
        # remainder "safe" -- it is only "rows without these two tags"; DQ-71
        # (source-quote verification) still applies to all of it.
        #
        # Measured live 2026-09-04: 9,461 pending total; 5,479 tagged
        # count_drop (28 chapters) + 3,642 tagged preflight_two_column (85
        # chapters) = 9,121 (96.4%) carry one of the two tags; 340 do not.
        "SELECT count(*) FROM dcp_review_queue "
        "WHERE status = 'pending' "
        "AND (suspect_reason LIKE 'count_drop%%' "
        "     OR suspect_reason LIKE 'preflight_two_column%%')",
        (),
        "Each row carries a suspect_reason tag matching one of two extractor "
        "bug SIGNATURES -- a hypothesis about the row, not a confirmed defect. "
        "The count_drop root cause is proven fixed for only 1 of the 28 tagged "
        "chapters; a chapter with a genuine, legitimate DCP amendment that "
        "removed provisions would earn the identical tag. Use this as a triage "
        "signal for which chapters to open and check first -- do NOT treat the "
        "9,121 as confirmed-safe-to-skip, and do NOT treat the remaining 340 as "
        "a confirmed-clean review set; both need chapter-level or DQ-71 "
        "verification before either claim can be made.",
    ),
    "DQ-93": (
        "inner-west/marrickville NULL v2_topic rate vs its own 10% threshold",
        # Found live 2026-09-04 while wiring tests/test_drawdown_verify_real_db.py
        # into CI (DQ-91/DQ-92): tests/test_lga_coverage.py already has a
        # parametrised check for exactly this (test_no_null_v2_topic,
        # per-council thresholds in ONBOARDED_LGAS), but that file carries
        # pytest.mark.database, is deselected by pytest.ini's default addopts,
        # and nothing in this repo had ever invoked it with PYTEST_REAL_DB=1 --
        # the identical root cause as DQ-91/DQ-92, on a different file. Query
        # copied from that test's own body, not re-derived, so this probe and
        # that test can never quietly disagree about what "over threshold"
        # means. Deliberately does NOT point dq_checks.json at a raw
        # `pytest -m database ...` invocation: without PYTEST_REAL_DB=1 set,
        # that command SKIPS (pytest exit 0), which dq_check.py reads as
        # PASSED -- the exact false-reassurance shape this ledger exists to
        # prevent. Routing through dq_probe_live.py instead means an
        # unreachable database exits 2 (UNKNOWN), never a silent pass, via
        # dq_db.py's own connect().
        # Sol cross-review (2026-09-04, on push): the original NULLIF(COUNT(*),0)
        # form returns NULL, not 1, when zero rows match -- CASE WHEN NULL THEN
        # 1 ELSE 0 END evaluates to 0, so a council whose provisions were all
        # deleted/deactivated would report CLEAN (0) instead of the actual
        # problem (no data at all). Zero-row is checked explicitly FIRST.
        "SELECT CASE "
        "  WHEN COUNT(*) = 0 THEN 1 "
        "  WHEN COUNT(*) FILTER (WHERE v2_topic IS NULL)::float / COUNT(*) > 0.10 THEN 1 "
        "  ELSE 0 END "
        "FROM regulatory_provisions "
        "WHERE source_council = 'marrickville' AND is_current = TRUE",
        (),
        "inner-west/marrickville's live NULL v2_topic rate exceeds the 10% "
        "threshold tests/test_lga_coverage.py's own ONBOARDED_LGAS config "
        "sets for it -- measured 2026-09-04 at 14.8% (583 of 3,934). Not "
        "investigated further here: why this council drifted specifically, "
        "or whether other ONBOARDED_LGAS entries are also currently red -- "
        "only this one was observed this session. Fix = re-run topic "
        "classification for this council (the underlying test's own error "
        "message), not attempted here.",
    ),
    "DQ-97": (
        "SERVED provisions carrying the margin-artifact SYMPTOM "
        "(coarse SQL proxy for the Python has_margin_artifact scan)",
        # See ~/.claude/plans/ce-margin-artifact-census-2026-09-06.md for the
        # full per-chapter census this count summarises.
        #
        # THIS COUNT CANNOT REACH 0 BY DESIGN, and that is stated up front
        # rather than discovered later (feedback-a-check-can-watch-the-field-
        # the-fix-abandoned): a run of 6+ short whitespace-separated tokens
        # also matches genuine content -- numeric tables (a flood-risk X/N
        # compatibility matrix, an Rw noise-insulation schedule), contour/
        # site-plan RL labels, and ordinary Title Case prose with short
        # link-words (Of/In/To/Or). Confirmed live 2026-09-06 on marrickville
        # (all 6 of its residual post-DQ-92 rows), blacktown, ku_ring_gai's
        # 14k/14m/14o site-plan chapters, and 3 of city_of_sydney's 5 rows.
        #
        # Of the rest, per-chapter real-geometry inspection (pdfplumber
        # extract_words on the actual flagged pages, not just the symptom
        # regex) found this is NOT one bug: woollahra (~410 of 424 flagged
        # rows, 21 of 22 chapters) carries a "Repealed by [instrument]
        # Amendment No. X on [date]" stamp whose characters extract in
        # reversed x-order (upright glyphs, decreasing position) -- a THIRD
        # mechanism distinct from both marrickville's stacked-vertical-glyph
        # margin label (PR #1050) and canterbury_bankstown's original
        # extract_words word-splitting. canterbury_bankstown/chapter-7-6-
        # belmore-and-lakemba separately carries a locality-map label
        # interleave (~18 rows: street/station names from a rotated map
        # graphic merging character-by-character) -- 3 of that chapter's
        # rows (pages 126/128/130) already match find_vertical_margin_label_
        # band on the CURRENT code, meaning they are stale pending rows that
        # a bare re-extraction would clear, not a live gap. No fix has been
        # decided or built for any of this yet -- this entry records the
        # census result only.
        #
        # SQL approximates the Python token scan (word-boundary-anchored,
        # not true whole-token length) and over-counts by ~10% against it
        # (574 vs. the Python census's 519 on 2026-09-06) -- a triage upper
        # bound, not the per-row-verified count.
        # POPULATION CHANGED 2026-09-10, from pending queue rows to SERVED
        # provisions. The old query counted dcp_review_queue WHERE status =
        # 'pending'. On 2026-09-09 the review backlog was cleared -- 8,875 rows
        # approved in one night -- and this count fell from 574 to 0, so the
        # ratchet read "declared open but the check PASSES: it appears to be
        # fixed". Nothing was fixed. The rows were approved out of the queue and
        # 578 of them were committed into the served set, which is where the
        # symptom now sits: the check was watching a population an operator can
        # drain without repairing anything, and it went green by the defect
        # moving downstream. Exactly feedback-a-check-can-watch-the-field-the-
        # fix-abandoned, and feedback-audit-rows-are-not-live-claims: a queue is
        # a workflow state, exposure is what a reader can actually see.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable "
        r"AND provision_text ~ '([[:space:]][^[:space:]]{1,2}){6,}'",
        (),
        "A SERVED provision matches the coarse short-token-run symptom. Per the "
        "2026-09-06 census this is mostly ONE real, unfixed cause (woollahra's "
        "reversed-order repeal stamp) plus a smaller distinct cause "
        "(canterbury_bankstown's map-label interleave) plus a substantial "
        "false-positive rate from legitimate tables/diagrams/prose -- do NOT "
        "read this count as 'N rows of corruption'. See the census doc for "
        "the per-chapter breakdown before triaging or fixing anything from "
        "this number alone.",
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
