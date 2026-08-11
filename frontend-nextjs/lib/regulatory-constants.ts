/**
 * NSW Planning Regulatory Constants
 *
 * Centralized repository for all NSW planning legislation thresholds,
 * zone definitions, and numeric standards. These values are defined
 * in state legislation and do not vary by LGA.
 *
 * @see https://legislation.nsw.gov.au/
 */

/**
 * NSW Standard Land Use Zones
 *
 * Standard Instrument (Local Environmental Plans) Order 2006
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/sl-2006-0155
 *
 * prior-art-checked: this edits the existing NSW_STANDARD_ZONES in this same
 * file in place (not a new parallel implementation) — the guard's suggested
 * matches are unrelated blog pages and the already-known
 * environmental-relevance-filter.ts duplicate (itself flagged for
 * consolidation in DQ-30, .claude/DATA_QUALITY_TRACKER.md, not reused here
 * because it is a separate hardcode being replaced, not a shared utility).
 *
 * DQ-30: the zone lists below were previously a flat, independently-
 * maintained mix of legacy (B1-B8, IN1-IN4) and current (E1-E5, MU1) codes,
 * hand-curated with no shared source — the kind of duplication that let the
 * same B/E mismatch happen twice in this codebase (once here, once in
 * `dcp_general_requirements`/zone-translation.ts, fixed independently in
 * Nov 2025). Now built by expanding each current-era zone through
 * getZoneAliases() from the single shared source (shared/zone-taxonomy.json),
 * so the legacy/current mapping can never drift between this file and
 * zone-translation.ts again.
 */
import { getZoneAliases } from './zone-translation';

function aliasesOf(...currentZones: string[]): string[] {
  return Array.from(new Set(currentZones.flatMap(z => getZoneAliases(z))));
}

export const NSW_STANDARD_ZONES = {
  /** Residential zones that permit dwelling houses and associated development.
   * R-zone codes were not renamed by the 2023 Employment Zones Reform. */
  RESIDENTIAL: ['R1', 'R2', 'R3', 'R4', 'R5', 'RU5'] as const,

  /** Zones that permit apartment developments (including post-LMR reforms):
   * residential R1-R4, plus centre/mixed-use zones (current + their legacy
   * B-zone aliases) that permit shop-top housing / residential flat buildings. */
  APARTMENT_PERMITTING: [
    'R1', 'R2', 'R3', 'R4',
    ...aliasesOf('E1', 'E2', 'MU1'),
  ] as const,

  /** Industrial and employment zones: E3 (Productivity Support), E4 (General
   * Industrial), E5 (Heavy Industrial) plus their legacy B/IN aliases. */
  INDUSTRIAL: aliasesOf('E3', 'E4', 'E5'),

  /** Business/commercial zones: all Employment zones (E1-E5) and Mixed Use
   * (MU1), plus their legacy B-zone aliases. */
  BUSINESS: aliasesOf('E1', 'E2', 'E3', 'E4', 'E5', 'MU1'),
} as const;

/**
 * Zones eligible for Housing SEPP 2021 provisions: residential R1-R4 plus
 * centre/mixed-use zones that permit shop-top housing (E1, MU1 — current
 * codes; were B1/B2/B4).
 *
 * DQ-30 (.claude/DATA_QUALITY_TRACKER.md): this exact literal
 * (`['R1','R2','R3','R4','B1','B2','B4']`) was independently hardcoded,
 * byte-for-byte identical, in 4 separate files (lib/see/seeBuilders.ts,
 * lib/see/section-aggregation.ts, lib/pdf/see-helpers.ts,
 * components/pdf/ContextSection.tsx) — all now import this single export
 * instead. B1/B2/B4 are retired NSW zone codes (April 2023 Employment Zones
 * Reform); each is mechanically translated to its real current equivalent
 * (B1,B2->E1; B4->MU1) — not a scope change, the same zones under their
 * current names. This list is matched against a live property's CURRENT
 * zone code (from the Planning Portal), which is never a legacy code, so
 * unlike APARTMENT_PERMITTING/INDUSTRIAL/BUSINESS above it deliberately
 * does NOT include legacy aliases via aliasesOf() — those exist for
 * matching zone codes stored in old DB rows, not live property zones.
 */
// Not `as const`: every consumer calls `.includes(zoneCode)` with a plain
// `string`, which `as const`'s literal-union element type would reject.
export const HOUSING_SEPP_ZONES: readonly string[] = ['R1', 'R2', 'R3', 'R4', 'E1', 'MU1'];

