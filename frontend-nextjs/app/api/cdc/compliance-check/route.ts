/**
 * CDC Full Compliance Check API
 *
 * Validates all user-input development details against SEPP Housing 2021
 * CDC standards. Returns per-check results with proposed vs required values.
 *
 * SEPP Housing 2021 CDC Standards (Part 3, Division 1):
 * - Front setback: 6.0m (or prevailing line) - Clause 22(a)
 * - Side setback: 0.9m - Clause 22(b)
 * - Rear setback: 3.0m (6.0m for upper floor habitable) - Clause 22(c)
 * - Site coverage: Max 50-60% (zone-dependent) - Clause 23
 * - Landscaped area: Min 30% - Clause 24
 * - Building height: Max 8.5m - Clause 21
 * - Storeys: Max 2 - Clause 21
 * - Car parking: 1-2 spaces (bedroom-dependent) - Clause 25
 */

import { NextRequest, NextResponse } from 'next/server';

// SEPP Housing 2021 CDC standards
const CDC_STANDARDS = {
  setbacks: {
    front: { minimum: 6.0, reference: 'SEPP Housing 2021, Clause 22(a)' },
    side: { minimum: 0.9, reference: 'SEPP Housing 2021, Clause 22(b)' },
    rear: {
      minimum: 3.0,
      minimumUpperFloor: 6.0,
      reference: 'SEPP Housing 2021, Clause 22(c)',
    },
  },
  siteCoverage: { maximum: 50, reference: 'SEPP Housing 2021, Clause 23' },
  landscapedArea: { minimum: 30, reference: 'SEPP Housing 2021, Clause 24' },
  buildingHeight: { maximum: 8.5, reference: 'SEPP Housing 2021, Clause 21' },
  storeys: { maximum: 2, reference: 'SEPP Housing 2021, Clause 21' },
  parking: { reference: 'SEPP Housing 2021, Clause 25' },
};

interface CdcComplianceInput {
  developmentType: string;
  setbacks: {
    front: number;
    sideLeft: number;
    sideRight: number;
    rear: number;
  };
  hasUpperFloorHabitableRooms: boolean;
  siteCoveragePercent: number;
  landscapedAreaPercent: number;
  buildingHeightMeters: number;
  storeys: number;
  parkingSpaces: number;
  bedrooms: number;
  address?: string;
}

interface ComplianceCheckResult {
  standard: string;
  proposed: number | string;
  required: number | string;
  compliant: boolean;
  margin: number | string;
  reference: string;
  unit: string;
}

/**
 * Get required parking based on bedroom count
 */
function getRequiredParking(bedrooms: number): number {
  if (bedrooms <= 2) return 1;
  return 2;
}

/**
 * Check a minimum requirement
 */
function checkMinimum(
  standard: string,
  proposed: number,
  minimum: number,
  reference: string,
  unit: string
): ComplianceCheckResult {
  const compliant = proposed >= minimum;
  const margin = Math.round((proposed - minimum) * 100) / 100;
  return {
    standard,
    proposed,
    required: `\u2265${minimum}`,
    compliant,
    margin,
    reference,
    unit,
  };
}

/**
 * Check a maximum requirement
 */
