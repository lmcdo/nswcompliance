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
 * Last DB verification: 2026-07-26 (see per-field source query below).
 *
 *   provisionsTotal            SELECT COUNT(*) FROM regulatory_provisions
 *   dcpActionableProvisions    SELECT COUNT(*) FROM regulatory_provisions
 *                                WHERE v2_is_actionable = TRUE AND v2_dcp_layer IS NOT NULL
 *   dcpNumericCouncils         SELECT COUNT(DISTINCT r.display_name)
 *                                FROM dcp_setback_controls c
 *                                JOIN lga_registry r ON r.slug = c.lga
 *                                WHERE c.is_current = TRUE
 *                                  AND r.slug != 'nsw_statewide'
 *                                  AND r.parent_lga IS NULL
 *                                (identical to /api/dcp/coverage — the canonical list)
 *   dcpSetbackRows             SELECT COUNT(*) FROM dcp_setback_controls   (all extracted rows)
 *   heritageAreas              SELECT COUNT(*) FROM heritage_conservation_areas
 *   regulatoryDefinitions      SELECT COUNT(*) FROM regulatory_definitions
 *
 * Fields WITHOUT a DB query below are editorial/config-derived facts, frozen here
 * so they stay consistent across pages (not auto-verifiable):
 *   dcpFullCouncils            7 councils with full structured DCP configs
 *                                (3 Inner West _tag_x methods + 4 in COUNCIL_CONFIGS)
 *   seppStandards / adgCriteria  SEPP (Housing) 2021 + Apartment Design Guide
 *   secondaryDwellingCouncils  councils in the Planning Portal open-data secondary-dwelling feed
 *   floodLgas                  LGAs with modelled flood-depth coverage
 *   totalNswCouncils           128 — count of NSW councils (external fact)
 *   lgasCovered                statewide portal/satellite layer coverage
 *   riskLayers / govDataSources  named on the homepage
 */

/** Exact integers — each either DB-verified (see header) or a frozen editorial fact. */
export const COVERAGE = {
  provisionsTotal: 53716,
  dcpActionableProvisions: 39827,
  dcpNumericCouncils: 25,
  dcpFullCouncils: 7,
  dcpSetbackRows: 1069,
  heritageAreas: 2039,
  regulatoryDefinitions: 474,
  seppStandards: 33,
  adgCriteria: 23,
  secondaryDwellingCouncils: 102,
  floodLgas: 71,
  totalNswCouncils: 128,
  lgasCovered: 130,
  riskLayers: 8,
  govDataSources: 7,
} as const;

/**
 * Rendered strings. Growing counts round DOWN with a "+" so the published claim
 * stays true as the corpus grows; countable/stable sets show the exact figure.
 */
export const COVERAGE_DISPLAY = {
  provisionsTotal: '53,000+',
  dcpActionableProvisions: '39,000+',
  dcpNumericCouncils: '25',
  dcpFullCouncils: '7',
  dcpSetbackRows: '1,000+',
  heritageAreas: '2,039',
  regulatoryDefinitions: '470+',
  seppStandards: '33',
  adgCriteria: '23',
  secondaryDwellingCouncils: '102',
  floodLgas: '71',
  totalNswCouncils: '128',
  lgasCovered: '130+',
  riskLayers: '8',
  govDataSources: '7',
} as const;

export type CoverageKey = keyof typeof COVERAGE;