/**
 * Residential zones eligible for the Exempt & Complying Development Codes
 * (CDC) pathway: R1-R4 and RU5, deliberately NOT including R5 (Large Lot
 * Residential) — the same 5-zone set was independently declared, identically,
 * in 3 separate files, which is itself evidence the R5 exclusion is
 * intentional rather than an oversight (unlike the SEPP Housing 2021 cl 49
 * general "residential zone" definition below, R1-R5+RU5, which does include
 * R5). DQ-30 (.claude/DATA_QUALITY_TRACKER.md): consolidated from
 * `components/compliance/CDCScreener.tsx`,
 * `components/compliance/ExemptComplyingProvisions.tsx`, and
 * `app/api/sepp/exempt-complying/route.ts` — do NOT merge this with
 * NSW_STANDARD_ZONES.RESIDENTIAL, they are deliberately different scopes.
 * Confirm against the actual Housing Code (SEPP Exempt and Complying
 * Development Codes 2008, Schedule 1) before changing either list, not by
 * inference.
 */
export const CDC_HOUSING_CODE_ZONES: readonly string[] = ['R1', 'R2', 'R3', 'R4', 'RU5'];

/**
 * Transport Oriented Development (TOD) Thresholds
 *
 * SEPP (Housing) 2021 - Schedule 11: Definition of "accessible area"
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.11
 */
export const TOD_THRESHOLDS = {
  /** Maximum walking distance to heavy rail/metro station for "accessible area" (meters) */
  HEAVY_RAIL_WALKABLE_M: 800,

  /** Maximum walking distance to light rail station for "accessible area" (meters) */
  LIGHT_RAIL_WALKABLE_M: 600,

  /** Maximum walking distance to frequent bus service for parking reductions (meters) */
  BUS_WALKABLE_M: 400,

  /** Search radius for nearby transport stops when detecting TOD eligibility (meters) */
  TRANSPORT_PROXIMITY_SEARCH_M: 1000,
} as const;

/**
 * Housing SEPP Low and Mid-Rise (LMR) Standards
 *
 * Two-stage rollout under SEPP (Housing) 2021 amendments:
 *
 * Stage 1 (effective 1 Jul 2024): Dual occupancy + semi-detached in R2, statewide
 *   except Blue Mountains, Hawkesbury, Wollondilly, Bathurst Regional.
 *
 * Stage 2 (effective 28 Feb 2025): Full LMR housing types (terraces, MDF, apartments
 *   up to 6 storeys, shop-top) within 800m of 171 nominated stations/town centres.
 *   Geographic scope: Greater Sydney, Central Coast, Lower Hunter/Newcastle,
 *   Illawarra-Shoalhaven only.
 *
 * @see https://www.planning.nsw.gov.au/policy-and-legislation/housing/low-and-mid-rise-housing-policy
 */
export const HOUSING_SEPP_LMR = {
  /** Zones eligible for Stage 2 LMR (full housing types near nominated centres) */
  ELIGIBLE_ZONES: ['R1', 'R2', 'R3', 'R4'] as const,

  /** Zone eligible for Stage 1 (dual occ/semi-detached, statewide R2) */
  STAGE1_ZONE: 'R2' as const,

  /**
   * LGAs excluded from Stage 1 statewide dual occupancy provisions.
   * Lowercase, no punctuation for matching.
   */
  STAGE1_EXCLUDED_LGAS: [
    'blue mountains',
    'hawkesbury',
    'wollondilly',
    'bathurst regional',
  ] as const,

  /**
   * LGAs within the four Stage 2 designated regions.
   * Greater Sydney, Central Coast, Lower Hunter/Newcastle, Illawarra-Shoalhaven.
   * Lowercase for case-insensitive matching against portal LGA names.
   */
  STAGE2_REGION_LGAS: [
    // Greater Sydney
    'bayside', 'blacktown', 'blue mountains', 'burwood', 'camden', 'campbelltown',
    'canada bay', 'canterbury-bankstown', 'canterbury bankstown', 'cumberland',
    'fairfield', 'georges river', 'the hills', 'hills shire', 'hornsby',
    "hunter's hill", 'hunters hill', 'inner west', 'ku-ring-gai', 'ku ring gai',
    'lane cove', 'liverpool', 'mosman', 'north sydney', 'northern beaches',
    'parramatta', 'city of parramatta', 'penrith', 'randwick', 'ryde',
    'strathfield', 'sutherland', 'sydney', 'city of sydney', 'waverley',
    'willoughby', 'wollondilly', 'woollahra',
    // Central Coast
    'central coast',
    // Lower Hunter / Newcastle
    'newcastle', 'city of newcastle', 'lake macquarie', 'cessnock', 'maitland',
    'port stephens',
    // Illawarra-Shoalhaven
    'wollongong', 'shellharbour', 'shoalhaven', 'kiama',
  ] as const,

  /** Default lot width assumption when cadastral data unavailable (meters) */
  DEFAULT_LOT_WIDTH_M: 15,

  /** Minimum lot width for dual occupancy development (meters) */
  MIN_LOT_WIDTH_DUAL_OCC_M: 12,

  /** Minimum lot area for multi-dwelling housing (square meters) */
  MIN_LOT_AREA_MULTI_DWELLING_M2: 450,
} as const;

