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
      console.log(`[Permissibility Check] ${lepDevType} not found in land use table for ${zone} / ${lga}`);

      // Coverage gate: only conclude prohibition when the zone/LGA table is complete.
      const coverageResult = await query(`
        SELECT is_complete FROM lep_zone_coverage WHERE zone = $1 AND lga = $2
      `, [zone, lga]);

      const isCovered =
        coverageResult.rows.length > 0 && coverageResult.rows[0].is_complete === true;

      if (!isCovered) {
        // Incomplete data — cannot determine permissibility either way.
        return NextResponse.json({
          success: false,
          permitted: null,
          coverage_incomplete: true,
          zone,
          lga,
          reason: `LEP land use table for ${zone} zone / ${lga} is not yet complete — cannot determine permissibility for ${lepDevType.replace(/_/g, ' ')}`
        }, { status: 422 });
      }

      // Zone is covered. Check whether "any other development" catch-all is permitted.
      const catchAllResult = await query(`
        SELECT permissibility FROM lep_land_use_table
        WHERE zone = $1 AND lga = $2 AND development_type = 'any_other_development'
      `, [zone, lga]);

      const catchAllPermissibility = catchAllResult.rows[0]?.permissibility;

      if (catchAllPermissibility === 'permitted') {
        // Not explicitly listed, but falls under "any other development not specified" → permitted with consent.
        return NextResponse.json({
          success: true,
          permitted: true,
          permissibility: 'permitted',
          zone,
          zone_name: `${zone} Zone`,
          lga,
          formerCouncil,
          source: 'catch_all',
          notes: `${lepDevType.replace(/_/g, ' ')} is not specifically listed — permitted under "any other development not specified in item 2 or 4"`,
          summary: `${lepDevType.replace(/_/g, ' ')} is permitted with consent in ${zone} zone (catch-all clause).`,
          lep_controls: { general: { max_height: constraints.maxHeight, max_fsr: constraints.maxFsr }, dev_type_specific: [] },
          dcp_sections: [],
        });
      }

      // Catch-all is prohibited (e.g. RE1, W1, SP1/SP2 zones) or absent.
      const alternatives = await query(`
        SELECT DISTINCT development_type
        FROM lep_land_use_table
        WHERE zone = $1
          AND lga = $2
          AND permissibility = 'permitted'
        ORDER BY development_type
        LIMIT 10
      `, [zone, lga]);

      return NextResponse.json({
        success: false,
        permitted: false,
        zone,
        zone_name: `${zone} Zone`,
        lga,
        formerCouncil,
        reason: `${lepDevType.replace(/_/g, ' ')} is not listed and the zone does not permit unlisted development — effectively prohibited in ${zone} zone`,
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
          AND permissibility = 'permitted'
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

    // 6. Get DCP section info from regulatory_provisions (authoritative table)
    // Uses former_council + v2_topic grouping. dcp_general_requirements is legacy (false positives).
    const dcpSections = await query(`
      SELECT v2_topic AS category,
             NULL AS subcategory,
             COUNT(*) AS requirement_count
      FROM regulatory_provisions
      WHERE former_council = $1
        AND v2_is_actionable = true
        AND is_current = TRUE
        AND (v2_applicable_dev_types IS NULL
             OR array_length(v2_applicable_dev_types, 1) IS NULL
             OR $2 = ANY(v2_applicable_dev_types))
      GROUP BY v2_topic
      ORDER BY requirement_count DESC
      LIMIT 10
    `, [formerCouncil, developmentType]);

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
