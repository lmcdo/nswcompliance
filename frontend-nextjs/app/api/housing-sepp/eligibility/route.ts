import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { HousingSEPPSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

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
  pdfPageImageUrl: string | null;
}

interface EligibilityResult {
  developmentType: string;
  displayName: string;
  description: string;
  isEligible: boolean;
  eligibilityReason: string;
  standards: DevelopmentStandard[];
  effectiveDate: string;
  legislationUrl: string;
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

    const { address, zone: zoneCode, lotSize, developmentType, lga, coordinates } = validation.data;

    // Extract additional fields for compatibility
    const lotWidth = body.lotWidth;
    const stationDistance = body.stationDistance;
    const isLMRArea = body.isLMRArea;

    // Normalize zone code (e.g., "R2 Low Density Residential" -> "R2")
    const zone = zoneCode.split(' ')[0].toUpperCase();

    // Check if zone is residential
    const residentialZones = ['R1', 'R2', 'R3', 'R4'];
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
        pdf_page_image_url
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
        pdfPageImageUrl: row.pdf_page_image_url
      });
    }

    // Check eligibility for each development type
    const eligibilityResults: EligibilityResult[] = [];

    // Default to true if isLMRArea not specified (most LMR areas are residential zones)
    const inLMRArea = isLMRArea !== false;

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
          eligibilityReason: 'Property is not in an LMR reform area',
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

    return NextResponse.json({
      success: true,
      data: {
        eligibleTypes: eligibilityResults,
        propertyInfo: {
          zoneCode: zone,
          lotSize,
          lotWidth,
          stationDistance,
          isLMRArea: inLMRArea
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