/**
 * Apartment Design Guide (ADG) Standards
 *
 * SEPP (Housing) 2021 - Apartment Design Guide
 * @see https://www.planning.nsw.gov.au/policy-and-legislation/housing/apartment-design-guide
 */
export const ADG_STANDARDS = {
  /**
   * High-priority design criteria typically required for CDC/DA assessment
   * These are the most commonly referenced ADG standards
   */
  KEY_CRITERIA_IDS: [
    '4A-1',  // Solar and daylight access
    '4D-1',  // Apartment size and layout
    '4E-1',  // Private open space and balconies
    '4B-1',  // Natural ventilation
    '4C-1',  // Ceiling heights
    '4F-1',  // Common circulation and spaces
    '4G-1',  // Storage
    '3F-1',  // Visual privacy
  ] as const,

  /** Minimum apartment sizes (square meters, internal area) */
  MIN_APARTMENT_SIZES_M2: {
    STUDIO: 35,
    ONE_BED: 50,
    TWO_BED: 70,
    THREE_BED: 90,
  },

  /** Minimum ceiling heights (meters) */
  MIN_CEILING_HEIGHT_M: {
    HABITABLE: 2.7,
    NON_HABITABLE: 2.4,
  },
} as const;

/**
 * BASIX (Building Sustainability Index) Standards
 *
 * SEPP (Sustainable Buildings) 2022
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0698
 */
export const BASIX_STANDARDS = {
  /** Water consumption reduction target from baseline (percentage) */
  WATER_REDUCTION_PERCENT: 40,

  /** Energy reduction target for single dwelling houses (percentage) */
  ENERGY_REDUCTION_SINGLE_DWELLING_PERCENT: 50,

  /** Thermal comfort target (percentage) */
  THERMAL_COMFORT_PERCENT: 'Pass',  // Climate zone dependent
} as const;

/**
 * Pattern Book CDC Standards
 *
 * SEPP (Exempt and Complying Development Codes) 2008 - Schedule 1 (Housing Code)
 * Verified 2026-02-26 via direct clause analysis
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572
 */
export const PATTERN_BOOK_CDC = {
  /**
   * Zones eligible for the Pattern Book CDC pathway: R1, R2, R3 only — a
   * narrower set than CDC_HOUSING_CODE_ZONES (R1-R4+RU5) and deliberately not
   * merged with it (Pattern Book excludes R4). DQ-30
   * (.claude/DATA_QUALITY_TRACKER.md): previously an independent hardcoded
   * literal in `lib/pattern-book-eligibility/check-exclusions.ts`.
   */
  ELIGIBLE_ZONES: ['R1', 'R2', 'R3'] as const,

  /** Number of exclusion triggers extracted from Schedule 1 (validated database count) */
  EXCLUSION_TRIGGERS_COUNT: 32,

  /** Number of numeric design standards with extractable values (validated database count) */
  NUMERIC_STANDARDS_COUNT: 37,

  /** Number of override rules including Schedule 1 + other SEPPs (validated database count) */
  OVERRIDE_RULES_COUNT: 68,

  /** Target approval timeframe (days) */
  APPROVAL_TIMEFRAME_DAYS: 10,

  /** Source legislation */
  SOURCE: 'SEPP (Exempt and Complying Development Codes) 2008 Schedule 1',

  /** Verification date */
  VERIFIED_DATE: '2026-02-26',

  /** Extraction method */
  EXTRACTION_METHOD: 'Automated extraction with constraint validation',
} as const;

