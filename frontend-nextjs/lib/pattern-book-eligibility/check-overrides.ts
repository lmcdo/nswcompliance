/**
 * Pattern Book Override Checker
 *
 * Checks if triggered exclusions can be overridden with assessments/certificates
 * using our 9 curated override rules.
 */

import { Pool } from 'pg';
import { ExclusionTrigger } from './check-exclusions';

export interface OverrideOption {
  exclusionType: string;
  canOverride: boolean;
  condition?: string; // What assessment/certificate is required
  notes?: string;
  sourceClause?: string;
}

export interface OverrideCheckResult {
  anyOverrideable: boolean;
  overrides: OverrideOption[];
  summary: string;
}

/**
 * Query database for override rules for triggered exclusions
 */
export async function checkOverrides(
  triggeredExclusions: ExclusionTrigger[],
  dbPool: Pool
): Promise<OverrideCheckResult> {

  if (triggeredExclusions.length === 0) {
    return {
      anyOverrideable: false,
      overrides: [],
      summary: 'No exclusions to override'
    };
  }

  const exclusionTypes = triggeredExclusions.map(e => e.exclusionType);

  // Query our 9 override rules
  const query = `
    SELECT
      exclusion_type,
      is_override,
      override_condition,
      ambiguity_notes,
      source_clause
    FROM sepp_structured_requirements
    WHERE requirement_category = 'override'
      AND exclusion_type = ANY($1::text[])
      AND (applies_to = 'Pattern_Book' OR applies_to = 'all')
  `;

  const result = await dbPool.query(query, [exclusionTypes]);

  // Build override options
  const overrides: OverrideOption[] = result.rows.map(row => ({
    exclusionType: row.exclusion_type,
    canOverride: row.is_override,
    condition: row.override_condition,
    notes: row.ambiguity_notes,
    sourceClause: row.source_clause
  }));

  const anyOverrideable = overrides.some(o => o.canOverride);

  // Generate summary
  const overrideableCount = overrides.filter(o => o.canOverride).length;
  const blockedCount = overrides.filter(o => !o.canOverride).length;

  let summary = '';
  if (overrideableCount > 0 && blockedCount > 0) {
    summary = `${overrideableCount} exclusion(s) can be overridden, ${blockedCount} cannot`;
  } else if (overrideableCount > 0) {
    summary = `All ${overrideableCount} exclusion(s) can be overridden with assessments`;
  } else {
    summary = `No overrides available - DA required`;
  }

  return {
    anyOverrideable,
    overrides,
    summary
  };
}

/**
 * Helper: Generate user-friendly next steps for overrides
 */
export function generateOverrideSteps(overrides: OverrideOption[]): string[] {
  const steps: string[] = [];

  const overrideable = overrides.filter(o => o.canOverride);
  const blocked = overrides.filter(o => !o.canOverride);

  // If ANY exclusion is non-overrideable, Pattern Book CDC is NOT available
  const patternBookAvailable = blocked.length === 0;

  if (blocked.length > 0) {
    // Show blockers first
    steps.push('The following exclusions CANNOT be overridden:');
    blocked.forEach(o => {
      steps.push(`  • ${o.exclusionType.replace(/_/g, ' ')}`);
    });
    steps.push('');
    steps.push('Pattern Book CDC pathway is NOT available - Development Application (DA) required');

    // If there are also overrideable exclusions, mention them for context
    if (overrideable.length > 0) {
      steps.push('');
      steps.push('Note: Some exclusions could be addressed with assessments:');
      overrideable.forEach(o => {
        if (o.condition) {
          steps.push(`  • ${o.condition} (addresses ${o.exclusionType.replace(/_/g, ' ')})`);
        }
      });
      steps.push('However, due to non-overrideable exclusions above, these assessments will not enable Pattern Book CDC');
    }
  } else if (overrideable.length > 0) {
    // All exclusions are overrideable
    steps.push('Required assessments/certificates:');
    overrideable.forEach(o => {
      if (o.condition) {
        steps.push(`  • ${o.condition}`);
      }
    });
    steps.push('');
    steps.push('Once obtained, Pattern Book CDC pathway is available (10-day approval)');
  }

  return steps;
}
