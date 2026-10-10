/**
 * Coverage & corpus statistics — SINGLE SOURCE OF TRUTH.
 *
 * prior-art-checked: reuse not viable because no stats-constants module exists.
 *   /api/dcp/coverage/route.ts returns the live council LIST (not the marketing
 *   counts); CoverageSection.tsx and the *Display components RENDER values passed
 *   as props; none holds the corpus/coverage figures. This file is that missing
 *   source — the numbers those and the marketing pages should read FROM.
 *
 * Every public-facing "how much data do we have" number lives here. Pages MUST
 * import from this module instead of hard-coding figures inline. Hard-coded
 * copies drift and go stale as coverage grows; a "never a guess" product cannot
 * publish numbers it can't trace.
 *
 * Two exports:
 *   COVERAGE          — exact integers, each verifiable against a live DB query.
 *   COVERAGE_DISPLAY  — the strings pages render. Growing/volatile counts use a
 *                       rounded-DOWN "N,000+" form so the claim stays TRUE as the
 *                       corpus grows; stable/countable sets use the exact figure.
 *
 * PROVENANCE — verify with:  python scripts/verify_coverage_stats.py
 * Last DB verification: 2026-09-01 (see per-field source query below).
 *
 *   provisionsTotal            SELECT COUNT(*) FROM regulatory_provisions
 *   dcpActionableProvisions    SELECT COUNT(*) FROM regulatory_provisions
 *                                WHERE v2_is_actionable = TRUE AND v2_dcp_layer IS NOT NULL
 *   dcpNumericCouncils         SELECT COUNT(DISTINCT COALESCE(parent.display_name, r.display_name))
 *                                FROM dcp_setback_controls c
 *                                JOIN lga_registry r ON r.slug = c.lga
 *                                LEFT JOIN lga_registry parent ON parent.slug = r.parent_lga
 *                                WHERE c.is_current = TRUE
 *                                  AND (c.needs_review IS NULL OR c.needs_review = FALSE)
 *                                  AND r.slug != 'nsw_statewide'
 *                                  AND r.is_active = TRUE
 *                                  AND (r.parent_lga IS NULL OR parent.is_active = TRUE)
 *                                (identical to /api/dcp/coverage — the canonical list)
 *                                FIXED 2026-09-07: was 25, kept deliberately understated to
 *                                match /api/dcp/coverage's own bug (a parent_lga IS NULL
 *                                filter that dropped Ashfield/Leichhardt/Marrickville — the
 *                                three councils with the DEEPEST DCP integration — because
 *                                their parent Inner West registry row holds 0 current rows
 *                                to be "shown under"). First fix attempt (same day) removed
 *                                the filter with no aggregation and landed on 28, wrongly
 *                                counting the three abolished pre-2016-merger councils as
 *                                separate CURRENT councils — caught by Sol cross-review
 *                                (HIGH 0.96) before merge. Corrected to aggregate them under
 *                                Inner West's current display name: 26 (25 + Inner West,
 *                                newly surfaced), re-verified live.
 *   dcpSetbackTripleCouncils   Councils holding ALL THREE of front/side/rear setback — the
 *                                claim the conveyancer page actually makes. Live:
 *                                WITH t AS (SELECT lga,
 *                                  count(*) FILTER (WHERE control_type='front_setback') f,
 *                                  count(*) FILTER (WHERE control_type='side_setback')  s,
 *                                  count(*) FILTER (WHERE control_type='rear_setback')  r
 *                                FROM dcp_setback_controls WHERE is_current
 *                                  AND (needs_review IS NULL OR needs_review=FALSE)
 *                                  AND COALESCE(value_min, value_max) IS NOT NULL  -- a number, not a
 *                                    quoted 'NO FIGURE' rule (2026-10-10: 26 with them, 19 without)
 *                                  AND applicability IS DISTINCT FROM 'precinct_specific'
 *                                  AND lga<>'nsw_statewide' AND lga<>'inner_west' GROUP BY lga)
 *                                SELECT count(*) FILTER (WHERE f>0 AND s>0 AND r>0) FROM t; -> 21
 *                                (22 until later on 2026-09-14, when precinct-only rules stopped being
 *                                served council-wide (DQ-99): ashfield's only front setback was the
 *                                Haberfield Yasmar Estate rule. 23 until the outreach gate's first run
 *                                that morning measured 22 live; an exact count must never overstate.)
 *                                (was 24 as of 2026-08-24; re-verified 2026-09-01 and re-derived
 *                                independently against a fresh session, not just the script's own
 *                                claim. burwood, cumberland, ku_ring_gai, parramatta and woollahra
 *                                currently lack at least one of the three control types — which
 *                                one of these five newly dropped below 24 was not traced further;
 *                                this corrects the published figure to match the live count, an
 *                                exact-count field must never overstate.)
 *   dcpSetbackRows             SELECT COUNT(*) FROM dcp_setback_controls   (all extracted rows)
 *   heritageAreas              SELECT COUNT(*) FROM heritage_conservation_areas
 *   regulatoryDefinitions      SELECT COUNT(*) FROM regulatory_definitions
 *
 * Fields WITHOUT a DB query below are config- or source-derived. "Editorial" was
 * never a reason a number COULD NOT be verified — only a reason nobody had written
 * the check, which is how `lgasCovered: 130` claimed more councils than NSW has.
 * Two of them are now checked against their real source by
 * tests/test_coverage_source_derived_stats.py: govDataSources (the homepage's own
 * DATA_SOURCES list) and secondaryDwellingCouncils (the generated stats file).
 *
 * dcpFullCouncils ("7 councils with full structured provisions") was RETIRED on
 * 2026-09-14 by the user's decision on the outreach claim set (claim OC-14): no council
 * holds its own target set of DCP chapters, so no council is "full". Do not re-add it.
 *
 * riskLayers ("8 risk layers") was RETIRED on 2026-09-14 (outreach claim OC-13). It was a
 * headline stat on the homepage and two audience pages, and nothing produced an 8: searched
 * 2026-09-11, the homepage's CLIMATE_HAZARDS (4), the /climate-risk hazards section (5), the
 * open-data catalogue (7), the capability tiles, and every table whose name contains 'risk'.
 * An unsourced number is grounded or removed, never adjusted to another guess. Do not re-add
 * it without a source and a check against that source.
 *
 * The remaining fields are frozen here so they stay consistent across pages:
 *   seppStandards / adgCriteria  NOW DB-VERIFIED, see verify_coverage_stats.py.
 *                                seppStandards was published as 33 while
 *                                housing_sepp_standards held 45 AND /planning-standards
 *                                rendered all 45 live — two pages, one fact, two
 *                                numbers. Corrected to 45 on 2026-09-11; 44 on 2026-10-09 after
 *                                migration 088 retired the 0-parking row (id 35);
 *                                42 on 2026-10-10 after 089 retired ids 34 and 44;
 *                                58 on 2026-10-10 after 090 added Schedule 1 cl 5-11.
 *   secondaryDwellingCouncils  councils in the Planning Portal open-data secondary-dwelling feed
 *   floodStudies               COUNCIL FLOOD STUDIES ingested (NOT an LGA count).
 *   floodDepthStudies          Of those, the ones that can answer DEPTH: the studies whose
 *                                FLOOD_STUDIES entry carries has_depth=True. THREE — tweed,
 *                                wollongong, redbank. Hawkesbury's rasters are water LEVEL
 *                                only (h, no pre-computed d), so it cannot answer a depth
 *                                question. Five surfaces said "modelled flood depth ... 4
 *                                studies" and one named Hawkesbury among them; the count was
 *                                verified against len(FLOOD_STUDIES), which is the number of
 *                                studies INGESTED, not the number that deliver depth — so the
 *                                check passed on the wrong artifact. Use floodStudies for
 *                                "studies ingested" and floodDepthStudies for any DEPTH claim.
 *                                services/flood_truth.py FLOOD_STUDIES holds exactly four:
 *                                hawkesbury, tweed, wollongong, redbank. This was published
 *                                as "71 LGAs of flood depth" until 2026-08-24 — 71 is the
 *                                flood OVERLAY council count (SELECT count(DISTINCT lga_name)
 *                                FROM spatial_overlays WHERE layer_type='flood' -> 72), i.e.
 *                                the yes/no layer the depth claim explicitly said it was
 *                                "not just". Depth exists ONLY where a study is ingested;
 *                                elsewhere the answer is the mapped flood planning area, and
 *                                flood_truth.py degrades to "not assessed", never to "no".
 *   totalNswCouncils           128 — count of NSW councils (external fact)
 *   lgasCovered                statewide portal/satellite layer coverage. MUST NOT EXCEED
 *                                totalNswCouncils — it is the same population. Published as
 *                                "130+" until 2026-08-24, i.e. more councils than NSW has.
 *                                Live: SELECT count(DISTINCT lga_name) FROM spatial_overlays
 *                                WHERE layer_type='zone' -> 128, and the CDC record -> 128.
 *   govDataSources             named on the homepage (DATA_SOURCES)
 */