/**
 * Exempt and Complying Development Standards
 *
 * SEPP (Exempt and Complying Development Codes) 2008
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572
 */
export const EXEMPT_COMPLYING_STANDARDS = {
  /** Standard CDC approval timeframe (days) */
  CDC_APPROVAL_TIMEFRAME_DAYS: 20,

  /** Maximum building height for exempt development (meters) */
  EXEMPT_MAX_HEIGHT_M: 3,

  /** Common work types with specific standards */
  WORK_TYPES: ['deck', 'fence', 'carport', 'garage', 'pool', 'shed'] as const,
} as const;

/**
 * Development Application Timeframes
 *
 * Environmental Planning and Assessment Act 1979
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/act-1979-203
 */
export const DA_TIMEFRAMES = {
  /** Standard DA determination period (days) */
  STANDARD_DA_DAYS: 40,

  /** Typical DA processing time including delays (days) */
  TYPICAL_DA_DAYS: 60,

  /** Integrated development DA timeframe (days) */
  INTEGRATED_DA_DAYS: 90,

  /** Heritage DA typical timeframe (days) */
  HERITAGE_DA_DAYS: 90,
} as const;

/**
 * All NSW planning regulatory constants grouped by category
 */
export const NSW_PLANNING_CONSTANTS = {
  ZONES: NSW_STANDARD_ZONES,
  TOD: TOD_THRESHOLDS,
  HOUSING_SEPP: HOUSING_SEPP_LMR,
  ADG: ADG_STANDARDS,
  BASIX: BASIX_STANDARDS,
  PATTERN_BOOK: PATTERN_BOOK_CDC,
  EXEMPT_COMPLYING: EXEMPT_COMPLYING_STANDARDS,
  DA_TIMEFRAMES,
} as const;

/**
 * Type helpers for zone checking
 */
export type ResidentialZone = typeof NSW_STANDARD_ZONES.RESIDENTIAL[number];
export type ApartmentZone = typeof NSW_STANDARD_ZONES.APARTMENT_PERMITTING[number];
export type IndustrialZone = typeof NSW_STANDARD_ZONES.INDUSTRIAL[number];
export type BusinessZone = typeof NSW_STANDARD_ZONES.BUSINESS[number];

/**
 * Helper function: Check if zone permits residential development
 */
export function isResidentialZone(zone: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  return (NSW_STANDARD_ZONES.RESIDENTIAL as readonly string[]).includes(zoneCode);
}

/**
 * Standard Instrument zone families, for copy that must not assume every
 * non-residential zone is a centres/business zone (a C4 lot is not "shop-top
 * housing" country).
 *
 * - residential: R1–R5 and RU5 Village (the zones the dwelling model covers)
 * - rural: RU1–RU4, RU6
 * - conservation: C1–C4 (Standard Instrument environment/conservation zones)
 * - centres: E1/E2 (employment-scheme centres), B1–B7, MU1 — shop-top territory
 * - other: waterway, special purpose, recreation, industrial (E3–E5, IN, W, SP, RE), unknown
 */
export type ZoneFamily = 'residential' | 'rural' | 'conservation' | 'centres' | 'other';

/**
 * Helper function: Classify a zone code into its Standard Instrument family.
 * Accepts either a bare code ("C4") or a labelled zone ("C4 Environmental Living").
 */
export function zoneFamily(zone: string): ZoneFamily {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  if ((NSW_STANDARD_ZONES.RESIDENTIAL as readonly string[]).includes(zoneCode)) return 'residential';
  if (/^R\d/.test(zoneCode)) return 'residential';
  if (/^RU\d/.test(zoneCode)) return 'rural';
  if (/^C[1-4]$/.test(zoneCode)) return 'conservation';
  if (/^(E1|E2|B\d|MU\d?)$/.test(zoneCode)) return 'centres';
  return 'other';
}

/**
 * Helper function: Check if zone permits apartment development
 */
export function isApartmentZone(zone: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  return (NSW_STANDARD_ZONES.APARTMENT_PERMITTING as readonly string[]).includes(zoneCode);
}

/**
 * Helper function: Check if zone is industrial
 */
export function isIndustrialZone(zone: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  return (NSW_STANDARD_ZONES.INDUSTRIAL as readonly string[]).includes(zoneCode);
}

