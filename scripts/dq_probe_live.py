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
        #
        # nsw_statewide is not a council plan, for the reason
        # check_dcp_as_at_coverage.py already records: its numbers come from the
        # Codes SEPP and the Apartment Design Guide, so "which version of the
        # council's plan do we hold" is a question it cannot answer and counting
        # it kept this row at 1 forever. The SEPPs' currency is DQ-88's
        # (instrument_registry and the legislation monitor).
        "SELECT count(DISTINCT d.lga) FROM dcp_setback_controls d "
        "LEFT JOIN dcp_plan_as_at a ON a.lga = d.lga "
        "WHERE d.is_current AND NOT COALESCE(d.needs_review, false) "
        "  AND d.lga <> 'nsw_statewide' "
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
        "                                    AND c.sibling_chapter_key = s.chapter_key "
        "                                    AND btrim(c.sibling_section_ref) <> ''))",
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
    "DQ-117": (
        "The DCP source sweep has not run fleet-wide in 10 days",
        # LIVENESS, not data quality -- DQ-69's missing sibling for the OTHER
        # monitor. r2_monitor writes url_last_checked on all four of its paths
        # (900, 1106, 1126, 1143), so only a real sweep moves it; a code edit
        # cannot satisfy this.
        #
        # ⚠ 17 DAYS, NOT 10, AND THE 10 WAS WRONG. This shipped believing the
        # cron was "weekly Mon 02:00 UTC", which the opening prompt asserted.
        # railway.dcp-monitor.toml in this repo says otherwise:
        #
        #     cronSchedule = "0 2 1,15 * *"   # fortnightly: 1st and 15th, 02:00 UTC
        #
        # The gap between the 15th and the 1st is 14-17 days depending on the
        # month, so a 10-day window goes RED ON A HEALTHY SCHEDULE, every single
        # cycle. A check that is always red is exactly as useless as one that is
        # always green, and it is worse than useless here because this ledger's
        # whole purpose is that a red row means something.
        #
        # 17 days = the longest healthy gap (15 Jan -> 1 Feb is 17 days) with no
        # slack beyond it. A run missed entirely therefore shows up within about
        # a fortnight, which for a corpus that amends ~5 times a year across 28
        # councils is proportionate.
        #
        # ⚠ The toml is the DECLARED schedule, not proof of the live one:
        # scripts/check_railway_cron_drift.py exists because on 2026-09-10 six of
        # eight services ran a different schedule from their file and four had no
        # cron at all. If that check ever reports dcp-monitor drifting, this
        # window is wrong again.
        #
        # WHY: measured 2026-09-27, the sweep had been dead for 12 days --
        # 499 of 514 monitorable chapters last checked 2026-09-15, one missed
        # Monday, zero heartbeats, zero alerts. DQ-70 stayed GREEN the whole
        # time, because content_hash has exactly one writer -- this sweep -- so
        # both sides of its comparison froze together. url_last_checked appeared
        # in ZERO of the 136 ledger rows.
        #
        # ⚠ THE FIRST DRAFT OF THIS PROBE WAS DEFEATED BEFORE IT WAS INSTALLED,
        # and the correction is the whole point of the row. It read
        # `max(url_last_checked)` fleet-wide. That returns 0 today: six
        # wollongong chapters were checked for the FIRST time on 2026-09-24
        # during onboarding, which moved the fleet maximum to four days ago
        # while 499 chapters sat 13 days stale. A fleet-wide max() goes green as
        # soon as ANY single council is touched -- a check that cannot go red
        # while the defect stands, which is the silent-pass shape this ledger
        # exists to remove, and the same shape as the DQ-69 premise its own gate
        # caught in 2026-08. Both measured on production 2026-09-28: max() = 0,
        # median = 1 at 12 days 20 h behind.
        #
        # THE MEDIAN, therefore. A sweep touches every monitorable chapter, so a
        # real run moves it; onboarding a handful cannot. A HALF-completed sweep
        # leaves it old, which is correct -- a half sweep is a broken sweep.
        #
        # Deliberately BINARY on the fleet, not a per-row count. A per-row count
        # sits at a permanent floor (liverpool 146d, waverley 90d are real but
        # SEPARATE defects -- DQ-118), and a floor is precisely what made the
        # 12-day gap unreadable.
        #
        # Two silent-pass holes closed in the SQL itself:
        #  - NULL url_last_checked is coalesced to -infinity rather than dropped,
        #    so a never-checked chapter counts as maximally stale instead of
        #    vanishing from the population being measured.
        #  - The whole expression is coalesced, so an EMPTY registry reads 1.
        #    percentile_disc over zero rows returns NULL, and a NULL count is
        #    falsy in run(), i.e. it would have printed CLEAN.
        #
        # SCOPE, stated because it is narrower than the sweep: is_inert chapters
        # are excluded, and r2_monitor does sweep them (24 rows, median also
        # 2026-09-15). This measures the chapters whose freshness anyone depends
        # on; including them changes today's verdict either way not at all.
        #
        # ⚠ NOT A DISCOVERY CHECK. Whether a council PUBLISHED something new is
        # a different question that hashing known URLs structurally cannot
        # answer -- Randwick DCP 2025 commenced 27 July 2026 and was found by
        # hand seven weeks later because the council left the old file
        # byte-identical. That is DQ-118's question, not this one's.
        "SELECT CASE WHEN COALESCE(percentile_disc(0.5) WITHIN GROUP ("
        "                 ORDER BY COALESCE(url_last_checked, '-infinity'::timestamptz)), "
        "               '-infinity'::timestamptz) < NOW() - INTERVAL '17 days' "
        "            THEN 1 ELSE 0 END "
        "FROM dcp_chapter_registry "
        "WHERE is_active AND NOT COALESCE(is_inert, false) "
        "  AND council_url IS NOT NULL AND btrim(council_url) <> ''",
        (),
        "1 means no sweep completed in 10 days, so every 'unchanged since "
        "extraction' verdict in this ledger -- DQ-70 above all -- describes the "
        "last sweep date, not today. Silence from VerifyOpsBot is NOT evidence "
        "of no change while this reads 1. Reads 0 only after a real sweep, which "
        "no code change can produce.",
    ),
    "DQ-119": (
        "Served chapters whose own contents page says the reader missed sections",
        # THE AGGREGATION, not a new detector. ai_extractor.coverage_gap() has
        # scored every extraction for months and dcp_extract_changed stamps the
        # verdict onto the queue row as a suspect_reason. Nothing ever counted
        # them, so a chapter could record "15/15 TOC sections missing" and keep
        # serving an older extraction with nobody told. Measured 2026-10-03: 7
        # served chapters, of which ashfield chapter-a-miscellaneous (15/15),
        # chapter-c-sustainability (21/21) and chapter-f-dev-category (11/11)
        # found NONE of the sections their own contents page lists.
        #
        # NOT DQ-118. That number is reserved for per-council hub-scrape
        # liveness -- whether a council PUBLISHED something new -- which DQ-117
        # names and this row does not touch.
        #
        # LATEST VERDICT PER CHAPTER, deliberately. A re-extract supersedes its
        # predecessor's rows, so counting every queue row would keep reporting a
        # fault a later read already cleared: woollahra
        # chapter-b3-general-development is exactly that, coverage_fail on a
        # superseded batch and clean since. DISTINCT ON ... created_at DESC
        # takes the newest batch only.
        #
        # SERVED, not merely queued. A coverage_fail in a queue nobody approved
        # harms no reader. This counts chapters live in regulatory_provisions --
        # the same correction DQ-97 needed on 2026-09-10, when its population
        # turned out to be one an operator could DRAIN without repairing
        # anything.
        #
        # coverage_unknown COUNTS HERE. "We could not read the contents page" is
        # the third state, not a pass; omitting it would make this check green on
        # exactly the documents nobody can verify. northern_beaches
        # warringah-dcp-2011-full and canterbury_bankstown
        # chapter-11-2-undercliffe-bridge-precinct are both in that state.
        "SELECT count(*) FROM ("
        "SELECT DISTINCT ON (q.council, q.chapter_key) q.suspect_reason AS sr "
        "FROM dcp_review_queue q "
        "JOIN dcp_chapter_registry r ON r.council = q.council "
        "AND r.chapter_key = q.chapter_key AND r.is_active "
        "AND NOT COALESCE(r.is_inert, false) "
        "WHERE EXISTS (SELECT 1 FROM regulatory_provisions p "
        "WHERE p.source_council = q.council AND p.source_chapter_key = q.chapter_key "
        "AND p.is_current AND p.v2_is_actionable) "
        "ORDER BY q.council, q.chapter_key, q.created_at DESC) t "
        "WHERE t.sr LIKE %s OR t.sr LIKE %s",
        ("%coverage_fail%", "%coverage_unknown%"),
        "Each count is one chapter that is SERVED to readers while its most "
        "recent extraction recorded that the reader did not find the sections "
        "the chapter's own table of contents lists -- or could not read that "
        "contents page at all. The finding already existed on every one of "
        "these rows; nothing aggregated it, so no one was ever told. Clears by "
        "re-reading the chapter until coverage_gap() is satisfied, or by "
        "recording why the contents page cannot be parsed. It does NOT clear by "
        "approving the queue: the count reads the latest verdict per chapter "
        "regardless of status.",
    ),
    "DQ-120": (
        "City of Sydney areas the DCP excludes, for which we hold no plan and no exclusion",
        # Sydney DCP 2012 Section 1 clause 1.4, page 4, read 2026-10-03: the plan
        # applies to "the land identified in Figure 1.1 ... where the City of
        # Sydney is the consent authority". Figure 1.1 on page 5 EXCLUDES eight
        # areas, each keeping its own plan: Barangaroo, Bays Precinct/Wentworth
        # Park, Harold Park, Redfern/Waterloo, Various Sites (South Sydney),
        # Green Square Town Centre, Moore Park Showground and Glebe (Affordable
        # Housing).
        #
        # We serve City of Sydney rules by COUNCIL. Green Square is inside the
        # City of Sydney, so a Green Square property is shown Sydney DCP 2012
        # controls that do not bind it, and the plan that does bind it is absent.
        #
        # WHY THIS IS A ROW AND NOT A FIX. The exclusion is a MAPPED BOUNDARY.
        # No column in this schema carries it: v2_applicable_zones is a zone
        # list, v2_precinct_id holds locality-statement clause numbers like
        # "2.1.1" rather than place extents, and inventing the boundaries would
        # break the standing rule against guessing real-world geography. So the
        # honest state is measured and visible rather than approximated.
        #
        # WHAT IT COUNTS, and why that is checkable when the boundary is not:
        # how many of the eight have NEITHER their own plan in the registry NOR
        # any served provision attributable to them. Measured 2026-10-03 it is
        # 8 of 8 -- zero documents match any of the names. It falls as each area
        # gains its own plan, and it cannot be cleared by editing City of
        # Sydney's config, which is the point.
        "SELECT count(*) FROM unnest(%s::text[]) AS area(name) "
        "WHERE NOT EXISTS (SELECT 1 FROM documents d "
        "                   WHERE lower(d.pdf_name) LIKE '%%' || area.name || '%%') "
        "  AND NOT EXISTS (SELECT 1 FROM dcp_chapter_registry r "
        "                   WHERE r.is_active "
        "                     AND (lower(r.chapter_key) LIKE '%%' || replace(area.name,' ','-') || '%%' "
        "                          OR lower(coalesce(r.chapter_label,'')) LIKE '%%' || area.name || '%%'))",
        (["barangaroo", "wentworth park", "harold park", "redfern",
          "green square", "moore park showground", "glebe", "south sydney"],),
        "Each count is one area that Sydney DCP 2012 says it does NOT cover, for which we hold "
        "no replacement plan and no way to withhold the City of Sydney controls that do not "
        "bind it. A property there is shown the wrong plan's rules and is not shown its own. "
        "Clears by ingesting that area's plan, or by acquiring the Figure 1.1 boundary so the "
        "exclusion can be applied. It does NOT clear by editing city_of_sydney_config.py -- the "
        "config has no key that can express a mapped boundary.",
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
        # Council rows only, and the reason is in the repair this ratchet watches:
        # retag_applicability_slug_docids.py selects "WHERE source_council = ANY(%s)",
        # so it only ever touched rows WITH a council and the 1,278 it deliberately
        # left is entirely inside that population. Subtracting it from the whole table
        # was therefore comparing a council-scoped floor against a count that also
        # held 4,887 statewide LEP and SEPP rows (measured 2026-09-19, against 1,986
        # council rows). A statewide instrument has no council whose config could
        # resolve it, so for those rows 'no_config' is the permanent honest answer
        # rather than a defect, and the check could never fall below 4,887 however
        # much was repaired -- a ratchet that cannot reach zero measures nothing.
        # Scoped, it reports 708 and can still move, which is the test that this is a
        # correction and not a way to go green: a narrowing that produced 0 would be
        # deleting the check rather than fixing it.
        # FLOOR LOWERED 1278 -> 1158 on 2026-09-21, after leichhardt's nine
        # unconfigured documents were declared (871 rows resolved). A ratchet floor
        # may only FALL: leaving it at 1,278 would have let 120 rows of new
        # breakage arrive while this still reported 0. 1,158 is the exact count
        # measured immediately after that repair, not a rounded allowance.
        #
        # What the floor still hides, and should not be mistaken for clean:
        # parramatta 341, canterbury_bankstown 216, marrickville 157, ashfield 118
        # and five smaller councils. Each needs its unconfigured documents declared
        # the way leichhardt's were. Lower this again each time one is done.
        "SELECT GREATEST(count(*) - 1158, 0) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable "
        "AND source_council IS NOT NULL "
        "AND v2_dev_type_source = 'no_config'",
        (),
        "no_config on served COUNCIL rows has risen above the 1,278 left "
        "deliberately by the 2026-08-01 retag, so document_ids are failing to "
        "resolve against council config again and those rows silently apply to "
        "ALL development types. Scoped to rows that HAVE a council because the "
        "retag only touched those: 4,887 served statewide LEP/SEPP rows also "
        "read no_config and always will, having no council config to resolve "
        "against, and counting them made this ratchet unable to reach zero. "
        "SEPARATE AND LARGER: 10,103 served rows carry a NULL v2_dev_type_source "
        "and were never tagged at all, so the question cannot be asked of them; "
        "that gap is not counted here and needs its own row.",
    ),
    "DQ-114": (
        "Served scope keys left ALL by a NON-decision (the schema's own undetermined list, less no_config)",
        # THE ROW DQ-33 ASKED FOR. DQ-33's own note ends "SEPARATE AND LARGER:
        # ... that gap is not counted here and needs its own row." This is it,
        # widened: DQ-33 and DQ-105 both own `no_config`, and between them they
        # leave every OTHER way a key ends up ALL without anybody deciding it
        # uncounted. Together the rows partition the non-decisions.
        #
        # THE LIST IS THE SCHEMA'S OWN, NOT THIS PROBE'S OPINION. Migration 062
        # documents the vocabulary on the column itself: "Trustworthy assertions:
        # config_specific, config_all, text_regex. Undetermined: config_silent,
        # no_config, no_document_id, filtered_to_all." plus "NULL = tagged before
        # provenance existed (origin unknown, NOT a pass)". So:
        #
        #   no_config        no entry matched at all      -> DQ-33 (rows), DQ-105 (councils)
        #   config_silent    an entry matched, key omitted -> HERE
        #   filtered_to_all  the text named zones this council does not have,
        #                    so the tagger fell back to ALL             -> HERE
        #   no_document_id   nothing to match an entry against          -> HERE
        #   NULL             never tagged                               -> HERE
        #
        # `filtered_to_all` was missed on the first write of this row and added
        # before it was ever committed. It is 43 served zone keys, counted by
        # NOTHING else - DQ-33 reads `no_config` only - so the check could have
        # gone green with them still undetermined. That is
        # feedback-a-check-can-watch-the-field-the-fix-abandoned, and the guard
        # against it is taking the list from the migration's COMMENT rather than
        # from whoever writes the query.
        #
        # `config_silent` is the one that reads as finished. An entry exists, the
        # council is "configured", the council's words sit in the config file as
        # a comment -- and the key nobody decided resolves to ALL, so the rule is
        # served to every development type on the strength of an omission.
        # ApplicabilityTagger._resolve is where the meaning is fixed: silent
        # means "an entry matched and nobody decided this key".
        #
        # COUNTED PER KEY, not per row, and that is deliberate. The suppression
        # in tag_with_provenance is per-ENTRY, so an entry that names dev types
        # and omits zones is silent on zones alone; counting rows would let a
        # column go fully undecided without the number moving, which is
        # feedback-a-check-can-watch-the-field-the-fix-abandoned.
        #
        # IT CAN REACH ZERO, which is what makes it worth enforcing rather than
        # ratcheting. A chapter that states no scope of its OWN is not stuck
        # silent: it inherits the plan's own stated scope, which is itself a
        # quotable decision (Wollongong A1 s5, verbatim, "This plan applies to
        # all lands within the Wollongong LGA"), recorded as config_all with
        # that sentence as its evidence. Silent is never the honest answer --
        # only "not read yet".
        #
        # NOT the same population as DQ-103, and the difference is who can fix
        # it. DQ-103 is the SUBSET whose own text carries discarded evidence, so
        # code can resolve it by stopping the discard. What is left here needs a
        # person to read the chapter. Measured 2026-09-27: 4,374 key-decisions
        # (dev types 2,859 silent + 36 untagged; zones 1,400 silent + 43
        # filtered_to_all + 36 untagged), of which DQ-103 accounts for 1,021.
        # Council rows only, for DQ-33's reason: a statewide SEPP or LEP has no
        # council config that could ever resolve it.
        #
        # LEP rows are excluded BY DOCUMENT TYPE, not by source_council, and that
        # was learned the hard way: migration 087 (2026-10-09) correctly gave the
        # Inner West LEP 2022 rows their council, which silently pulled 120 LEP
        # keys into this DCP count and turned it red. "Council rows" here always
        # meant council DCP rows. The LEP's undecided scope is DQ-140's.
        "SELECT count(*) FROM ("
        "  SELECT 1 FROM regulatory_provisions rp"
        "   WHERE rp.is_current AND rp.v2_is_actionable AND rp.source_council IS NOT NULL"
        "     AND NOT EXISTS (SELECT 1 FROM documents d"
        "                      WHERE d.id = rp.document_id AND d.document_type = 'LEP')"
        "     AND (rp.v2_dev_type_source IN ('config_silent','filtered_to_all',"
        "                                    'no_document_id')"
        "          OR rp.v2_dev_type_source IS NULL)"
        "  UNION ALL"
        "  SELECT 1 FROM regulatory_provisions rp"
        "   WHERE rp.is_current AND rp.v2_is_actionable AND rp.source_council IS NOT NULL"
        "     AND NOT EXISTS (SELECT 1 FROM documents d"
        "                      WHERE d.id = rp.document_id AND d.document_type = 'LEP')"
        "     AND (rp.v2_zone_source IN ('config_silent','filtered_to_all',"
        "                                'no_document_id')"
        "          OR rp.v2_zone_source IS NULL)"
        ") t",
        (),
        "Each count is one key -- a development-type list or a zone list -- on "
        "one served rule, left reading ALL because nobody decided it. The rule "
        "is served to properties and projects its own chapter may not reach, on "
        "the authority of an omission. Reachable only by reading each chapter's "
        "own scope section and recording what it says, including the case where "
        "the chapter states nothing and inherits the plan's stated scope. "
        "Deleting a council's rows, or typing ALL to clear the count, would "
        "also take this to zero -- DQ-115 is the half that refuses that, by "
        "requiring every declared key to carry the council's own words.",
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
        "     AND COALESCE(h.verified_at, h.created_at) < ir.last_changed "
        "     AND h.source_document ILIKE %s) "
        "  + "
        "  (SELECT count(*) FROM housing_sepp_standards h "
        "   JOIN instrument_registry ir ON ir.instrument_key = 'sepp_exempt_complying_2008' "
        "   WHERE ir.needs_review AND h.stale_since IS NULL "
        "     AND COALESCE(h.verified_at, h.created_at) < ir.last_changed "
        "     AND (h.source_document ILIKE %s OR h.source_document ILIKE %s)) "
        "  + "
        "  (SELECT count(*) FROM cdc_eligibility_standards c "
        "   JOIN instrument_registry ir ON ir.instrument_key = 'sepp_exempt_complying_2008' "
        "   WHERE ir.needs_review AND c.stale_since IS NULL "
        "     AND COALESCE(c.verified_at, c.created_at) < ir.last_changed)",
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
    "DQ-100": (
        "SERVED provisions from a council DCP that carry NO source_council, so every "
        "council-scoped check skips them",
        # A DCP is always a council's document. A served row whose document_id names
        # one and whose source_council is NULL is mislabelled, not statewide -- and
        # the label is what every council-scoped query filters on.
        #
        # Measured 2026-09-21: 1,336 such rows, ALL of them Inner West Ashfield DCP
        # 2016 chapters (E1 Heritage 887, C Sustainability 181, A Miscellaneous 140,
        # F Development Categories 71, D Precinct Guidelines 48, B Public Domain 9),
        # while 2,041 rows of the SAME document family correctly carry 'ashfield'.
        # One document set, split two ways.
        #
        # WHY IT MATTERS MORE THAN ITS SIZE. These rows are invisible to anything
        # scoped by council: the DQ-70 staleness join, the plan-in-force confirmation,
        # per-council coverage counts, and DQ-33 -- which was narrowed to
        # `source_council IS NOT NULL` on 2026-09-19 for the sound reason that a
        # statewide instrument has no council config to resolve against. That
        # narrowing is right for real statewide rows and wrong for these, so the
        # ratchet beside this one is quietly excluding 1,336 rows of council data.
        #
        # NOT counted here: 554 served LEP rows also carry no council. Whether an LEP
        # belongs to its council or is statewide is a real question with a defensible
        # answer either way -- instrument_registry files LEPs per council, which
        # suggests it does -- and mixing it in would make this number unarguable
        # rather than exact. It needs its own row and its own decision.
        "SELECT count(*) FROM regulatory_provisions "
        "WHERE is_current AND v2_is_actionable AND source_council IS NULL "
        # %% not % -- psycopg2 reads a lone % as a parameter placeholder even when
        # the parameter tuple is empty, and raises IndexError before the query runs.
        "AND (document_id ILIKE '%%DCP%%' "
        "     OR document_id ILIKE '%%Development Control Plan%%' "
        "     OR document_id ILIKE '%%Development_Control_Plan%%')",
        (),
        "Each row is a control we serve that came from a named council's DCP but "
        "carries no council, so every council-scoped check passes over it: staleness "
        "(DQ-70), the plan-in-force confirmation, coverage counts, and the no_config "
        "ratchet (DQ-33), which was deliberately narrowed to rows that HAVE a council. "
        "Clears by setting source_council on the affected rows, which is a data repair "
        "and not a code change -- and the repair must decide what Inner West's "
        "pre-amalgamation Ashfield chapters should say, since 2,041 sibling rows "
        "already say 'ashfield'.",
    ),
    "DQ-130": (
        "SEPPs/LEPs whose text we serve that the legislation monitor does not watch",
        # DQ-69 asks "does the monitor run over what is registered?" -- it cannot
        # see an instrument nobody registered. The Industry and Employment SEPP's
        # 2026 amendment went unflagged for exactly that reason (found by hand
        # 2026-09-15), and the Sustainable Buildings SEPP's 31 Oct 2025 amendment
        # likewise (found by hand 2026-10-05). This counts from the SERVED side.
        #
        # There is no documents -> instrument_registry key yet (Step 2 of
        # ce-lep-sepp-currency-integration-PROMPT-2026-10-05 adds one), so the
        # join is on the instrument's title. Controls run 2026-10-05: the 6
        # counted are exactly the 6 SEPPs with no registry row, and the 4
        # registered instruments that serve text (Housing, Codes, Industry and
        # Employment SEPPs; Inner West LEP) are all excluded -- a title mismatch
        # would have counted one of them.
        "WITH served AS ("
        "  SELECT DISTINCT split_part(d.pdf_name, ' - NSW Legislation', 1) AS instrument"
        "  FROM documents d JOIN regulatory_provisions p ON p.document_id = d.id"
        "  WHERE d.document_type IN ('SEPP', 'LEP') AND p.is_current AND p.v2_is_actionable"
        ") SELECT count(*) FROM served s WHERE NOT EXISTS ("
        "  SELECT 1 FROM instrument_registry r WHERE r.is_active"
        "  AND r.pco_instrument_id IS NOT NULL AND lower(r.instrument_label) = lower(s.instrument))",
        (),
        "Each is a SEPP or LEP served to users whose amendments nothing detects. "
        "Measured 6 on 2026-10-05: Transport and Infrastructure, Biodiversity and "
        "Conservation, Planning Systems, Primary Production, Resilience and Hazards, "
        "Sustainable Buildings -- 1,842 served rows between them. Clears by registering "
        "each with the EPI id read from its own legislation page, not by un-serving it.",
    ),
    "DQ-131": (
        "Active registered instruments with a missing or shared EPI id",
        # The monitor matches PCO's amendment export by pco_instrument_id. A NULL
        # id can never match, so the instrument is never checked (DQ-69's known
        # floor of 1). A SHARED id is worse: both rows are reported current off
        # one instrument's history, so the wrong one's amendments are never seen
        # and nothing errors. Counts ROWS, so a shared pair counts 2 until the
        # wrong one is corrected.
        "SELECT count(*) FROM instrument_registry r WHERE r.is_active AND ("
        "  r.pco_instrument_id IS NULL OR EXISTS ("
        "    SELECT 1 FROM instrument_registry o WHERE o.is_active AND o.id <> r.id"
        "    AND o.pco_instrument_id = r.pco_instrument_id))",
        (),
        "Measured 3 on 2026-10-05: wingecarribee_lep_2010 has no id, and "
        "camden_lep_2010 and penrith_lep_2010 both carry epi-2010-0540, so Camden "
        "LEP is checked against Penrith's history. Clears by taking each id from "
        "the instrument's own legislation page -- never from memory or a handoff.",
    ),
    "DQ-132": (
        "Served SEPPs/LEPs whose stored text cannot be shown to match the version in force",
        # Counts an instrument when ANY served document of it: has no registry
        # row; records no version date (documents.consolidated_as_of_date); or
        # records one older than the version the monitor last saw while the
        # instrument is NOT flagged needs_review (flagged = already visibly
        # caveated by the fail-closed badge, so not silent).
        #
        # Reads 10 of 10 on 2026-10-05 because no served document records its
        # version at all -- which is the defect: the Housing SEPP's text was
        # refreshed on 2026-09-15 and its documents row still names Dec 2025, and
        # the Sustainable Buildings text is the 5 Apr 2024 version of a SEPP
        # amended 31 Oct 2025, and no check could tell either. version_date is
        # TEXT in instrument_registry; the regex guard keeps a malformed value
        # from erroring the probe (it then cannot excuse the row).
        "WITH served AS ("
        "  SELECT DISTINCT split_part(d.pdf_name, ' - NSW Legislation', 1) AS instrument,"
        "         d.id AS doc_id, d.consolidated_as_of_date"
        "  FROM documents d JOIN regulatory_provisions p ON p.document_id = d.id"
        "  WHERE d.document_type IN ('SEPP', 'LEP') AND p.is_current AND p.v2_is_actionable"
        ") SELECT count(DISTINCT s.instrument) FROM served s"
        "  LEFT JOIN instrument_registry r"
        "    ON r.is_active AND lower(r.instrument_label) = lower(s.instrument)"
        "  WHERE r.id IS NULL OR s.consolidated_as_of_date IS NULL"
        "     OR (s.consolidated_as_of_date < (CASE WHEN r.version_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'"
        "                                     THEN r.version_date::date END)"
        "         AND NOT r.needs_review)",
        (),
        "Each is a SEPP or LEP served as current law whose stored text is either "
        "older than the version in force or cannot say which version it is. "
        "Clears per instrument by recording the version the text was taken from "
        "and refreshing text that is behind (DQ-88 method), not by stamping today's date.",
    ),
    "DQ-133": (
        "Columns the SEPP parking tier selects that housing_sepp_standards does not have",
        # /api/tod/parking-rates runs three tiers: SEPP standards (which override a
        # council rate), then the council's numeric DCP controls, then DCP provision
        # text. Tier 1 selects `dwelling_type`, `notes` and `is_current`. The table has
        # `development_type`, `verification_notes` and no currency boolean at all (use
        # `stale_since IS NULL`). So tier 1 raises on EVERY call, runTier records a
        # degradation, and the answer always comes from the council DCP -- including
        # where a state standard would override it. Nothing errors visibly: the route
        # was built to degrade rather than fail, so a tier that never runs reads exactly
        # like a tier that found nothing.
        #
        # Counts the missing columns, so a partial rename cannot clear it.
        "SELECT count(*) FROM (VALUES ('dwelling_type'), ('notes'), ('is_current')) AS c(col)"
        " WHERE NOT EXISTS ("
        "   SELECT 1 FROM information_schema.columns"
        "   WHERE table_schema = 'public' AND table_name = 'housing_sepp_standards'"
        "     AND column_name = c.col)",
        (),
        "Each is a column the SEPP-override tier of /api/tod/parking-rates asks for and "
        "cannot get, so the tier throws and a council rate is served where a state "
        "standard would override it. Reads 3 on 2026-10-05. Reaching 0 is necessary and "
        "NOT sufficient: SEPP_DWELLING_TYPE_MAP also maps to values the table does not "
        "use (residential_flat_building/rfb vs residential_flat_r1r2 / r3r4_inner / "
        "r3r4_outer; multi_dwelling_housing/mdh vs multi_dwelling; boarding_house is "
        "absent), so after a rename only dual_occupancy resolves. Choosing between the "
        "three residential_flat bands needs the zone and whether the land is in an "
        "accessible or designated area -- a regulatory decision, not a rename. Do not "
        "close this row on the rename alone.",
    ),
    "DQ-134": (
        "SQL columns in scanned code that the schema-contract gate cannot check",
        # validate_schema_contract.py exists because a renamed table left
        # dcp-complete/route.ts raising a 500 on every address while 3,207 Python tests,
        # ~900 Jest tests, TSC, four lints and the QA gate all stayed green. Its column
        # rule only covers ALIAS-QUALIFIED columns ("alias.column", alias bound to a real
        # base table in the same statement). A single-table query written without an
        # alias -- the ordinary way to write one -- has no qualified columns, so its
        # column list is never checked and only the table name is. That is how DQ-133
        # survived: the gate ran on frontend-nextjs/app/api, read
        # tod/parking-rates/route.ts, resolved housing_sepp_standards, and checked none
        # of the seven bare columns it selects.
        #
        # Measured from the catalog rather than by re-parsing the code, using the one
        # case already proven. Deliberately a FLOOR, not a census: a row that goes green
        # only once the gate itself checks unqualified columns.
        "SELECT CASE WHEN EXISTS ("
        "   SELECT 1 FROM information_schema.columns"
        "   WHERE table_schema = 'public' AND table_name = 'housing_sepp_standards'"
        "     AND column_name = 'dwelling_type') THEN 0 ELSE 1 END",
        (),
        "1 means the gate that exists to catch 'code queries a column that is not "
        "there' still cannot see an unaliased single-table query, and the known instance "
        "(DQ-133) is still live. Clears by extending validate_schema_contract.py to "
        "check bare columns when a statement names exactly one base table, then "
        "baselining whatever that newly surfaces. Fixing DQ-133 alone does NOT clear "
        "this -- the blind spot is the defect; DQ-133 is one thing that fell into it. "
        "Reads 1 on 2026-10-05.",
    ),
    "DQ-135": (
        "Statewide rules whose number was split from the obligation that imposes it",
        # The extractor splits one legal sentence into a lead-in row plus its numbered
        # sub-paragraphs, and the actionability classifier judges each row ALONE. The
        # lead-in keeps the obligation words ("must", "at least") and is classified
        # actionable; the sub-paragraph carrying the actual figure has no obligation word
        # of its own and is classified not actionable. The number is then dropped from
        # every surface that filters on v2_is_actionable.
        #
        # Proven on the boarding-house parking rate: row 40309 p11 ("...at least the
        # following number of parking spaces-") is actionable TRUE, and 40310 p11
        # ("0.2 parking spaces for each boarding room, ... otherwise-0.5") is FALSE.
        # Re-running enrichment/extractors/actionable_classifier.py over all nine
        # Housing SEPP parking rows reproduces the stored values exactly, every FALSE
        # with reason "lep_sepp_weak_indicators" -- so this is the classifier's standing
        # verdict on fragments, not a stale row a retag would fix.
        #
        # Counts statewide current rows that are not actionable, open as a list
        # sub-paragraph, carry a digit, and contain no obligation word of their own.
        "SELECT count(*) FROM regulatory_provisions"
        " WHERE is_current AND source_council IS NULL"
        "   AND v2_is_actionable IS NOT TRUE"
        "   AND provision_text ~ '^\\s*\\(?[a-z0-9ivx]{1,4}\\)'"
        "   AND provision_text ~ '[0-9]'"
        "   AND provision_text !~* '\\m(must|at least|no more than|not exceed|required|minimum|maximum)\\M'",
        (),
        "Each is a figure from a statewide instrument that is withheld from any surface "
        "filtering on v2_is_actionable, because the sentence imposing it was split into "
        "another row. Reads 2,241 of 2,339 such sub-paragraph rows on 2026-10-05 "
        "(statewide current rows: 7,253 actionable, 10,680 not). Do NOT clear this by "
        "flipping rows: the classifier re-derives the same FALSE from the fragment, so "
        "hand-set values are reverted by the next enrichment run with force_reprocess. "
        "It clears by giving the classifier its parent paragraph, or by keeping a "
        "sub-paragraph joined to its lead-in at extraction. v2_has_numeric_value is "
        "wrong on the same rows -- 40310 plainly contains '0.2' and reads FALSE, and only "
        "1 statewide current row is (actionable FALSE, numeric TRUE). This is why "
        "DQ-130/132 measure a served set that EXCLUDES the boarding-house parking rate "
        "the SEPP tab displays; /api/sepp/parking-provisions deliberately does not filter "
        "on the flag.",
    ),
    "DQ-136": (
        "Statewide standards a determination reads that carry no machine-renewable proof",
        # Origin 2026-10-08, tracing the SEPP tab for 45 Graham St Greystanes. The
        # Multiple Occupancy card prints a clause reference beside every number --
        # "Max FSR 0.65:1  S168(2)(d)", "Min Lot Size 450m2  S168(2)(a)" -- read from
        # housing_sepp_standards.source_clause. The clause STRING is stored; nothing
        # ties the number to the clause's words. 33 of those rows have neither a quote
        # nor an anchored legislation URL, and 12 more (secondary_dwelling, Schedule 1)
        # have the URL but no quote, so no check can run on them either.
        #
        # PROOF here means the three things scripts/provenance_check.py needs to run
        # weekly: an anchored legislation.nsw.gov.au URL, the clause's own words, and
        # therefore the ability to assert the words are on the live page and the value
        # is inside the words. 9 rows have all three (ids 53-61, the CDC and DA pathway
        # rules for secondary dwellings, #1239) and are re-verified weekly. The other 45
        # are claims with a clause label attached.
        #
        # Do NOT clear this by writing source_quote from the value or from a model's
        # paraphrase: provenance_check.py fetches the anchor and compares word for word,
        # so a quote not literally in the clause fails the weekly check instead.
        "SELECT count(*) FROM housing_sepp_standards"
        " WHERE source_quote IS NULL OR source_quote = ''"
        "    OR legislation_url IS NULL"
        "    OR legislation_url !~ '^https://legislation\\.nsw\\.gov\\.au/.+#.+'",
        (),
        "Each is a number the SEPP tab prints with a clause reference that no machine can "
        "trace to that clause. Reads 45 of 54 on 2026-10-08 (the 9 proven are the #1239 "
        "secondary-dwelling CDC/DA rules). Splits two ways: 33 with neither quote nor "
        "anchored URL (dual_occupancy, independent_living_unit, multi_dwelling, "
        "residential_flat_r1r2, residential_flat_r3r4_inner/outer, terraces) and 12 with "
        "the URL and no quote (secondary_dwelling). cdc_eligibility_standards is clean by "
        "this test, 4 of 4 quoted. Clears row by row: anchor the URL, store the clause's "
        "own words, let provenance_check.py prove it. The read gate in "
        "ce-authority-status-and-offer-2026-10-08.md cannot be switched on before this "
        "reaches 0, because it would take the table from 54 servable rows to 9.",
    ),
    "DQ-137": (
        "Numeric standards whose declared scope is 'all', so a determination picks among them",
        # Origin 2026-10-08, same address. The Pattern Book card refused the pathway:
        # "lot size min: minimum 900.0sqm required, 573.81sqm available". The 900 is real
        # -- sepp_structured_requirements.metric_value -- but
        # lib/pattern-book-eligibility/check-numerics.ts:52-62 selects it with
        #   WHERE metric_name='lot_size_min' AND (applies_to='Pattern_Book' OR 'all')
        # and no zone, LGA or development-type filter. Its own comment says so: "we don't
        # have zone-specific filtering yet ... queries all". There is no Pattern_Book row
        # at all, so the match is on 'all', 24 rows compete, values run 200 to 1500, and
        # the card took 900. Row order decides eligibility.
        #
        # This is NOT the proof problem (DQ-136) and a proof gate does not catch it: a
        # fully quoted row can still be the wrong row. 199 of 236 numeric standards
        # declare applies_to='all', across 7 metrics with more than one competitor --
        # height_max has 75 rows spanning 3.0 m to 32.5 m. All of them came from the
        # Exempt and Complying Development Codes SEPP 2008, whose Part and development
        # type IS the scope, and the scope was flattened on extraction.
        #
        # source_clause on these rows holds a filename and page ("...Codes) 2008 - NSW
        # Legislation.pdf - Page 213"), not a clause, so surfacing it would not help a
        # reader choose either.
        "SELECT count(*) FROM sepp_structured_requirements"
        " WHERE requirement_category = 'numeric_standard'"
        "   AND applies_to = 'all'"
        "   AND metric_name IN ("
        "     SELECT metric_name FROM sepp_structured_requirements"
        "      WHERE requirement_category = 'numeric_standard' AND applies_to = 'all'"
        "      GROUP BY metric_name HAVING count(*) > 1)",
        (),
        "Each is a regulatory figure any determination can select without a filter "
        "distinguishing it from its competitors. Reads 199 of 236 numeric standards on "
        "2026-10-08. The 7 contested metrics: height_max 75 rows (3.0-32.5 m), "
        "setback_side_min 31 (1.0-10.0), setback_rear_min 30 (1.0-8.0), lot_size_min 24 "
        "(200-1500), setback_front_min 21 (1.2-15.0), fsr_min 13 (0.65-10.0), "
        "deep_soil_percent_min 5 (5-15). Clears by scoping each row to the Part, "
        "development type and zone its source clause actually governs -- NOT by adding an "
        "ORDER BY or a LIMIT 1, which only makes the arbitrary pick repeatable. The "
        "serving rule this exists to enforce: a query returning more than one candidate "
        "for one determination must refuse, not choose.",
    ),
    "DQ-138": (
        "Rule tables the public browser role can write",
        # Origin 2026-10-08, measuring the authority surface for the read-gate design.
        # anon is the role behind NEXT_PUBLIC_SUPABASE_ANON_KEY, which ships to every
        # browser. It holds INSERT, UPDATE, DELETE and TRUNCATE on every rule table.
        #
        # Nothing is exploitable TODAY: RLS is enabled on these tables with no policies
        # and anon has rolbypassrls = false, so every statement is denied. That is ONE
        # mechanism, and the grant sits underneath it. A single permissive policy added
        # for an unrelated feature, or one DISABLE ROW LEVEL SECURITY, turns a public key
        # into a write path to regulatory data -- and the grant would make it legal.
        #
        # REVOKE costs nothing functionally, precisely because RLS already denies these
        # roles and no serving path uses them to read a rule table: the app connects as
        # postgres, the table owner, which bypasses RLS. Defence in depth that cannot
        # regress a feature.
        #
        # SCOPE LIMIT, recorded deliberately: the table list below is hardcoded. A
        # catalogue sweep on 2026-10-08 found 72 further rule-shaped tables outside it,
        # including 17 BACKUP tables holding copies of regulatory data (11
        # dcp_setback_controls_*, 6 regulatory_provisions_citation_backup_*). ALL 149
        # public base tables are writable by anon and authenticated (1,192 grant rows) --
        # the Supabase default -- so this probe counts the rule-bearing subset rather
        # than all 149, because legitimate anon write paths exist (dcp_interest for the
        # register-interest form, feedback, leads). Replace this list with the derived
        # rule-table inventory (A1 of ce-rule-provenance-lockdown-PLAN-2026-10-08.md)
        # once that exists; until then a new rule table is NOT counted here.
        # The probe's scope must be the SAME scope the migrations protect, or the
        # check goes green on a table the fix covered. The first version inspected
        # only 085's 17 names, so a GRANT UPDATE on lep_zone_coverage after 086 --
        # a serving gate, re-granted -- would have left this reading 0. Caught by
        # cross-review (gpt-5.6-sol, MEDIUM silent-failure); the repo has a memory
        # file for exactly this shape, feedback-a-check-can-watch-the-field-the-fix-
        # abandoned. Name patterns and the table list below are kept identical to
        # migrations/086_revoke_public_writes_on_remaining_rule_tables.sql.
        "SELECT count(*) FROM ("
        "  SELECT DISTINCT g.table_name, g.grantee"
        "    FROM information_schema.role_table_grants g"
        "    JOIN information_schema.tables t"
        "      ON t.table_schema = g.table_schema"
        "     AND t.table_name = g.table_name"
        "     AND t.table_type = 'BASE TABLE'"
        "   WHERE g.table_schema = 'public'"
        "     AND g.grantee IN ('anon', 'authenticated')"
        "     AND g.privilege_type IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')"
        "     AND (g.table_name IN ('housing_sepp_standards', 'cdc_eligibility_standards',"
        "                           'regulatory_provisions', 'instrument_registry',"
        "                           'sepp_structured_requirements', 'sepp_adg_requirements',"
        "                           'dcp_setback_controls', 'lep_land_use_table',"
        "                           'lep_clauses', 'lep_development_type_clauses',"
        "                           'development_controls', 'control_codes',"
        "                           'quantitative_standards', 'dcp_base_requirements',"
        "                           'dcp_precinct_requirements', 'dcp_table_of_contents',"
        "                           'provision_versions', 'lep_zone_coverage')"
        # NOTE the doubled %%: run() calls cur.execute(sql, params) with a tuple,
        # so psycopg2 interpolates and a single % in a LIKE pattern is read as a
        # placeholder (IndexError: tuple index out of range).
        "          OR g.table_name LIKE 'dcp\\_setback\\_controls\\_%%'"
        "          OR g.table_name LIKE 'regulatory\\_provisions\\_%%backup%%')) s",
        (),
        "Each is one (rule table, public role) pair holding write privileges. Reads 16 on "
        "2026-10-08 across the 8 tables that existed in the first version of this list -- "
        "anon and authenticated, each with DELETE, INSERT, TRUNCATE and UPDATE. The list "
        "is now 17 tables, so the first run after this row lands reads higher; that is "
        "the list widening, not a regression. Clears with REVOKE ALL on those tables from "
        "anon and authenticated. Verify by re-running this probe, NOT by checking the app "
        "still works: the app connects as postgres and is unaffected either way, so a "
        "green app proves nothing about this row.",
    ),
    "DQ-140": (
        "Served LEP rules whose zone or development-type scope nobody decided",
        # Split from DQ-114 on 2026-10-09 (user ruling: unblock the merge, then
        # do the full fix as its own PR). The whole Inner West LEP 2022 was
        # loaded with no scope: 554 served rules, every one reading ALL for both
        # keys, 434 as no_config and 120 never tagged at all. An LEP clause
        # states its own reach in its own words -- "This clause applies to land
        # in Zone E3", "applies to Lot 1, DP 1070825", or nothing, in which case
        # cl 1.4 (the land the Plan applies to) is the decision. The rows are
        # also stored split by subclause, so a fragment like "(a) each lot will
        # be used for a dwelling house" carries no zone text of its own: the
        # fix is per CLAUSE, not per row. Counted per key, as DQ-114 is, and
        # including no_config, because no council config can ever resolve an
        # LEP (DQ-33's reasoning) -- here no_config is simply "not read yet".
        "SELECT count(*) FROM ("
        "  SELECT 1 FROM regulatory_provisions rp"
        "    JOIN documents d ON d.id = rp.document_id AND d.document_type = 'LEP'"
        "   WHERE rp.is_current AND rp.v2_is_actionable"
        "     AND (rp.v2_dev_type_source IN ('config_silent','filtered_to_all',"
        "                                    'no_document_id','no_config')"
        "          OR rp.v2_dev_type_source IS NULL)"
        "  UNION ALL"
        "  SELECT 1 FROM regulatory_provisions rp"
        "    JOIN documents d ON d.id = rp.document_id AND d.document_type = 'LEP'"
        "   WHERE rp.is_current AND rp.v2_is_actionable"
        "     AND (rp.v2_zone_source IN ('config_silent','filtered_to_all',"
        "                                'no_document_id','no_config')"
        "          OR rp.v2_zone_source IS NULL)"
        ") t",
        (),
        "Each count is one key -- a zone list or a development-type list -- on "
        "one served LEP rule, reading ALL because nobody read the clause. The "
        "rule is shown to every zone and every kind of development, so an E3 "
        "business-premises clause or a single-lot Schedule 1 clause appears on "
        "an R2 house. Reachable only by reading each clause's own words and "
        "recording them, per clause rather than per stored row.",
    ),
    "DQ-141": (
        "Served rules from the second, council-less load of Ashfield DCP 2016",
        # Found 2026-10-10. Ashfield DCP 2016 is loaded twice: the current load
        # (Inner_West_Ashfield_DCP_2016__chapter_*, source_council 'ashfield') and
        # an older one (document ids 'Inner West Ashfield DCP 2016 - Chapter *'
        # plus one Chapter D id) with NO council, still served. Measured by
        # wording containment: E1 775/887 and D 42/48 old rules also appear in
        # the new load (served twice), while A 60/140, B 2/9, C 36/181 and F 0/71
        # do not -- the new load may be short, or the old text outdated. Only the
        # council's PDF can say which. Labelling the old rows 'ashfield' is NOT
        # the fix: OC-12 would then count all of them as untraced.
        "SELECT count(*) FROM regulatory_provisions"
        " WHERE is_current AND v2_is_actionable AND source_council IS NULL"
        "   AND (document_id ILIKE 'Inner West Ashfield DCP 2016 - Chapter%%'"
        "        OR document_id ILIKE 'Inner\_West\_Ashfield\_DCP\_2016\_\_\_Chapter%%')",
        (),
        "Each count is one served rule from a second copy of Ashfield DCP 2016 "
        "that carries no council. Where the copy duplicates the current load the "
        "rule is shown twice; where it differs, either the current load is "
        "missing it or the copy is outdated. Resolved per chapter against the "
        "council's PDF: retire what duplicates, restore what the current load is "
        "missing, never relabel.",
    ),
    "DQ-142": (
        "Building-area controls missing for a council's housing type (every council with DCP controls)",
        # Measured 2026-10-10 after DQ-139 read 11: DQ-139 only counts a missing
        # REAR where a front or side exists, so a council missing front AND rear,
        # or any coverage/landscaping cap, never showed. The buildable-area sum
        # needs: front, side and rear setbacks, and a footprint cap (site coverage
        # or landscaped area). Counted per (council, dev type, control) for the
        # three main low-rise types -- ONLY where the council already has at least
        # one current control for that type, so no DCP is presumed to cover a type
        # it may not. That is a recorded scope limit: this is a floor.
        # A control counts as present when a current, not-under-review row has a
        # number, or records a decided absence: condition beginning 'NO FIGURE:'
        # with the DCP's own words in source_text (e.g. 'match the neighbours').
        "WITH types AS ("
        "  SELECT DISTINCT lga, dev_type FROM dcp_setback_controls"
        "   WHERE is_current AND NOT needs_review AND lga <> 'nsw_statewide'"
        "     AND dev_type IN ('dwelling_house', 'secondary_dwelling', 'dual_occupancy')),"
        " needed AS ("
        "  SELECT t.lga, t.dev_type, c.ctl FROM types t"
        "  CROSS JOIN (VALUES ('front_setback'), ('side_setback'), ('rear_setback'), ('cap')) c(ctl)),"
        " have AS ("
        "  SELECT lga, dev_type,"
        "         CASE WHEN control_type IN ('max_site_coverage', 'landscaping_min', 'deep_soil_min') THEN 'cap'"
        "              ELSE control_type END AS ctl"
        "    FROM dcp_setback_controls"
        "   WHERE is_current AND NOT needs_review"
        "     AND (COALESCE(value_min, value_max) IS NOT NULL"
        "          OR (condition LIKE 'NO FIGURE:%%' AND source_text IS NOT NULL)))"
        " SELECT count(*) FROM needed n"
        "  WHERE NOT EXISTS (SELECT 1 FROM have h"
        "                     WHERE h.lga = n.lga AND h.dev_type = n.dev_type AND h.ctl = n.ctl)",
        (),
        "Each count is one control the buildable-area sum needs for a housing "
        "type a council's DCP covers, with neither a number nor a quoted decision "
        "that there is none. Where it is missing, the app shows no building-area "
        "figure for that council and type. Cleared by extracting the control from "
        "the council's DCP, or recording 'NO FIGURE:' with the DCP's own words.",
    ),
    "DQ-139": (
        "Council/development-type pairs whose setback arithmetic lacks a required control",
        # Origin 2026-10-08, the LEP tab for 45 Graham St Greystanes. The yield card
        # showed "DCP Setbacks Applied -- Front: 6m, Side: 0.9m" and "Buildable footprint
        # 423m2 (74% of lot)". Both setbacks are Cumberland's own current rows, page 8 of
        # cumberland-part-b-residential.pdf, and the is_current filter correctly rejected
        # its two stale front-setback rows (5.5 m and 4.0 m). That part works.
        #
        # Cumberland has no CURRENT rear setback; its only rear row (8.0 m, id 30) is
        # is_current = false, needs_review = true. The footprint formula in
        # services/constraint_arithmetic.py:615-623 is
        #   (frontage - 2*side) * (depth - front - rear)
        # and the displayed number is only reachable with rear = 0:
        #   (18.79 - 1.8) * (30.9 - 6 - 0) = 16.99 * 24.9 = 423.05  -> "423m2"
        #   423 / 573.81 = 73.7%                                    -> "74%"
        #
        # So a missing control became zero, and zero is the PERMISSIVE direction: it makes
        # the buildable area larger. The card does print "Calculated from 3 of 6 planning
        # controls", but it still prints the figure. A caveat beside a number is not the
        # same as withholding the number.
        #
        # SCOPE. Counts (lga, dev_type) pairs where the arithmetic can run in that
        # state: a current front or side setback exists for that development type, so
        # the block renders, and no current rear setback does for it.
        #
        # The first version of this probe grouped by lga ALONE and read 1. That was
        # wrong in the direction that reports clean: a rear setback recorded for
        # residential_flat_building satisfied the EXCEPT for the whole council and hid
        # the dwelling_house gap. Scoped per development type -- the scope
        # _get_dcp_value actually serves on -- it reads 14. Caught by cross-review
        # (gpt-5.6-sol, MEDIUM db-filter) on this branch; the second time in one
        # session that a filter left out of a query made a defect look smaller.
        # USABLE VALUE, not merely a row. A current row whose value_min and
        # value_max are both null supplies no number -- Cumberland's
        # max_site_coverage and deep_soil_min rows are exactly that shape, which
        # the DCP tab renders as "No set number". Counting such a row as a present
        # control would report clean while _get_dcp_value still returns nothing and
        # the arithmetic still cannot run. Caught by cross-review (gpt-5.6-sol,
        # MEDIUM null-guard). The predicate matches the serving code's own test.
        "SELECT count(*) FROM ("
        "  SELECT lga, dev_type FROM dcp_setback_controls"
        "   WHERE is_current AND COALESCE(value_min, value_max) IS NOT NULL"
        "     AND control_type IN ('front_setback', 'side_setback')"
        "   GROUP BY lga, dev_type"
        "  EXCEPT"
        "  SELECT lga, dev_type FROM dcp_setback_controls"
        "   WHERE is_current AND COALESCE(value_min, value_max) IS NOT NULL"
        "     AND control_type = 'rear_setback'"
        "   GROUP BY lga, dev_type) s",
        (),
        "Each is a (council, development type) pair whose buildable-footprint and "
        "DCP-adjusted-GFA figures would be computed with a setback absent. Reads 14 on "
        "2026-10-09 scoped per development type; the same query grouped by council alone "
        "reads 1, which is why it is not grouped that way. This row measures the DATA "
        "gap and stays open until the controls are extracted. The CODE half -- refusing "
        "to publish a footprint, or a computation step carrying a figure, when an input "
        "is absent -- is closed separately and covered by tests/test_constraint_"
        "arithmetic.py (TestThreeState), NOT by this count, so a non-zero reading here "
        "is not evidence that the permissive default is back. Not counted: "
        "constraint_arithmetic.py's own STOREY_HEIGHT_M, MIN_DWELLING_GFA_M2 and "
        "PARKING_AREA_PER_SPACE_M2 are engineering assumptions, not regulatory values.",
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
