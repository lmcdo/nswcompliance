/**
 * CDC Preliminary Eligibility Check API
 *
 * Phase 5 of Rule-Based Provision Enrichment Plan.
 *
 * Performs exclusion-based screening for Complying Development Certificate (CDC) pathway.
 * Returns definite exclusions (property cannot use CDC) or preliminary eligibility
 * (may be eligible, needs professional verification).
 *
 * NOTE: This is NOT a formal CDC assessment. It identifies properties that are
 * definitively EXCLUDED from CDC pathway based on available data.
 */

import { NextRequest, NextResponse } from 'next/server';
import { PropertyDataService } from '@/lib/property-data';

// CDC-eligible residential zones
const CDC_ELIGIBLE_ZONES = [
  'R1', 'R2', 'R3', 'R4',  // Residential zones
  'RU5',                    // Village zone
  'B1', 'B2',              // Some business zones (limited CDC)
];

// Zone patterns that exclude CDC
const CDC_EXCLUDED_ZONE_PATTERNS = [
  /^E[1-4]$/,  // Environmental zones
  /^RE1$/,     // Public recreation
  /^SP[1-3]$/, // Special purpose zones
  /^W[1-3]$/,  // Waterway zones
  /^RU[1-4]$/, // Rural zones (except RU5)
  /^IN[1-4]$/, // Industrial zones (general residential CDC excluded)
];

interface CdcExclusion {
  reason: string;
  constraint: string;
  severity: 'definite' | 'likely';
  source: string;
}

interface CdcCheckResult {
  eligible: 'yes' | 'no' | 'maybe';
  exclusions: CdcExclusion[];
  warnings: string[];
  checksPerformed: string[];
  disclaimer: string;
}

/**
 * Extract zone code from zone description
 * e.g., "R2 Low Density Residential" -> "R2"
 */
function extractZoneCode(zoneDescription: string | null | undefined): string | null {
  if (!zoneDescription) return null;

  // Pattern: code at start, optionally followed by description
  const match = zoneDescription.match(/^([A-Z]+[0-9]*)/);
  return match ? match[1] : null;
}

/**
 * Check if zone is CDC-eligible
 */
function isZoneCdcEligible(zoneCode: string): { eligible: boolean; reason?: string } {
  // Check if zone is in eligible list
  if (CDC_ELIGIBLE_ZONES.some(z => zoneCode.startsWith(z))) {
    return { eligible: true };
  }

  // Check if zone matches excluded patterns
  for (const pattern of CDC_EXCLUDED_ZONE_PATTERNS) {
    if (pattern.test(zoneCode)) {
      return {
        eligible: false,
        reason: `Zone ${zoneCode} is not eligible for residential CDC`
      };
    }
  }

  // Unknown zone - can't confirm
  return {
    eligible: false,
    reason: `Zone ${zoneCode} eligibility could not be confirmed`
  };
}

/**
 * Perform CDC eligibility checks against property constraints
 */