/**
 * Helper function: Check if property is in TOD accessible area
 * @param transportDistance Distance to nearest rail station in meters
 * @param transportType Type of transport ('heavy_rail', 'light_rail', 'metro')
 */
export function isInTODAccessibleArea(
  transportDistance: number,
  transportType: 'heavy_rail' | 'light_rail' | 'metro'
): boolean {
  if (transportType === 'heavy_rail' || transportType === 'metro') {
    return transportDistance <= TOD_THRESHOLDS.HEAVY_RAIL_WALKABLE_M;
  }
  if (transportType === 'light_rail') {
    return transportDistance <= TOD_THRESHOLDS.LIGHT_RAIL_WALKABLE_M;
  }
  return false;
}

/**
 * Helper function: Check if zone is eligible for LMR Stage 2 (full housing types)
 */
export function isLMREligibleZone(zone: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  return (HOUSING_SEPP_LMR.ELIGIBLE_ZONES as readonly string[]).includes(zoneCode);
}

/**
 * Helper function: Check if LGA is within a Stage 2 designated region
 * (Greater Sydney, Central Coast, Lower Hunter/Newcastle, Illawarra-Shoalhaven)
 */
export function isLMRStage2Region(lga: string): boolean {
  const normalised = lga.toLowerCase().replace(/[^a-z0-9 -]/g, '').trim();
  return (HOUSING_SEPP_LMR.STAGE2_REGION_LGAS as readonly string[]).some(
    eligible => normalised.includes(eligible) || eligible.includes(normalised)
  );
}

/**
 * Helper function: Check if property qualifies for any LMR provisions.
 *
 * Returns true if:
 * - Stage 2: eligible zone (R1–R4) AND LGA is in a designated Stage 2 region, OR
 * - Stage 1: R2 zone AND LGA is not excluded from statewide dual occ provisions
 */
export function isLMRApplicable(zone: string, lga: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  const normalisedLga = lga.toLowerCase().replace(/[^a-z0-9 -]/g, '').trim();

  // Stage 2: full LMR housing types in designated regions
  if (isLMREligibleZone(zone) && isLMRStage2Region(lga)) return true;

  // Stage 1: dual occ / semi-detached statewide in R2 (excluding 4 LGAs)
  if (zoneCode === HOUSING_SEPP_LMR.STAGE1_ZONE) {
    const excluded = (HOUSING_SEPP_LMR.STAGE1_EXCLUDED_LGAS as readonly string[]).some(
      ex => normalisedLga.includes(ex)
    );
    return !excluded;
  }

  return false;
}

/**
 * Low/medium residential zones where a residential flat building (apartments) is
 * permitted ONLY via the Stage-2 LMR mid-rise reforms (designated regions) — not
 * under the base Standard Instrument. Stage-1 LMR in these zones is dual-occupancy
 * only, which does NOT engage the Apartment Design Guide.
 */
const LMR_DEPENDENT_APARTMENT_ZONES = ['R1', 'R2', 'R3'] as const;

/**
 * Whether apartment / residential-flat-building development — and therefore the
 * Apartment Design Guide (SEPP Housing 2021 Part 4 / former SEPP 65) — can apply at
 * this address, based on zone and LGA rather than a blanket zone list.
 *
 * - R4 and business / mixed-use / centre zones permit apartments or shop-top housing
 *   under the Standard Instrument, so they qualify anywhere.
 * - R1–R3 qualify only where Stage-2 LMR applies (an eligible zone inside a designated
 *   region). This stops every regional R2/R3 lot (e.g. Bowral/Wingecarribee) from being
 *   treated as apartment-permitting when the mid-rise reforms do not reach it.
 *
 * Permissibility is LGA-dependent; this is a screening gate, not a substitute for the
 * LEP land-use table.
 */
export function permitsApartmentDevelopment(zone: string, lga: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  if (!(NSW_STANDARD_ZONES.APARTMENT_PERMITTING as readonly string[]).includes(zoneCode)) {
    return false;
  }
  if ((LMR_DEPENDENT_APARTMENT_ZONES as readonly string[]).includes(zoneCode)) {
    // Stage-2 applicability is LGA-scoped; without a known LGA we cannot confirm the
    // designated region, so fail closed rather than showing the ADG on an unknown lot.
    if (!lga.trim()) return false;
    return isLMREligibleZone(zone) && isLMRStage2Region(lga);
  }
  return true;
}
