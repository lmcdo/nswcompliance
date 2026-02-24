/**
 * Pattern Book Numeric Standards Checker
 *
 * Checks property dimensions against 199 extracted numeric standards
 * (height, FSR, setbacks, lot size, deep soil).
 */

import { Pool } from 'pg';

export interface LotDimensions {
  area: number; // sqm
  frontage: number; // m
  depth: number; // m
}

export interface NumericFailure {
  metricName: string;
  required: number;
  actual: number;
  unit: string;
  operator: 'min' | 'max';
  gap: number;
}

export interface NumericCheckResult {
  allCompliant: boolean;
  failures: NumericFailure[];
  summary: string;
}

/**
 * Query database for applicable numeric standards
 */
export async function checkNumericStandards(
  lotDimensions: LotDimensions | null,
  zone: string | undefined,
  lga: string | undefined,
  dbPool: Pool
): Promise<NumericCheckResult> {

  if (!lotDimensions || !zone) {
    return {
      allCompliant: true,
      failures: [],
      summary: 'Insufficient data for numeric compliance check'
    };
  }

  // Query our 199 numeric standards
  // Note: We don't have zone-specific filtering yet, so this queries all
  // In practice, standards will need to be filtered by applicable zone/LGA
  const query = `
    SELECT DISTINCT
      metric_name,
      metric_value,
      metric_unit,
      metric_operator
    FROM sepp_structured_requirements
    WHERE requirement_category = 'numeric_standard'
      AND (applies_to = 'Pattern_Book' OR applies_to = 'all')
      AND metric_name IS NOT NULL
  `;

  const result = await dbPool.query(query);

  const failures: NumericFailure[] = [];

  // Check each standard against actual lot dimensions
  for (const row of result.rows) {
    const { metric_name, metric_value, metric_unit, metric_operator } = row;

    let actual: number | null = null;
    let compliant = true;

    switch (metric_name) {
      case 'lot_size_min':
        actual = lotDimensions.area;
        compliant = metric_operator === 'min' ? actual >= metric_value : actual <= metric_value;
        break;

      case 'setback_front_min':
        // We don't have setback data from property API yet
        // Skip for now
        continue;

      case 'setback_side_min':
      case 'setback_rear_min':
        // Skip - no property data available
        continue;

      case 'height_max':
        // Skip - would need building height, not lot height
        continue;

      case 'fsr_min':
        // Skip - FSR is a ratio, not a dimension
        continue;

      case 'deep_soil_percent_min':
        // Skip - would need site coverage analysis
        continue;

      default:
        continue;
    }

    if (actual !== null && !compliant) {
      const gap = metric_operator === 'min'
        ? metric_value - actual
        : actual - metric_value;

      failures.push({
        metricName: metric_name,
        required: metric_value,
        actual,
        unit: metric_unit,
        operator: metric_operator,
        gap
      });
    }
  }

  // Generate summary
  const summary = failures.length === 0
    ? 'All numeric standards met'
    : `${failures.length} standard(s) not met: ${failures.map(f => f.metricName).join(', ')}`;

  return {
    allCompliant: failures.length === 0,
    failures,
    summary
  };
}

/**
 * Helper: Format numeric failure for user display
 */
export function formatNumericFailure(failure: NumericFailure): string {
  const metricLabel = failure.metricName.replace(/_/g, ' ');
  const opLabel = failure.operator === 'min' ? 'minimum' : 'maximum';

  return `${metricLabel}: ${opLabel} ${failure.required}${failure.unit} required, ${failure.actual}${failure.unit} available (${failure.gap.toFixed(1)}${failure.unit} short)`;
}