async function performCdcChecks(address: string): Promise<CdcCheckResult> {
  const exclusions: CdcExclusion[] = [];
  const warnings: string[] = [];
  const checksPerformed: string[] = [];

  try {
    // Fetch property data
    const propertyData = await PropertyDataService.getPropertyComplianceData(address);

    const { constraints, heritage, environmental, propertyArea } = propertyData;

    // === CHECK 1: Zone eligibility ===
    checksPerformed.push('Zone eligibility');
    const zoneCode = extractZoneCode(constraints?.zone);

    if (!zoneCode) {
      warnings.push('Could not determine zone - verify zone eligibility with council');
    } else {
      const zoneCheck = isZoneCdcEligible(zoneCode);
      if (!zoneCheck.eligible) {
        exclusions.push({
          reason: zoneCheck.reason || `Zone ${zoneCode} not CDC-eligible`,
          constraint: 'zone',
          severity: 'definite',
          source: 'NSW Planning Portal'
        });
      }
    }

    // === CHECK 2: Lot size (minimum 200m²) ===
    checksPerformed.push('Minimum lot size (200m²)');
    if (propertyArea) {
      // Parse area - may be "450 m²" or "450m²" or just "450"
      const areaMatch = propertyArea.match(/[\d,]+\.?\d*/);
      if (areaMatch) {
        const areaNum = parseFloat(areaMatch[0].replace(',', ''));
        if (areaNum < 200) {
          exclusions.push({
            reason: `Lot size ${areaNum}m² is below 200m² minimum`,
            constraint: 'lot_size',
            severity: 'definite',
            source: 'NSW Planning Portal'
          });
        }
      }
    } else {
      warnings.push('Could not determine lot size - verify lot size meets 200m² minimum');
    }

    // === CHECK 3: Heritage exclusion ===
    checksPerformed.push('Heritage item exclusion');
    if (heritage?.isHeritage) {
      const heritageType = heritage.heritageType || 'Heritage item';
      exclusions.push({
        reason: `Property is a ${heritageType}`,
        constraint: 'heritage',
        severity: 'definite',
        source: 'NSW Planning Portal'
      });
    }

    // === CHECK 4: Flood-prone land ===
    checksPerformed.push('Flood-prone land exclusion');
    if (environmental?.floodProne) {
      exclusions.push({
        reason: 'Property is identified as flood-prone land',
        constraint: 'flood',
        severity: 'definite',
        source: 'NSW Planning Portal'
      });
    }

    // === CHECK 5: Bushfire-prone land ===
    checksPerformed.push('Bushfire-prone land exclusion');
    if (environmental?.bushfireProne) {
      exclusions.push({
        reason: 'Property is identified as bushfire-prone land',
        constraint: 'bushfire',
        severity: 'definite',
        source: 'NSW Planning Portal'
      });
    }

    // === CHECK 6: Acid sulfate soils (Class 1-3) ===
    checksPerformed.push('Acid sulfate soils check');
    if (environmental?.acidSulfateSoils) {
      const classMatch = environmental.acidSulfateSoils.match(/Class\s*([1-5])/i);
      if (classMatch) {
        const soilClass = parseInt(classMatch[1]);
        if (soilClass <= 3) {
          exclusions.push({
            reason: `Acid sulfate soils Class ${soilClass} requires specific management`,
            constraint: 'acid_sulfate',
            severity: 'likely',
            source: 'NSW Planning Portal'
          });
        }
      }
    }

    // === CHECK 7: Height compliance (if available) ===
    checksPerformed.push('Height standard check');
    if (constraints?.maxHeight) {
      // CDC typically requires max 8.5m for houses
      if (constraints.maxHeight < 8.5) {
        warnings.push(`Maximum height ${constraints.maxHeight}m may limit CDC dwelling types`);
      }
    }

    // === CHECK 8: FSR compliance (if available) ===
    checksPerformed.push('FSR standard check');
    if (constraints?.maxFsr) {
      // Very low FSR may limit CDC
      if (constraints.maxFsr < 0.3) {
        warnings.push(`Low FSR ${constraints.maxFsr}:1 may limit development options`);
      }
    }

    // === CHECKS NOT POSSIBLE (need external data) ===
    warnings.push('Cannot verify: registered easements (requires NSW LRS)');
    warnings.push('Cannot verify: site slope >18 degrees (requires elevation data)');
    warnings.push('Cannot verify: existing dwelling count on lot');

    // Determine final eligibility
    const definiteExclusions = exclusions.filter(e => e.severity === 'definite');

    let eligible: 'yes' | 'no' | 'maybe';
    if (definiteExclusions.length > 0) {
      eligible = 'no';
    } else if (exclusions.length > 0 || warnings.length > 3) {
      eligible = 'maybe';
    } else {
      eligible = 'maybe'; // Never say 'yes' - always needs professional verification
    }

    return {
      eligible,
      exclusions,
      warnings,
      checksPerformed,
      disclaimer: 'This is a preliminary indicator only. It does not replace a formal CDC assessment by a registered certifier. Always verify constraints with the relevant council and engage a professional for any development application.'
    };

  } catch (error) {
    // Return error state
    return {
      eligible: 'maybe',
      exclusions: [],
      warnings: [
        `Could not retrieve property data: ${error instanceof Error ? error.message : 'Unknown error'}`,
        'Manual verification required'
      ],
      checksPerformed: [],
      disclaimer: 'Property data unavailable. Professional assessment required.'
    };
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { address } = body;

    if (!address) {
      return NextResponse.json(
        { error: 'Address is required' },
        { status: 400 }
      );
    }

    const result = await performCdcChecks(address);

    return NextResponse.json({
      success: true,
      data: result,
      meta: {
        timestamp: new Date().toISOString(),
        address,
        source: 'NSW Planning Portal'
      }
    });

  } catch (error) {
    console.error('CDC check error:', error);
    return NextResponse.json(
      {
        error: 'Failed to perform CDC eligibility check',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const address = searchParams.get('address');

  if (!address) {
    return NextResponse.json(
      {
        error: 'Address query parameter is required',
        example: '/api/cdc/preliminary-check?address=123 Main St, Sydney NSW 2000'
      },
      { status: 400 }
    );
  }

  const result = await performCdcChecks(address);

  return NextResponse.json({
    success: true,
    data: result,
    meta: {
      timestamp: new Date().toISOString(),
      address,
      source: 'NSW Planning Portal'
    }
  });
}
