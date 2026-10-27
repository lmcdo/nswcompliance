/**
 * Requirement Prioritization - Organize by Actionability
 *
 * Splits requirements into numeric (actionable) vs qualitative (context)
 * without hiding anything - just smart organization.
 */

export interface FilterableRequirement {
  id: number;
  category: string;
  requirement_text: string;
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  section_type?: string;
  verbatim_source_text?: string;
  conditional_text?: string;
  part_number?: string;
  part_name?: string;
  section_header?: string;
  subcategory?: string;
}

export interface PrioritizedRequirements {
  numeric: FilterableRequirement[];      // Has measurable values
  qualitative: FilterableRequirement[];  // Design principles, character
  objectives: FilterableRequirement[];   // Informational only
}

export interface FilterStats {
  total: number;
  numericCount: number;
  qualitativeCount: number;
  objectivesCount: number;
  numericPercentage: string;
  filtered: {
    devType: number;
    subdivision: number;
    objectives: number;
    total: number;
  };
}

/**
 * Split requirements into actionable (numeric) vs qualitative
 */
export function prioritizeRequirements(
  requirements: FilterableRequirement[]
): PrioritizedRequirements {
  const numeric: FilterableRequirement[] = [];
  const qualitative: FilterableRequirement[] = [];
  const objectives: FilterableRequirement[] = [];

  for (const req of requirements) {
    // Objectives are purely informational
    if (req.section_type === 'objective') {
      objectives.push(req);
      continue;
    }

    // Numeric requirements have actionable values
    if (req.value_numeric != null || req.value_min != null || req.value_max != null) {
      numeric.push(req);
    } else {
      qualitative.push(req);
    }
  }

  return { numeric, qualitative, objectives };
}

/**
 * Get priority stats for UI feedback
 */
export function getPriorityStats(
  prioritized: PrioritizedRequirements,
  filterStats?: { devType: number; subdivision: number; objectives: number }
): FilterStats {
  const total = prioritized.numeric.length +
                prioritized.qualitative.length +
                prioritized.objectives.length;

  return {
    total,
    numericCount: prioritized.numeric.length,
    qualitativeCount: prioritized.qualitative.length,
    objectivesCount: prioritized.objectives.length,
    numericPercentage: ((prioritized.numeric.length / total) * 100).toFixed(1),
    filtered: {
      devType: filterStats?.devType || 0,
      subdivision: filterStats?.subdivision || 0,
      objectives: filterStats?.objectives || 0,
      total: (filterStats?.devType || 0) + (filterStats?.subdivision || 0) + (filterStats?.objectives || 0)
    }
  };
}

/**
 * Auto-detect development type from zone code
 * Returns specific development types that match the dev-type-filter expectations
 */
export function detectDevTypeFromZone(zone?: string): string {
  if (!zone) return 'dwelling_house';

  const zoneUpper = zone.toUpperCase();

  // Residential zones - differentiate by density
  if (zoneUpper.startsWith('R')) {
    // R4 = High Density Residential → residential flat buildings
    if (zoneUpper === 'R4') {
      return 'residential_flat_building';
    }
    // R3 = Medium Density Residential → multi-dwelling housing
    if (zoneUpper === 'R3') {
      return 'multi_dwelling_housing';
    }
    // R1, R2, R5 = Low Density / Large Lot → dwelling house
    return 'dwelling_house';
  }

  // Business/Commercial zones (B1, B2, B3, B4, etc.) or Employment zones (E1, E2, etc.)
  if (zoneUpper.startsWith('B') || zoneUpper.startsWith('E')) {
    return 'commercial';
  }

  // Industrial zones (IN1, IN2, IN3, etc.)
  if (zoneUpper.startsWith('IN')) {
    return 'commercial'; // Use commercial filter for industrial
  }

  // Mixed Use (MU1) or Shop Top
  if (zoneUpper.startsWith('MU')) {
    return 'shop_top_housing';
  }

  // Default to dwelling_house for unknown zones
  return 'dwelling_house';
}

/**
 * Auto-filter subdivision requirements based on lot size.
 * Hides them only when the lot is smaller than the LEP minimum lot size the lookup returned
 * (`constraints.minLotSize`, Planning Portal "Lot Size" layer). Either value unknown = show.
 * Never a typed figure: the old 450 m² was one council's number applied to every council.
 */
export function canSubdivide(propertyArea?: string | number, lepMinLotSize?: number | null): boolean {
  if (!propertyArea) return true; // If unknown, show subdivision requirements
  if (lepMinLotSize == null || !Number.isFinite(lepMinLotSize) || lepMinLotSize <= 0) return true;

  let areaSqm: number;

  if (typeof propertyArea === 'string') {
    // Parse "228.1 square metres" → 228.1
    const match = propertyArea.replace(/,/g, '').match(/[\d.]+/); // "1,200 m²" is 1200, not 1
    if (!match) return true;
    areaSqm = parseFloat(match[0]);
  } else {
    areaSqm = propertyArea;
  }

  if (!Number.isFinite(areaSqm) || areaSqm <= 0) return true;
  return areaSqm >= lepMinLotSize;
}

/**
 * Check if requirement is subdivision-related
 */
export function isSubdivisionRequirement(req: FilterableRequirement): boolean {
  const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
  const conditional = (req.conditional_text || '').toLowerCase();

  return text.includes('subdivision') ||
         text.includes('strata') ||
         conditional.includes('subdivision') ||
         conditional.includes('strata');
}

/**
 * Check if property is in a Heritage Conservation Area
 */
export function hasHeritage(heritage?: any): boolean {
  // No heritage answer at all is unknown: keep heritage requirements in view. Only a real false hides them.
  if (heritage == null) return true;
  if (typeof heritage === 'boolean') return heritage;
  if (typeof heritage !== 'object') return true; // odd old data: unknown, keep heritage rules in view
  if ('isHeritage' in heritage && heritage.isHeritage == null) return true; // not checked: keep heritage requirements in view

  return heritage.isHeritage === true ||
         !!heritage.hcaName || // unknown-ok: a named HCA is a positive answer
         (heritage.heritageItems?.length ?? 0) > 0;
}

/**
 * Check if requirement is heritage-related
 */
export function isHeritageRequirement(req: FilterableRequirement): boolean {
  const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
  const conditional = (req.conditional_text || '').toLowerCase();
  const category = (req.category || '').toLowerCase();

  return text.includes('heritage') ||
         text.includes('conservation area') ||
         text.includes('hca') ||
         conditional.includes('heritage') ||
         conditional.includes('conservation area') ||
         category.includes('heritage');
}

/**
 * Group requirements by category for display
 */
export function groupByCategory(requirements: FilterableRequirement[]): Record<string, FilterableRequirement[]> {
  return requirements.reduce((acc, req) => {
    if (!acc[req.category]) acc[req.category] = [];
    acc[req.category].push(req);
    return acc;
  }, {} as Record<string, FilterableRequirement[]>);
}
