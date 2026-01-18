/**
 * CDC Setback Compliance Check API
 *
 * Compares user-input proposed setbacks against SEPP Housing 2021 CDC standards.
 * Returns pass/fail for each boundary type.
 *
 * SEPP Housing 2021 CDC Setback Standards (Clause 22):
 * - Front: 6m minimum (or prevailing building line if less)
 * - Side (ground floor): 0.9m minimum
 * - Rear: 3m minimum (single storey), 6m (two storey upper floor windows)
 */

import { NextRequest, NextResponse } from 'next/server';

// SEPP Housing 2021 CDC setback standards (meters)
// Reference: State Environmental Planning Policy (Housing) 2021, Part 3, Division 1
const CDC_SETBACK_STANDARDS = {
  // Front setback: 6m or prevailing building line, whichever is less
  front: {
    minimum: 6.0,
    description: 'Front setback to street boundary',
    allowPrevailingLine: true,
    reference: 'SEPP Housing 2021, Clause 22(a)'
  },
  // Side setback: 0.9m for ground floor
  side: {
    minimum: 0.9,
    description: 'Side setback to side boundary',
    reference: 'SEPP Housing 2021, Clause 22(b)'
  },
  side_left: {
    minimum: 0.9,
    description: 'Side setback to left boundary',
    reference: 'SEPP Housing 2021, Clause 22(b)'
  },
  side_right: {
    minimum: 0.9,
    description: 'Side setback to right boundary',
    reference: 'SEPP Housing 2021, Clause 22(b)'
  },
  // Rear setback: 3m single storey, 6m for windows of habitable rooms on upper floors
  rear: {
    minimum: 3.0,
    minimumUpperFloor: 6.0,
    description: 'Rear setback to rear boundary',
    reference: 'SEPP Housing 2021, Clause 22(c)'
  }
};

interface SetbackInput {
  front?: number;
  side?: number;
  side_left?: number;
  side_right?: number;
  rear?: number;
}

interface SetbackCheckResult {
  boundary: string;
  proposed: number;
  required: number;
  compliant: boolean;
  margin: number; // positive = excess, negative = shortfall
  reference: string;
  note?: string;
}

interface CdcSetbackCheckResponse {
  success: boolean;
  overallCompliant: boolean;
  results: SetbackCheckResult[];
  summary: string;
  disclaimer: string;
}

function checkSetback(
  boundary: keyof typeof CDC_SETBACK_STANDARDS,
  proposed: number | undefined,
  isUpperFloor: boolean = false
): SetbackCheckResult | null {
  if (proposed === undefined) return null;

  const standard = CDC_SETBACK_STANDARDS[boundary];
  if (!standard) return null;

  // Use upper floor minimum for rear if applicable
  let required = standard.minimum;
  if (boundary === 'rear' && isUpperFloor) {
    const rearStandard = CDC_SETBACK_STANDARDS.rear;
    required = rearStandard.minimumUpperFloor;
  }

  const compliant = proposed >= required;
  const margin = proposed - required;

  return {
    boundary,
    proposed,
    required,
    compliant,
    margin: Math.round(margin * 100) / 100,
    reference: standard.reference,
    note: !compliant
      ? `Shortfall of ${Math.abs(margin).toFixed(2)}m - may require variation or DA pathway`
      : margin > 0
        ? `Exceeds minimum by ${margin.toFixed(2)}m`
        : 'Meets minimum requirement'
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { setbacks, hasUpperFloorWindows } = body as {
      setbacks: SetbackInput;
      hasUpperFloorWindows?: boolean;
    };

    if (!setbacks || typeof setbacks !== 'object') {
      return NextResponse.json(
        { error: 'Setbacks object is required' },
        { status: 400 }
      );
    }

    const results: SetbackCheckResult[] = [];

    // Check each provided setback
    if (setbacks.front !== undefined) {
      const result = checkSetback('front', setbacks.front);
      if (result) results.push(result);
    }

    // Check side setbacks (generic or specific)
    if (setbacks.side !== undefined) {
      const result = checkSetback('side', setbacks.side);
      if (result) results.push(result);
    }
    if (setbacks.side_left !== undefined) {
      const result = checkSetback('side_left', setbacks.side_left);
      if (result) results.push(result);
    }
    if (setbacks.side_right !== undefined) {
      const result = checkSetback('side_right', setbacks.side_right);
      if (result) results.push(result);
    }

    // Check rear setback (upper floor consideration)
    if (setbacks.rear !== undefined) {
      const result = checkSetback('rear', setbacks.rear, hasUpperFloorWindows);
      if (result) {
        if (hasUpperFloorWindows) {
          result.note = (result.note || '') + ' (assessed for upper floor habitable rooms)';
        }
        results.push(result);
      }
    }

    if (results.length === 0) {
      return NextResponse.json(
        { error: 'At least one setback value must be provided' },
        { status: 400 }
      );
    }

    const overallCompliant = results.every(r => r.compliant);
    const failedCount = results.filter(r => !r.compliant).length;

    let summary: string;
    if (overallCompliant) {
      summary = 'All proposed setbacks comply with SEPP Housing 2021 CDC standards.';
    } else {
      const failedBoundaries = results.filter(r => !r.compliant).map(r => r.boundary);
      summary = `${failedCount} setback(s) do not meet CDC standards: ${failedBoundaries.join(', ')}. ` +
        'A Development Application may be required, or setbacks need adjustment.';
    }

    const response: CdcSetbackCheckResponse = {
      success: true,
      overallCompliant,
      results,
      summary,
      disclaimer: 'This check is based on SEPP Housing 2021 default standards. ' +
        'Actual requirements may vary based on lot characteristics, prevailing building lines, ' +
        'and council-specific controls. Always verify with a registered certifier.'
    };

    return NextResponse.json({
      ...response,
      meta: {
        timestamp: new Date().toISOString(),
        standardsApplied: 'SEPP Housing 2021, Part 3, Division 1',
        note: 'Front setback may be reduced to prevailing building line if documented'
      }
    });

  } catch (error) {
    console.error('CDC setback check error:', error);
    return NextResponse.json(
      {
        error: 'Failed to check setback compliance',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  // Return the standards for reference
  return NextResponse.json({
    success: true,
    standards: CDC_SETBACK_STANDARDS,
    usage: {
      method: 'POST',
      body: {
        setbacks: {
          front: 'number (meters)',
          side: 'number (meters) - generic side setback',
          side_left: 'number (meters) - optional specific left side',
          side_right: 'number (meters) - optional specific right side',
          rear: 'number (meters)'
        },
        hasUpperFloorWindows: 'boolean - if rear windows to habitable rooms on upper floor'
      },
      example: {
        setbacks: { front: 6, side: 1.0, rear: 4 },
        hasUpperFloorWindows: false
      }
    },
    disclaimer: 'SEPP Housing 2021 CDC standards. Actual requirements may vary.'
  });
}
