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
 */
export const NSW_STANDARD_ZONES = {
  /** Residential zones that permit dwelling houses and associated development */
  RESIDENTIAL: ['R1', 'R2', 'R3', 'R4', 'R5', 'RU5'] as const,

  /** Zones that permit apartment developments (including post-LMR reforms) */
  APARTMENT_PERMITTING: [
    'R1',   // General Residential - now permits low-rise apartments (LMR reforms July 2024)
    'R2',   // Low Density Residential - now permits low-rise apartments (LMR reforms July 2024)
    'R3',   // Medium Density Residential
    'R4',   // High Density Residential
    'B1',   // Neighbourhood Centre
    'B2',   // Local Centre
    'B3',   // Commercial Core
    'B4',   // Mixed Use
    'B5',   // Business Development
    'B6',   // Enterprise Corridor
    'MU1',  // Mixed Use (new naming convention)
    'E1',   // Local Centre (new naming convention)
    'E2',   // Commercial Centre (new naming convention)
  ] as const,

  /** Industrial and employment zones */
  INDUSTRIAL: ['IN1', 'IN2', 'IN3', 'E4', 'E5', 'B5', 'B6', 'B7', 'E3'] as const,

  /** Business/commercial zones */
  BUSINESS: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'E1', 'E2', 'E3', 'E4', 'E5'] as const,
} as const;

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
 * SEPP (Housing) 2021 - Division 2, Subdivision 3
 * @see https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#pt.3-div.2-sdiv.3
 */
export const HOUSING_SEPP_LMR = {
  /** Zones where LMR housing provisions apply */
  ELIGIBLE_ZONES: ['R1', 'R2', 'R3', 'R4'] as const,

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
 * Helper function: Check if zone is eligible for LMR housing
 */
export function isLMREligibleZone(zone: string): boolean {
  const zoneCode = zone.split(' ')[0]?.replace(/[^A-Z0-9]/gi, '')?.toUpperCase() || '';
  return (HOUSING_SEPP_LMR.ELIGIBLE_ZONES as readonly string[]).includes(zoneCode);
}