function checkMaximum(
  standard: string,
  proposed: number,
  maximum: number,
  reference: string,
  unit: string
): ComplianceCheckResult {
  const compliant = proposed <= maximum;
  const margin = Math.round((maximum - proposed) * 100) / 100;
  return {
    standard,
    proposed,
    required: `\u2264${maximum}`,
    compliant,
    margin,
    reference,
    unit,
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CdcComplianceInput;

    const {
      setbacks,
      hasUpperFloorHabitableRooms,
      siteCoveragePercent,
      landscapedAreaPercent,
      buildingHeightMeters,
      storeys,
      parkingSpaces,
      bedrooms,
    } = body;

    // Validate required fields
    if (!setbacks || typeof setbacks !== 'object') {
      return NextResponse.json(
        { error: 'Setbacks object is required' },
        { status: 400 }
      );
    }

    const results: ComplianceCheckResult[] = [];
    const recommendations: string[] = [];

    // === SETBACK CHECKS ===

    // Front setback (min 6.0m)
    const frontResult = checkMinimum(
      'Front setback',
      setbacks.front,
      CDC_STANDARDS.setbacks.front.minimum,
      CDC_STANDARDS.setbacks.front.reference,
      'm'
    );
    results.push(frontResult);
    if (!frontResult.compliant) {
      recommendations.push(
        `Increase front setback by ${Math.abs(frontResult.margin as number).toFixed(1)}m to meet 6.0m minimum`
      );
    }

    // Side left setback (min 0.9m)
    const sideLeftResult = checkMinimum(
      'Side Left setback',
      setbacks.sideLeft,
      CDC_STANDARDS.setbacks.side.minimum,
      CDC_STANDARDS.setbacks.side.reference,
      'm'
    );
    results.push(sideLeftResult);
    if (!sideLeftResult.compliant) {
      recommendations.push(
        `Increase side left setback by ${Math.abs(sideLeftResult.margin as number).toFixed(1)}m to meet 0.9m minimum`
      );
    }

    // Side right setback (min 0.9m)
    const sideRightResult = checkMinimum(
      'Side Right setback',
      setbacks.sideRight,
      CDC_STANDARDS.setbacks.side.minimum,
      CDC_STANDARDS.setbacks.side.reference,
      'm'
    );
    results.push(sideRightResult);
    if (!sideRightResult.compliant) {
      recommendations.push(
        `Increase side right setback by ${Math.abs(sideRightResult.margin as number).toFixed(1)}m to meet 0.9m minimum`
      );
    }

    // Rear setback (min 3.0m, or 6.0m if upper floor habitable)
    const rearMinimum = hasUpperFloorHabitableRooms
      ? CDC_STANDARDS.setbacks.rear.minimumUpperFloor
      : CDC_STANDARDS.setbacks.rear.minimum;
    const rearResult = checkMinimum(
      'Rear setback',
      setbacks.rear,
      rearMinimum,
      CDC_STANDARDS.setbacks.rear.reference,
      'm'
    );
    if (hasUpperFloorHabitableRooms) {
      rearResult.standard += ' (upper floor)';
    }
    results.push(rearResult);
    if (!rearResult.compliant) {
      recommendations.push(
        `Increase rear setback by ${Math.abs(rearResult.margin as number).toFixed(1)}m to meet ${rearMinimum}m minimum`
      );
    }

    // === SITE COVERAGE (max 50%) ===
    const siteCoverageResult = checkMaximum(
      'Site coverage',
      siteCoveragePercent,
      CDC_STANDARDS.siteCoverage.maximum,
      CDC_STANDARDS.siteCoverage.reference,
      '%'
    );
    results.push(siteCoverageResult);
    if (!siteCoverageResult.compliant) {
      recommendations.push(
        `Reduce site coverage by ${Math.abs(siteCoverageResult.margin as number).toFixed(0)}% to meet 50% maximum`
      );
    }

    // === LANDSCAPED AREA (min 30%) ===
    const landscapedResult = checkMinimum(
      'Landscaped area',
      landscapedAreaPercent,
      CDC_STANDARDS.landscapedArea.minimum,
      CDC_STANDARDS.landscapedArea.reference,
      '%'
    );
    results.push(landscapedResult);
    if (!landscapedResult.compliant) {
      recommendations.push(
        `Increase landscaped area by ${Math.abs(landscapedResult.margin as number).toFixed(0)}% to meet 30% minimum`
      );
    }

    // === BUILDING HEIGHT (max 8.5m) ===
    const heightResult = checkMaximum(
      'Building height',
      buildingHeightMeters,
      CDC_STANDARDS.buildingHeight.maximum,
      CDC_STANDARDS.buildingHeight.reference,
      'm'
    );
    results.push(heightResult);
    if (!heightResult.compliant) {
      recommendations.push(
        `Reduce building height by ${Math.abs(heightResult.margin as number).toFixed(1)}m to meet 8.5m maximum`
      );
    }

    // === STOREYS (max 2) ===
    const storeysResult = checkMaximum(
      'Storeys',
      storeys,
      CDC_STANDARDS.storeys.maximum,
      CDC_STANDARDS.storeys.reference,
      ''
    );
    results.push(storeysResult);
    if (!storeysResult.compliant) {
      recommendations.push(
        `Development exceeds 2 storey maximum - CDC pathway not available`
      );
    }

    // === PARKING (bedroom-dependent) ===
    const requiredParking = getRequiredParking(bedrooms);
    const parkingResult = checkMinimum(
      'Parking spaces',
      parkingSpaces,
      requiredParking,
      CDC_STANDARDS.parking.reference,
      ''
    );
    results.push(parkingResult);
    if (!parkingResult.compliant) {
      recommendations.push(
        `Provide ${requiredParking - parkingSpaces} additional parking space(s) for ${bedrooms} bedroom dwelling`
      );
    }

    // Calculate summary
    const passCount = results.filter((r) => r.compliant).length;
    const totalChecks = results.length;
    const overallCompliant = passCount === totalChecks;

    let summary: string;
    if (overallCompliant) {
      summary =
        'All proposed development standards comply with SEPP Housing 2021 CDC requirements.';
    } else {
      summary = `${totalChecks - passCount} of ${totalChecks} checks do not meet CDC standards. ` +
        'Adjustments may be required, or a Development Application pathway may be needed.';
    }

    // Add general recommendation if not compliant
    if (!overallCompliant && recommendations.length > 0) {
      recommendations.push(
        'Alternatively, lodge a Development Application instead of CDC'
      );
    }

    return NextResponse.json({
      success: true,
      overallCompliant,
      passCount,
      totalChecks,
      results,
      summary,
      recommendations,
      disclaimer:
        'This check is based on SEPP Housing 2021 default standards. ' +
        'Actual requirements may vary based on lot characteristics, zone, ' +
        'and council-specific controls. Always verify with a registered certifier.',
      meta: {
        timestamp: new Date().toISOString(),
        standardsApplied: 'SEPP Housing 2021, Part 3, Division 1',
      },
    });
  } catch (error) {
    console.error('CDC compliance check error:', error);
    return NextResponse.json(
      {
        error: 'Failed to check compliance',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

export async function GET() {
  // Return usage information
  return NextResponse.json({
    success: true,
    usage: {
      method: 'POST',
      body: {
        developmentType: 'new_dwelling | alteration | addition | secondary_dwelling',
        setbacks: {
          front: 'number (meters)',
          sideLeft: 'number (meters)',
          sideRight: 'number (meters)',
          rear: 'number (meters)',
        },
        hasUpperFloorHabitableRooms: 'boolean',
        siteCoveragePercent: 'number (0-100)',
        landscapedAreaPercent: 'number (0-100)',
        buildingHeightMeters: 'number',
        storeys: 'number (1-3)',
        parkingSpaces: 'number',
        bedrooms: 'number',
      },
      example: {
        developmentType: 'new_dwelling',
        setbacks: { front: 6.5, sideLeft: 1.2, sideRight: 0.7, rear: 3.5 },
        hasUpperFloorHabitableRooms: false,
        siteCoveragePercent: 45,
        landscapedAreaPercent: 35,
        buildingHeightMeters: 7.5,
        storeys: 2,
        parkingSpaces: 2,
        bedrooms: 4,
      },
    },
    standards: CDC_STANDARDS,
    disclaimer: 'SEPP Housing 2021 CDC standards. Actual requirements may vary.',
  });
}
