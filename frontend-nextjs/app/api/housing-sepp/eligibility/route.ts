import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { HousingSEPPSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import { HOUSING_SEPP_LMR } from '@/lib/regulatory-constants';

/**
 * Housing SEPP Eligibility API
 * Returns development standards for Low/Mid-Rise housing types
 * with full provenance and compliance status
 *
 * POST /api/housing-sepp/eligibility
 * Body: { address, zone, lotSize, developmentType, lga?, coordinates? }
 */

interface DevelopmentStandard {
  standardType: string;
  numericValue: number;
  unit: string;
  sourceClause: string;
  sourceProvisionId: number | null;
  effectiveDate: string;
  pdfUrl: string | null;
  pdfPage: number | null;
}

interface EligibilityResult {
  developmentType: string;
  displayName: string;
  description: string;
  isEligible: boolean;
  /**
   * Three states, because `isEligible: false` alone cannot say WHY.
   *
   * The first pass at DQ-31 fixed the INPUT (an absent isLMRArea no longer means
   * "yes") and left the OUTPUT two-state — so a property whose LMR status was
   * never assessed came back with the same `isEligible: false` as one confirmed
   * outside a reform area. A consumer rendering the boolean would tell the user
   * "not eligible" about a check that never ran, which is the same defect in the
   * opposite direction.
   *
   * `isEligible` is kept and unchanged so existing consumers do not break;
   * 'not_assessed' is additive and a consumer can adopt it when ready.
   */
  assessmentStatus: 'eligible' | 'ineligible' | 'not_assessed';
  eligibilityReason: string;
  standards: DevelopmentStandard[];
  effectiveDate: string;
  legislationUrl: string;
}

interface SeppLepOverride {
  developmentType: string;
  displayName: string;
  metric: string;
  seppValue: number;
  lepValue: number;
  seppWins: boolean;
  unit: string;
  sourceClause: string;
  note: string;
}

// Human-readable names for development types
// Terminology includes common names used by homeowners, developers, and professionals
const DEVELOPMENT_TYPE_NAMES: Record<string, { name: string; description: string }> = {
  dual_occupancy: {
    name: 'Dual Occupancy (Duplex)',
    description: 'Two homes on one block — attached side-by-side, or detached (e.g., house + granny flat)'
  },
  manor_house: {
    name: 'Manor House',
    description: 'A building containing 3-4 homes designed to look like a large single house'
  },
  multi_dwelling: {
    name: 'Multi-Dwelling Housing (Townhouses/Villas)',
    description: 'Multiple occupancy with 3 or more homes — includes townhouses, villas, and villa units'
  },
  multi_dwelling_housing: {
    name: 'Multi-Dwelling Housing (Townhouses/Villas)',
    description: 'Multiple occupancy with 3 or more homes — includes townhouses, villas, and villa units'
  },
  terraces: {
    name: 'Terrace Housing (Row Houses)',
    description: 'Row of attached homes, each with its own street entrance — traditional terrace style'
  },
  terrace_house: {
    name: 'Terrace Housing (Row Houses)',
    description: 'Row of attached homes, each with its own street entrance — traditional terrace style'
  },
  residential_flat_r1r2: {
    name: 'Low-Rise Apartments (R1/R2 Zones)',
    description: 'Apartment buildings now permitted in low density residential zones under LMR reforms'
  },
  residential_flat_r3r4_inner: {
    name: 'Mid-Rise Apartments (Near Station)',
    description: 'Up to 6-storey apartments within 400m of a train station — Transit Oriented Development'
  },
  residential_flat_r3r4_outer: {
    name: 'Mid-Rise Apartments (Near Station)',
    description: 'Up to 4-storey apartments 400-800m from a train station — Transit Oriented Development'
  },
  secondary_dwelling: {
    name: 'Secondary Dwelling (Granny Flat)',
    description: 'A self-contained dwelling on the same lot as a principal dwelling — max 60m² floor area'
  }
};

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body = await request.json();

    // Validate request data with Zod
    const validation = validateRequest(HousingSEPPSchema, body);

    if (!validation.success) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request data',
          details: formatValidationErrors(validation.details),
        },
        { status: 400 }
      );
    }

    const { zoneCode, lotSize, lotWidth, stationDistance, isLMRArea, address, lga, coordinates } = validation.data;

    // Optional LEP values for SEPP-LEP override detection
    const lepHeight: number | null = typeof body.lepHeight === 'number' ? body.lepHeight : null;
    const lepFsr: number | null = typeof body.lepFsr === 'number' ? body.lepFsr : null;

    // Normalize zone code (e.g., "R2 Low Density Residential" -> "R2")
    const zone = zoneCode.split(' ')[0].toUpperCase();

    // Check if zone is residential.
    // DQ-30 (.claude/DATA_QUALITY_TRACKER.md): this exact value is also
    // HOUSING_SEPP_LMR.ELIGIBLE_ZONES — consolidated (was independently
    // declared here; also a separate, independent reimplementation of the
    // same eligibility check as services/housing_sepp_eligibility.py, which
    // this route does not call — flagged as a further consolidation
    // candidate, not resolved in this pass).
    const residentialZones = HOUSING_SEPP_LMR.ELIGIBLE_ZONES as readonly string[];
    if (!residentialZones.includes(zone)) {
      return NextResponse.json({
        success: true,
        data: {
          eligibleTypes: [],
          message: `Zone ${zone} is not a residential zone. Housing SEPP LMR reforms apply to R1, R2, R3, and R4 zones only.`,
          propertyInfo: { zoneCode: zone, lotSize, lotWidth, stationDistance, isLMRArea }
        },
        metadata: {
          processingTimeMs: Date.now() - startTime,
          timestamp: new Date().toISOString()
        }
      });
    }

    // Fetch all standards from database
    const pool = getPool();
    const result = await pool.query(`
      SELECT
        development_type,
        standard_type,
        numeric_value,
        unit,
        applicable_zones,
        requires_lmr_area,
        source_clause,
        source_provision_id,
        source_document,
        legislation_url,
        effective_date,
        pdf_page,
        r2_pdf_url
      FROM housing_sepp_standards
      ORDER BY development_type, standard_type
    `);

    // Group standards by development type
    const standardsByType: Record<string, DevelopmentStandard[]> = {};
    const developmentTypeInfo: Record<string, {
      applicableZones: string[];
      requiresLMR: boolean;
      effectiveDate: string;
      legislationUrl: string;
    }> = {};

    for (const row of result.rows) {
      const devType = row.development_type;

      if (!standardsByType[devType]) {
        standardsByType[devType] = [];
        developmentTypeInfo[devType] = {
          applicableZones: row.applicable_zones || residentialZones,
          requiresLMR: row.requires_lmr_area,
          effectiveDate: row.effective_date,
          legislationUrl: row.legislation_url
        };
      }

      standardsByType[devType].push({
        standardType: row.standard_type,
        numericValue: parseFloat(row.numeric_value),
        unit: row.unit,
        sourceClause: row.source_clause,
        sourceProvisionId: row.source_provision_id,
        effectiveDate: row.effective_date,
        pdfUrl: row.r2_pdf_url ?? null,
        pdfPage: row.pdf_page ?? null
      });
    }

    // Check eligibility for each development type
    const eligibilityResults: EligibilityResult[] = [];

    // DQ-31. This used to read `const inLMRArea = isLMRArea !== false`, i.e. an
    // ABSENT input meant "yes, this property is in an LMR reform area" — the
    // single most consequential input to the whole endpoint, assumed in the
    // claimant's favour whenever nobody supplied it. services/housing_sepp_
    // eligibility.py was written specifically to replace this logic and names it
    // in its docstring as "a silent over-eligibility bug"; that service computes
    // the gate from the live 776 exclusion layer and fails CONSERVATIVE
    // (ineligible) on any query failure.
    //
    // Three states, matching that service's contract:
    //   true      caller confirmed the property is in an LMR area
    //   false     caller confirmed it is not
    //   undefined NOT ASSESSED — must not be read as either
    //
    // An unassessed gate now yields "cannot confirm" for the forms that depend on
    // it, never "eligible". Telling someone they can build when they cannot is
    // the expensive direction of this error.
    const lmrAreaKnown = typeof isLMRArea === 'boolean';
    const inLMRArea = isLMRArea === true;

    for (const [devType, standards] of Object.entries(standardsByType)) {
      const typeInfo = developmentTypeInfo[devType];
      const displayInfo = DEVELOPMENT_TYPE_NAMES[devType] || { name: devType, description: '' };

      // Check zone applicability
      const zoneApplicable = typeInfo.applicableZones.includes(zone);
      if (!zoneApplicable) {
        continue; // Skip types not applicable to this zone
      }

      // Check LMR area requirement
      const lmrRequired = typeInfo.requiresLMR;

      if (lmrRequired && !inLMRArea) {
        eligibilityResults.push({
          developmentType: devType,
          displayName: displayInfo.name,
          description: displayInfo.description,
          isEligible: false,
          // Not-assessed and confirmed-outside are both ineligible here, but they
          // are not the same statement and must not read the same to a user — in
          // the reason OR in the machine-readable status.
          assessmentStatus: lmrAreaKnown ? 'ineligible' : 'not_assessed',
          eligibilityReason: lmrAreaKnown
            ? 'Property is not in an LMR reform area'
            : 'LMR reform area not assessed for this property — this is not a '
              + 'finding that the property is outside one. Confirm the LMR area '
              + 'status to complete this check.',
          standards,
          effectiveDate: typeInfo.effectiveDate,
          legislationUrl: typeInfo.legislationUrl
        });
        continue;
      }

      // Check lot size
      const minLotSize = standards.find(s => s.standardType === 'min_lot_size');
      if (minLotSize && lotSize < minLotSize.numericValue) {
        eligibilityResults.push({
          developmentType: devType,
          displayName: displayInfo.name,
          description: displayInfo.description,
          isEligible: false,
          assessmentStatus: 'ineligible',
          eligibilityReason: `Lot size ${lotSize}m² is below minimum ${minLotSize.numericValue}m² (Clause ${minLotSize.sourceClause})`,
          standards,
          effectiveDate: typeInfo.effectiveDate,
          legislationUrl: typeInfo.legislationUrl
        });
        continue;
      }

      // Check lot width
      const minLotWidth = standards.find(s => s.standardType === 'min_lot_width');
      if (minLotWidth && lotWidth < minLotWidth.numericValue) {
        eligibilityResults.push({
          developmentType: devType,
          displayName: displayInfo.name,
          description: displayInfo.description,
          isEligible: false,
          assessmentStatus: 'ineligible',
          eligibilityReason: `Lot width ${lotWidth}m is below minimum ${minLotWidth.numericValue}m (Clause ${minLotWidth.sourceClause})`,
          standards,
          effectiveDate: typeInfo.effectiveDate,
          legislationUrl: typeInfo.legislationUrl
        });
        continue;
      }

      // Check TOD distance for RFB types
      if (devType.includes('residential_flat_r3r4')) {
        if (!stationDistance) {
          eligibilityResults.push({
            developmentType: devType,
            displayName: displayInfo.name,
            description: displayInfo.description,
            isEligible: false,
            // No distance supplied means the TOD test never ran. A mechanical
            // patch had marked this 'ineligible', which asserts a negative
            // determination from a check that did not happen.
            assessmentStatus: 'not_assessed',
            eligibilityReason: 'Distance to station required for TOD eligibility check',
            standards,
            effectiveDate: typeInfo.effectiveDate,
            legislationUrl: typeInfo.legislationUrl
          });
          continue;
        }

        // Check if station distance matches the zone
        const isInner = stationDistance <= 400;
        const isOuter = stationDistance > 400 && stationDistance <= 800;

        if (devType === 'residential_flat_r3r4_inner' && !isInner) {
          continue; // Not in inner zone
        }
        if (devType === 'residential_flat_r3r4_outer' && !isOuter) {
          continue; // Not in outer zone
        }
        if (stationDistance > 800) {
          eligibilityResults.push({
            developmentType: devType,
            displayName: displayInfo.name,
            description: displayInfo.description,
            isEligible: false,
            assessmentStatus: 'ineligible',
            eligibilityReason: `Property is ${stationDistance}m from station (max 800m for TOD benefits)`,
            standards,
            effectiveDate: typeInfo.effectiveDate,
            legislationUrl: typeInfo.legislationUrl
          });
          continue;
        }
      }

      // All checks passed - eligible
      eligibilityResults.push({
        developmentType: devType,
        displayName: displayInfo.name,
        description: displayInfo.description,
        isEligible: true,
        assessmentStatus: 'eligible',
        eligibilityReason: 'Meets minimum lot size and width requirements',
        standards,
        effectiveDate: typeInfo.effectiveDate,
        legislationUrl: typeInfo.legislationUrl
      });
    }

    // Sort: eligible first, then by development type
    eligibilityResults.sort((a, b) => {
      if (a.isEligible !== b.isEligible) {
        return a.isEligible ? -1 : 1;
      }
      return a.displayName.localeCompare(b.displayName);
    });

    // SEPP-LEP override detection: compare Housing SEPP standards against LEP values
    // Rule: SEPP standard applies UNLESS LEP is MORE GENEROUS (higher height/FSR favours applicant)
    const overrides: SeppLepOverride[] = [];
    if (lepHeight !== null || lepFsr !== null) {
      for (const [devType, standards] of Object.entries(standardsByType)) {
        const typeInfo = developmentTypeInfo[devType];
        if (!typeInfo.applicableZones.includes(zone)) continue;

        const displayInfo = DEVELOPMENT_TYPE_NAMES[devType] || { name: devType, description: '' };

        for (const std of standards) {
          if (std.standardType === 'max_height' && lepHeight !== null) {
            const seppVal = std.numericValue;
            if (seppVal > lepHeight) {
              overrides.push({
                developmentType: devType,
                displayName: displayInfo.name,
                metric: 'max_height',
                seppValue: seppVal,
                lepValue: lepHeight,
                seppWins: true,
                unit: 'm',
                sourceClause: std.sourceClause,
                note: `SEPP Housing allows ${seppVal}m vs LEP ${lepHeight}m for ${displayInfo.name}`,
              });
            }
          }
          if (std.standardType === 'max_fsr' && lepFsr !== null) {
            const seppVal = std.numericValue;
            if (seppVal > lepFsr) {
              overrides.push({
                developmentType: devType,
                displayName: displayInfo.name,
                metric: 'max_fsr',
                seppValue: seppVal,
                lepValue: lepFsr,
                seppWins: true,
                unit: ':1',
                sourceClause: std.sourceClause,
                note: `SEPP Housing allows ${seppVal}:1 vs LEP ${lepFsr}:1 for ${displayInfo.name}`,
              });
            }
          }
        }
      }
    }

    return NextResponse.json({
      success: true,
      data: {
        eligibleTypes: eligibilityResults,
        overrides: overrides.length > 0 ? overrides : null,
        propertyInfo: {
          zoneCode: zone,
          lotSize,
          lotWidth,
          stationDistance,
          isLMRArea: inLMRArea,
          lepHeight,
          lepFsr,
        },
        totalChecked: eligibilityResults.length,
        eligibleCount: eligibilityResults.filter(r => r.isEligible).length
      },
      metadata: {
        processingTimeMs: Date.now() - startTime,
        timestamp: new Date().toISOString(),
        source: 'housing_sepp_standards table'
      }
    });

  } catch (error) {
    console.error('[Housing SEPP Eligibility API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
