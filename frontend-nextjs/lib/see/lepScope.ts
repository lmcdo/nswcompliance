/**
 * lib/see/lepScope.ts
 *
 * Auto-populate WorksScopeAnswers from LEP land use table data.
 *
 * When a zone/LGA pair is confirmed complete in lep_zone_coverage, we can
 * infer WorksScopeAnswers fields = false for uses that are prohibited in that zone.
 *
 * Logic per field:
 *   - directProhibited: ALL slugs must be explicitly in the prohibited list.
 *   - classProhibited:  ANY slug in this list being prohibited triggers exclusion
 *                       (handles broad-category prohibition, e.g. "residential_accommodation").
 *   - specificPermitted: ANY of these in the permitted/exempt list overrides both triggers
 *                        (prevents false exclusions when a specific subtype is explicitly permitted).
 *
 * Fail-open: ambiguous or missing data leaves the field as null.
 * Caller must merge as lowest priority: { ...lepAutoScope, ...(worksScopeAnswers ?? {}) }
 * so user-saved answers always win.
 */

import type { WorksScopeAnswers } from './worksScope';

export interface LepPermissibilityEntry {
  development_type: string;
  permissibility: 'exempt' | 'permitted' | 'prohibited';
}

interface LepScopeGroup {
  field: keyof Omit<WorksScopeAnswers, 'heritage_elements'>;
  /**
   * ALL of these must be explicitly prohibited → triggers exclusion.
   * E.g. for has_commercial, both commercial_premises AND neighbourhood_shops
   * must be prohibited before we conclude commercial is absent.
   */
  directProhibited?: string[];
  /**
   * ANY of these being explicitly prohibited triggers exclusion.
   * Handles parent-class prohibitions like "residential_accommodation"
   * that implicitly cover sub-types not individually listed.
   */
  classProhibited?: string[];
  /**
   * ANY of these being permitted or exempt prevents exclusion.
   * Handles cases where a subtype is explicitly permitted despite a
   * parent-class prohibition (e.g. boarding_houses in E1 despite
   * residential_accommodation being prohibited).
   */
  specificPermitted: string[];
}

const LEP_SCOPE_GROUPS: LepScopeGroup[] = [
  {
    // Boarding houses explicitly prohibited (e.g. R2).
    // E1/E2/MU1 list boarding_houses as permitted → override prevents exclusion.
    field: 'has_boarding_house',
    directProhibited: ['boarding_houses'],
    specificPermitted: ['boarding_houses'],
  },
  {
    // Tourist/visitor accommodation prohibited in all residential zones (R1–R4)
    // and most commercial zones. Stays null where hotel_or_motel_accommodation
    // or backpackers are explicitly permitted (E2, MU1).
    field: 'has_tourist_accommodation',
    directProhibited: ['tourist_and_visitor_accommodation'],
    specificPermitted: [
      'tourist_and_visitor_accommodation',
      'hotel_or_motel_accommodation',
      'backpackers_accommodation',
    ],
  },
  {
    // residential_accommodation (the broad class) is prohibited in employment
    // and waterfront zones. When prohibited at the class level and no specific
    // multi-residential subtype is explicitly permitted, multi-dwelling is absent.
    // R3/R4 explicitly permit multi_dwelling_housing / residential_flat_buildings
    // → override fires correctly.
    field: 'has_multi_dwelling',
    classProhibited: ['residential_accommodation'],
    specificPermitted: [
      'multi_dwelling_housing',
      'residential_flat_buildings',
      'dual_occupancies',
      'attached_dwellings',
    ],
  },
  {
    // Both core commercial types must be prohibited. In practice no zone
    // in Inner West explicitly prohibits neighbourhood_shops without also
    // permitting commercial_premises, so this is intentionally conservative.
    field: 'has_commercial',
    directProhibited: ['commercial_premises', 'neighbourhood_shops'],
    specificPermitted: ['commercial_premises', 'neighbourhood_shops', 'shop_top_housing'],
  },
  {
    // industries (the broad class) is prohibited in residential zones (R1–R4).
    // E3/E4 explicitly permit light_industries or general_industries → stays null.
    field: 'has_industrial',
    classProhibited: ['industries'],
    specificPermitted: ['light_industries', 'general_industries', 'industries'],
  },
  {
    // home_businesses explicitly prohibited in E4, W4.
    // R2 explicitly permits home_businesses → override.
    // R1/R3/R4 permit home_industries → override.
    field: 'has_home_business',
    directProhibited: ['home_businesses'],
    specificPermitted: ['home_businesses', 'home_industries'],
  },
  {
    // Both main child-care types must be prohibited together.
    // Most zones permit centre_based_child_care_facilities → stays null.
    field: 'has_child_care',
    directProhibited: ['centre_based_child_care_facilities', 'early_education_and_care_facilities'],
    specificPermitted: [
      'centre_based_child_care_facilities',
      'early_education_and_care_facilities',
      'home_based_child_care',
    ],
  },
  {
    // land_subdivision is prohibited in all Inner West residential zones (R1–R4)
    // and most employment zones. RE1/RE2/SP zones vary — where subdivision is permitted
    // the specificPermitted override fires correctly.
    field: 'is_subdivision',
    directProhibited: ['land_subdivision'],
    specificPermitted: ['land_subdivision'],
  },
];

/**
 * Auto-populate WorksScopeAnswers from LEP permissibility entries.
 *
 * @param entries  Rows from lep_land_use_table for the zone/LGA.
 * @param covered  True when lep_zone_coverage.is_complete = true for this zone/LGA.
 * @returns Partial<WorksScopeAnswers> with false for provably-absent use types.
 *          Empty object if coverage is incomplete or entries are empty.
 */
export function autoPopulateWorksScopeFromLep(
  entries: LepPermissibilityEntry[],
  covered: boolean,
): Partial<WorksScopeAnswers> {
  if (!covered || entries.length === 0) return {};

  const prohibitedSet = new Set(
    entries.filter(e => e.permissibility === 'prohibited').map(e => e.development_type)
  );
  const permittedSet = new Set(
    entries
      .filter(e => e.permissibility === 'permitted' || e.permissibility === 'exempt')
      .map(e => e.development_type)
  );

  const result: Partial<WorksScopeAnswers> = {};

  for (const group of LEP_SCOPE_GROUPS) {
    // Step 1: check for a permitted override — if any specificPermitted slug is
    // explicitly permitted/exempt, the field cannot be auto-excluded.
    const hasPermittedOverride = group.specificPermitted.some(s => permittedSet.has(s));
    if (hasPermittedOverride) continue;

    // Step 2: check if the prohibition condition is met.
    let conditionMet = false;

    if (group.directProhibited) {
      // ALL slugs in directProhibited must be explicitly prohibited.
      conditionMet = group.directProhibited.every(s => prohibitedSet.has(s));
    }

    if (!conditionMet && group.classProhibited) {
      // ANY class-level slug being explicitly prohibited satisfies the condition.
      conditionMet = group.classProhibited.some(s => prohibitedSet.has(s));
    }

    if (conditionMet) {
      result[group.field] = false;
    }
  }

  return result;
}
