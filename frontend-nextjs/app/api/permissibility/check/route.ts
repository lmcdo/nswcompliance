import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { NSWPlanningPortalService } from '@/lib/nsw-planning-portal';
import { determineFormerCouncilArea } from '@/lib/inner-west-mapping-v2';
import fs from 'fs';
import path from 'path';
import { ComplianceCheckSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

// Load development type mappings
function getDevTypeMappings() {
  const mappingsPath = path.join(process.cwd(), 'config', 'development-type-mappings.json');
  const mappingsContent = fs.readFileSync(mappingsPath, 'utf-8');
  return JSON.parse(mappingsContent);
}

// Normalize dev type from UI to LEP terminology
function normalizeDevTypeToLEP(uiType: string): string {
  const mappings = getDevTypeMappings();
  const lepType = mappings.ui_to_lep[uiType];

  if (!lepType) {
    console.warn(`No LEP mapping for dev type: ${uiType}, using as-is`);
    return uiType;
  }

  return lepType;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request data with Zod
    const validation = validateRequest(ComplianceCheckSchema, body);

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

    const { address, zone: userZone, developmentType, lga: userLga, coordinates, lotSize, frontage } = validation.data;

    // 1. Get property details from Planning Portal
    const propertyData = await NSWPlanningPortalService.getPropertyComplianceData(address);

    if (!propertyData) {
      return NextResponse.json({
        success: false,
        error: 'Property not found in NSW Planning Portal'
      }, { status: 404 });
    }

    const { constraints } = propertyData;

    // Use validated zone if provided, otherwise use from property data
    const zone = userZone || constraints.zone;  // e.g., "R2"
    // Normalize LGA to title case (Planning Portal returns "INNER WEST", DB has "Inner West")
    const lga = userLga || (constraints.lga
      ? constraints.lga.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
      : null);
    const formerCouncil = determineFormerCouncilArea(address, lga ?? '');

    // 2. Normalize dev type to LEP terminology
    const lepDevType = normalizeDevTypeToLEP(developmentType);

    console.log(`[Permissibility Check] Address: ${address}, Zone: ${zone}, Dev Type: ${lepDevType}`);

    // 3. Check LEP Land Use Table
    const permissibilityResult = await query(`
      SELECT permissibility, zone_name, notes
      FROM lep_land_use_table
      WHERE zone = $1
        AND lga = $2
        AND development_type = $3
    `, [zone, lga, lepDevType]);

    if (!permissibilityResult.rows.length) {
      // Development type not found in land use table = PROHIBITED
      console.log(`[Permissibility Check] ${lepDevType} not found in land use table for ${zone} - PROHIBITED`);

      // Find alternative options
      const alternatives = await query(`
        SELECT DISTINCT development_type
        FROM lep_land_use_table
        WHERE zone = $1
          AND lga = $2
          AND permissibility IN ('permitted', 'permissible')
        ORDER BY development_type
        LIMIT 10
      `, [zone, lga]);

      return NextResponse.json({
        success: false,
        permitted: false,
        zone: zone,
        zone_name: `${zone} Zone`,
        lga: lga,
        formerCouncil: formerCouncil,
        reason: `${lepDevType.replace(/_/g, ' ')} is prohibited in ${zone} zone`,
        alternative_options: alternatives.rows.map((r: any) => r.development_type)
      });
    }

    const permissibility = permissibilityResult.rows[0];

    if (permissibility.permissibility === 'prohibited') {
      // Explicitly prohibited
      const alternatives = await query(`
        SELECT DISTINCT development_type
        FROM lep_land_use_table
        WHERE zone = $1
          AND lga = $2
          AND permissibility IN ('permitted', 'permissible')
        ORDER BY development_type
        LIMIT 10
      `, [zone, lga]);

      return NextResponse.json({
        success: false,
        permitted: false,
        zone: zone,
        zone_name: permissibility.zone_name,
        lga: lga,
        formerCouncil: formerCouncil,
        reason: `${lepDevType.replace(/_/g, ' ')} is prohibited in ${zone} zone`,
        alternative_options: alternatives.rows.map((r: any) => r.development_type)
      });
    }

    // 4. Get LEP dev-type-specific clauses
    const lepClauses = await query(`
      SELECT clause_number, clause_title, requirements, applies_to_zones
      FROM lep_development_type_clauses
      WHERE lga = $1
        AND (development_type = $2 OR applies_to_zones::jsonb ? $3)
    `, [lga, lepDevType, zone]);

    console.log(`[Permissibility Check] Found ${lepClauses.rows.length} LEP clauses for ${lepDevType}`);

    // 5. Get general LEP controls (height, FSR) - coming from constraints
    const generalControls = {
      max_height: constraints.maxHeight,
      max_fsr: constraints.maxFsr
    };

    // 6. Get DCP section info
    const dcpSections = await query(`
      SELECT category, subcategory, COUNT(*) as requirement_count
      FROM dcp_general_requirements
      WHERE lga = $1
        AND ($2 = ANY(development_types) OR development_types IS NULL)
      GROUP BY category, subcategory
      ORDER BY requirement_count DESC
      LIMIT 10
    `, [lga, developmentType]);

    const summary = generateSummary(
      permissibility,
      lepClauses.rows,
      generalControls
    );

    return NextResponse.json({
      success: true,
      permitted: true,
      permissibility: permissibility.permissibility,
      zone: zone,
      zone_name: permissibility.zone_name,
      lga: lga,
      formerCouncil: formerCouncil,
      lep_controls: {
        general: generalControls,
        dev_type_specific: lepClauses.rows
      },
      dcp_sections: dcpSections.rows,
      summary: summary,
      notes: permissibility.notes
    });

  } catch (error) {
    console.error('Permissibility check error:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to check permissibility',
      details: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

function generateSummary(
  permissibility: any,
  lepClauses: any[],
  generalControls: any
): string {
  const devTypeDisplay = permissibility.development_type
    ? permissibility.development_type.replace(/_/g, ' ')
    : 'This development';

  if (permissibility.permissibility === 'permitted') {
    let summary = `${devTypeDisplay} are PERMITTED with consent in ${permissibility.zone_name}.`;

    if (lepClauses.length > 0) {
      summary += ` See LEP Clause ${lepClauses[0].clause_number} for specific controls.`;
    }

    if (generalControls.max_height) {
      summary += ` Max height: ${generalControls.max_height}m.`;
    }

    if (generalControls.max_fsr) {
      summary += ` Max FSR: ${generalControls.max_fsr}:1.`;
    }

    return summary;
  } else if (permissibility.permissibility === 'permissible') {
    let summary = `${devTypeDisplay} are PERMISSIBLE in ${permissibility.zone_name} (requires development consent and assessment).`;

    if (lepClauses.length > 0) {
      summary += ` See LEP Clause ${lepClauses[0].clause_number} for specific controls.`;
    }

    return summary;
  }

  return `Check permissibility status for ${devTypeDisplay} in ${permissibility.zone_name}.`;
}
