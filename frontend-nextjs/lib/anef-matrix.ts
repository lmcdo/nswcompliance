/**
 * ANEF (Australian Noise Exposure Forecast) Building Acceptability Matrix
 *
 * Deterministic lookup table for building acceptability based on ANEF zones.
 * Source: AS 2021-2015 Acoustics - Aircraft noise intrusion
 *
 * NO AI/LLM INVOLVED - Pure lookup table
 */

export interface ANEFAcceptability {
  residential: 'acceptable' | 'conditional' | 'unacceptable';
  commercial: 'acceptable' | 'conditional' | 'unacceptable';
  conditions?: string[];
  notes?: string;
}

/**
 * ANEF Acceptability Matrix
 * Key: ANEF zone level (20, 25, 30, 35, 40)
 */
const ANEF_MATRIX: Record<number, ANEFAcceptability> = {
  20: {
    residential: 'acceptable',
    commercial: 'acceptable',
    notes: 'Acceptable for all building types'
  },
  25: {
    residential: 'conditional',
    commercial: 'acceptable',
    conditions: [
      'Acoustic design required per AS 2021-2015',
      'Building construction must achieve indoor noise criteria',
      'Disclosure required in sales/lease contracts'
    ],
    notes: 'Residential requires acoustic treatment'
  },
  30: {
    residential: 'conditional',
    commercial: 'acceptable',
    conditions: [
      'Acoustic design required per AS 2021-2015',
      'Enhanced building construction standards',
      'Mandatory disclosure in all contracts',
      'Council may require noise impact assessment'
    ],
    notes: 'Residential development discouraged but not prohibited'
  },
  35: {
    residential: 'unacceptable',
    commercial: 'conditional',
    conditions: [
      'Residential development generally not permitted',
      'Commercial buildings require acoustic treatment',
      'Specific approval from council required',
      'Noise management plan mandatory'
    ],
    notes: 'Strong discouragement of residential development'
  },
  40: {
    residential: 'unacceptable',
    commercial: 'conditional',
    conditions: [
      'Residential development prohibited',
      'Commercial buildings heavily restricted',
      'Ministerial approval may be required',
      'Comprehensive noise impact assessment mandatory'
    ],
    notes: 'Highly restricted development zone'
  }
};

/**
 * Get ANEF acceptability for a given zone level
 *
 * @param anefLevel - ANEF zone (20, 25, 30, 35, 40+)
 * @returns Acceptability assessment or null if ANEF level not in matrix
 */
export function getANEFAcceptability(anefLevel: number | null): ANEFAcceptability | null {
  if (!anefLevel || anefLevel < 20) {
    return null; // Below ANEF 20 = no aircraft noise impact
  }

  // Round to nearest 5
  const roundedLevel = Math.min(Math.round(anefLevel / 5) * 5, 40);

  return ANEF_MATRIX[roundedLevel] || null;
}

/**
 * Format ANEF acceptability as human-readable text
 *
 * @param anefLevel - ANEF zone level
 * @param developmentType - 'residential' or 'commercial'
 * @returns Formatted description with conditions
 */
export function formatANEFAcceptability(
  anefLevel: number | null,
  developmentType: 'residential' | 'commercial' = 'residential'
): string {
  const acceptability = getANEFAcceptability(anefLevel);

  if (!acceptability) {
    return 'No ANEF restrictions apply (below ANEF 20 threshold)';
  }

  const status = acceptability[developmentType];
  const conditions = acceptability.conditions || [];

  let result = `**ANEF ${anefLevel} - ${developmentType.charAt(0).toUpperCase() + developmentType.slice(1)} Development: ${status.toUpperCase()}**\n\n`;

  if (status === 'acceptable') {
    result += 'Development is generally acceptable with standard controls.';
  } else if (status === 'conditional') {
    result += 'Development is conditional on meeting the following requirements:\n\n';
    conditions.forEach(condition => {
      result += `• ${condition}\n`;
    });
  } else {
    result += 'Development is generally unacceptable.\n\n';
    if (conditions.length > 0) {
      result += 'Restrictions:\n';
      conditions.forEach(condition => {
        result += `• ${condition}\n`;
      });
    }
  }

  if (acceptability.notes) {
    result += `\n*${acceptability.notes}*`;
  }

  return result.trim();
}

/**
 * Check if ANEF zone exists (property is in an aircraft noise zone)
 *
 * @param anefLevel - ANEF zone level
 * @returns true if property is in an ANEF zone (>= 20)
 */
export function hasANEFRestrictions(anefLevel: number | null): boolean {
  return anefLevel !== null && anefLevel >= 20;
}
