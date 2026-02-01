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


export const dynamic = 'force-dynamic';
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

    const { constraints, heritage, environmental, propertyArea, lotDimensions } = propertyData;

    // === CHECK 1: Zone eligibility ===
    checksPerformed.push('Zone');
    const zoneCode = extractZoneCode(constraints?.zone);

    if (!zoneCode) {
      warnings.push('Could not determine zone - verify zone eligibility with council');
    } else {
      const zoneCheck = isZoneCdcEligible(zoneCode);
      if (!zoneCheck.eligible) {
        exclusions.push({
          reason: `Zone ${zoneCode} can't use CDC pathway`,
          constraint: 'zone',
          severity: 'definite',
          source: 'NSW Planning Portal'
        });
      }
    }

    // === CHECK 2: Lot size (minimum 200m²) ===
    checksPerformed.push('Lot size');

    // Prefer cadastre-calculated area (more accurate), fallback to property area string
    let areaNum: number | null = null;

    if (lotDimensions?.area) {
      areaNum = lotDimensions.area;
    } else if (propertyArea) {
      const areaMatch = propertyArea.match(/[\d,]+\.?\d*/);
      if (areaMatch) {
        areaNum = parseFloat(areaMatch[0].replace(',', ''));
      }
    }

    if (areaNum !== null) {
      if (areaNum < 200) {
        exclusions.push({
          reason: `Lot is too small (${Math.round(areaNum)}m², need at least 200m²)`,
          constraint: 'lot_size',
          severity: 'definite',
          source: 'NSW Planning Portal'
        });
      }
    } else {
      warnings.push('Could not determine lot size - verify lot size meets 200m² minimum');
    }

    // === CHECK 3: Heritage exclusion ===
    checksPerformed.push('Heritage');
    if (heritage?.isHeritage) {
      // Simplify heritage type for display
      const heritageType = heritage.heritageType || '';
      const isHCA = heritageType.toLowerCase().includes('conservation area');
      const isItem = heritageType.toLowerCase().includes('item');

      let reason = 'Heritage listed';
      if (isHCA) {
        reason = 'In a heritage conservation area';
      } else if (isItem) {
        reason = 'Heritage listed property';
      }

      exclusions.push({
        reason,
        constraint: 'heritage',
        severity: 'definite',
        source: 'NSW Planning Portal'
      });
    }

    // === CHECK 4: Flood-prone land ===
    checksPerformed.push('Flood risk');
    if (environmental?.floodProne) {
      exclusions.push({
        reason: 'Flood-prone land',
        constraint: 'flood',
        severity: 'definite',
        source: 'NSW Planning Portal'
      });
    }

    // === CHECK 5: Bushfire-prone land ===
    checksPerformed.push('Bushfire risk');
    if (environmental?.bushfireProne) {
      exclusions.push({
        reason: 'Bushfire-prone land',
        constraint: 'bushfire',
        severity: 'definite',
        source: 'NSW Planning Portal'
      });
    }

    // === CHECK 6: Acid sulfate soils (Class 1-3) ===
    checksPerformed.push('Acid sulfate soils');
    if (environmental?.acidSulfateSoils) {
      const classMatch = environmental.acidSulfateSoils.match(/Class\s*([1-5])/i);
      if (classMatch) {
        const soilClass = parseInt(classMatch[1]);
        if (soilClass <= 3) {
          exclusions.push({
            reason: `Acid sulfate soil (Class ${soilClass})`,
            constraint: 'acid_sulfate',
            severity: 'likely',
            source: 'NSW Planning Portal'
          });
        }
      }
    }

    // === CHECK 7: Height compliance (if available) ===
    checksPerformed.push('Height limit');
    if (constraints?.maxHeight) {
      // CDC typically requires max 8.5m for houses
      if (constraints.maxHeight < 8.5) {
        warnings.push(`Height limit ${constraints.maxHeight}m (CDC needs 8.5m)`);
      }
    }

    // === CHECK 8: FSR compliance (if available) ===
    checksPerformed.push('Floor space ratio');
    if (constraints?.maxFsr) {
      // Very low FSR may limit CDC
      if (constraints.maxFsr < 0.3) {
        warnings.push(`Low floor space ratio (${constraints.maxFsr}:1)`);
      }
    }

    // Note: Some checks need external data we don't have

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
  const searchParams = request.nextUrl.searchParams;
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
