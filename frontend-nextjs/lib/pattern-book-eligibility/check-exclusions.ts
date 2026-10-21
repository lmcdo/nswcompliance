/**
 * Pattern Book Exclusion Checker
 *
 * Checks property constraints against 217 extracted SEPP exclusion triggers
 * to determine if Pattern Book CDC pathway is blocked.
 */

import { Pool } from 'pg';
import { PATTERN_BOOK_CDC } from '../regulatory-constants';

export interface PropertyConstraints {
  // From PropertyData.heritage
  heritage?: {
    isHeritage: boolean;
    heritageType?: string; // 'item' or 'conservation area'
    heritageItemName?: string;
  };

  // From PropertyData.environmental
  environmental?: {
    floodProne: boolean | null;
    /** null = the bush fire map did not answer (not checked). */
    bushfireProne: boolean | null;
    acidSulfateSoils?: string; // 'Class 1', 'Class 2', etc.
  };

  // From PropertyData.constraints
  zone?: string;
  lga?: string;

  // From PropertyData.planningLayers (need to parse)
  planningLayers?: any[];

  // From PropertyData.anefData
  anefData?: {
    anefValue?: number; // Aircraft noise exposure forecast
    /** What PropertyData.anefData actually carries (anefValue is never set by the portal client). */
    anefLevel?: number | null;
  } | null;
}

export interface ExclusionTrigger {
  exclusionType: string;
  triggered: boolean;
  reason: string;
  sourceClause?: string;
}

export interface ExclusionCheckResult {
  hasExclusions: boolean;
  triggered: ExclusionTrigger[];
  summary: string;
  /** Exclusions that could not be tested because the map did not answer. Not empty = "no exclusions" is NOT known. */
  notChecked: string[];
}

/** Exclusions whose map gave no answer: unknown is not "clear" (a failed bush fire lookup used to read as eligible). */
export function uncheckedExclusions(constraints: PropertyConstraints): string[] {
  const out: string[] = [];
  if (constraints.environmental && constraints.environmental.floodProne == null) out.push('flood_planning_area');
  if (constraints.environmental && constraints.environmental.bushfireProne == null) out.push('bushfire_prone');
  return out;
}

/**
 * Map property constraints to exclusion types that may be triggered
 */
function mapConstraintsToExclusions(constraints: PropertyConstraints): string[] {
  const potentialExclusions: string[] = [];

  // Heritage
  if (constraints.heritage?.isHeritage) {
    potentialExclusions.push('heritage');
  }

  // Flood
  if (constraints.environmental?.floodProne) {
    potentialExclusions.push('flood_planning_area');
  }

  // Bushfire
  if (constraints.environmental?.bushfireProne) {
    potentialExclusions.push('bushfire_prone');
  }

  // Acid Sulfate Soils (Class 1-4 are constraints, Class 5 is clear)
  const assClass = constraints.environmental?.acidSulfateSoils;
  if (assClass && !assClass.includes('Class 5')) {
    potentialExclusions.push('acid_sulfate_soils');
  }

  // Aircraft Noise (ANEF > 20 is a constraint)
  const anef = constraints.anefData?.anefValue ?? constraints.anefData?.anefLevel ?? null;
  if (anef != null && anef > 20) {
    potentialExclusions.push('aircraft_noise');
  }

  // TODO: Add parsing for other exclusions from planningLayers:
  // - threatened_species
  // - coastal_erosion
  // - protected_area
  // - unsewered

  return potentialExclusions;
}

/**
 * Query database for exclusion triggers matching property constraints
 */
export async function checkExclusions(
  constraints: PropertyConstraints,
  dbPool: Pool
): Promise<ExclusionCheckResult> {

  // Map property data to potential exclusion types
  const potentialExclusions = mapConstraintsToExclusions(constraints);
  const notChecked = uncheckedExclusions(constraints);
  const notCheckedNote = notChecked.length
    ? `; not checked (the government map did not answer): ${notChecked.join(', ')}`
    : '';

  if (potentialExclusions.length === 0) {
    return {
      hasExclusions: false,
      triggered: [],
      summary: 'No exclusions triggered' + notCheckedNote,
      notChecked,
    };
  }

  // Query our 217 extracted exclusion triggers
  const query = `
    SELECT DISTINCT
      exclusion_type,
      applies_to,
      source_clause,
      source_provision_text
    FROM sepp_structured_requirements
    WHERE requirement_category = 'exclusion'
      AND is_exclusion_trigger = true
      AND exclusion_type = ANY($1::text[])
      AND (applies_to = 'Pattern_Book' OR applies_to = 'all')
  `;

  const result = await dbPool.query(query, [potentialExclusions]);

  // Deduplicate by exclusion_type (we may have multiple provisions for same exclusion)
  const uniqueExclusions = new Map<string, any>();
  result.rows.forEach(row => {
    if (!uniqueExclusions.has(row.exclusion_type)) {
      uniqueExclusions.set(row.exclusion_type, row);
    }
  });

  // Build triggered exclusions with reasons
  const triggered: ExclusionTrigger[] = Array.from(uniqueExclusions.values()).map(row => {
    let reason = '';

    switch (row.exclusion_type) {
      case 'heritage':
        const isItem = constraints.heritage?.heritageType?.toLowerCase().includes('item');
        const itemName = constraints.heritage?.heritageItemName;
        const itemNumber = (constraints.heritage as any)?.heritageItemNumber;

        if (isItem && itemName) {
          reason = `Property is a Heritage Item: ${itemName}`;
        } else if (isItem && itemNumber) {
          reason = `Property is a Heritage Item (${itemNumber})`;
        } else if (itemName) {
          reason = `Property is within Heritage Conservation Area (${itemName})`;
        } else if (itemNumber) {
          reason = `Property is heritage listed (${itemNumber})`;
        } else {
          reason = 'Property has heritage constraints';
        }
        break;

      case 'flood_planning_area':
        reason = 'Property is flood prone land';
        break;

      case 'bushfire_prone':
        reason = 'Property is bushfire prone land';
        break;

      case 'acid_sulfate_soils':
        reason = `Property has acid sulfate soils: ${constraints.environmental?.acidSulfateSoils}`;
        break;

      case 'aircraft_noise':
        reason = `Property in aircraft noise zone: ${constraints.anefData?.anefValue ?? constraints.anefData?.anefLevel} ANEF`;
        break;

      default:
        reason = `Property affected by ${row.exclusion_type.replace(/_/g, ' ')}`;
    }

    return {
      exclusionType: row.exclusion_type,
      triggered: true,
      reason,
      sourceClause: row.source_clause
    };
  });

  // Generate summary
  const summary = triggered.length === 0
    ? 'No exclusions triggered'
    : `${triggered.length} exclusion(s) triggered: ${triggered.map(e => e.exclusionType).join(', ')}`;

  return {
    hasExclusions: triggered.length > 0,
    triggered,
    summary: summary + notCheckedNote,
    notChecked,
  };
}

/**
 * Helper: Check if zone is eligible for Pattern Book
 * Pattern Book only applies to R1, R2, R3 zones
 */
export function isZoneEligible(zone?: string): boolean {
  if (!zone) return false;
  return PATTERN_BOOK_CDC.ELIGIBLE_ZONES.some(z => zone.toUpperCase().includes(z));
}