/** Exact integers — each either DB-verified (see header) or a frozen editorial fact. */
export const COVERAGE = {
  provisionsTotal: 53716,
  dcpActionableProvisions: 39827,
  dcpNumericCouncils: 26,
  dcpSetbackTripleCouncils: 19,
  dcpSetbackRows: 1069,
  heritageAreas: 2039,
  regulatoryDefinitions: 474,
  seppStandards: 58,
  adgCriteria: 23,
  secondaryDwellingCouncils: 102,
  floodStudies: 4,
  floodDepthStudies: 3,
  totalNswCouncils: 128,
  lgasCovered: 128,
  govDataSources: 7,
} as const;

/**
 * Rendered strings. Growing counts round DOWN with a "+" so the published claim
 * stays true as the corpus grows; countable/stable sets show the exact figure.
 */
export const COVERAGE_DISPLAY = {
  provisionsTotal: '53,000+',
  dcpActionableProvisions: '39,000+',
  dcpNumericCouncils: '26',
  dcpSetbackTripleCouncils: '19',
  dcpSetbackRows: '1,000+',
  heritageAreas: '2,039',
  regulatoryDefinitions: '470+',
  seppStandards: '58',
  adgCriteria: '23',
  secondaryDwellingCouncils: '102',
  floodStudies: '4',
  floodDepthStudies: '3',
  totalNswCouncils: '128',
  lgasCovered: '128',
  govDataSources: '7',
} as const;

export type CoverageKey = keyof typeof COVERAGE;
