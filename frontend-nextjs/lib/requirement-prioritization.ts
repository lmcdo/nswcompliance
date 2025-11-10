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
 */
export function detectDevTypeFromZone(zone?: string): string {
  if (!zone) return 'dwelling_house';

  const zoneUpper = zone.toUpperCase();

  // Residential zones (R1, R2, R3, R4, R5, etc.)
  if (zoneUpper.startsWith('R')) {
    return 'residential';
  }

  // Business/Commercial zones (B1, B2, B3, B4, etc.)
  if (zoneUpper.startsWith('B')) {
    return 'commercial';
  }

  // Industrial zones (IN1, IN2, IN3, etc.)
  if (zoneUpper.startsWith('IN')) {
    return 'industrial';
  }

  // Mixed Use (MU1)
  if (zoneUpper.startsWith('MU')) {
    return 'mixed_use';
  }

  // Default to residential for edge cases
  return 'residential';
}

/**
 * Auto-filter subdivision requirements based on lot size
 * Subdivisions require minimum 450m² (typically 2x225m²) in Inner West
 */
export function canSubdivide(propertyArea?: string | number): boolean {
  if (!propertyArea) return true; // If unknown, show subdivision requirements

  let areaSqm: number;

  if (typeof propertyArea === 'string') {
    // Parse "228.1 square metres" → 228.1
    const match = propertyArea.match(/[\d.]+/);
    if (!match) return true;
    areaSqm = parseFloat(match[0]);
  } else {
    areaSqm = propertyArea;
  }

  // Conservative: 450m² minimum for subdivision
  return areaSqm >= 450;
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
 * Group requirements by category for display
 */
export function groupByCategory(requirements: FilterableRequirement[]): Record<string, FilterableRequirement[]> {
  return requirements.reduce((acc, req) => {
    if (!acc[req.category]) acc[req.category] = [];
    acc[req.category].push(req);
    return acc;
  }, {} as Record<string, FilterableRequirement[]>);
}
