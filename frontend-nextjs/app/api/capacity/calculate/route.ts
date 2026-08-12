import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { CapacityCalculationSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import { fetchDcpControls, DcpControlRow } from '@/lib/dcp-controls-client';

interface SetbackResult {
  type: 'numeric' | 'prevailing' | 'precinct_specific' | 'not_available' | 'mixed';
  front?: number;
  side?: number;
  rear?: number;
  message?: string;
  method?: string;
  minimum_standards?: any;
  source?: string;
  precinct_name?: string;
  guidance?: Array<{
    boundary: string;
    text: string;
  }>;
  values?: Array<any>;
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate request data with Zod
    const validation = validateRequest(CapacityCalculationSchema, body);

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

    const { lotSize: lotArea, frontage, zone, fsr, heightLimit, developmentType } = validation.data;

    // Extract additional fields that aren't in the schema but are still used
    const address = body.address || 'Unknown';
    const coordinates = body.coordinates;
    const lga = body.lga || 'Unknown';
    const formerCouncil = body.formerCouncil || 'Unknown';

    // Normalize LGA to title case
    const normalizedLGA = lga.split(' ').map((w: string) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');

    const pool = getPool();

    // 1. Get LEP height and FSR controls with PDF citations
    const lepControlsQuery = `
      SELECT
        ldc.clause_number,
        ldc.clause_title,
        ldc.requirements,
        ldc.applies_to_zones,
        rp.pdf_page,
        rp.pdf_printed_page,
        rp.pdf_page_image_url
      FROM lep_development_type_clauses ldc
      LEFT JOIN regulatory_provisions rp ON ldc.source_provision_id = rp.id
      WHERE ldc.lga = $1
        AND (ldc.development_type = $2 OR ldc.applies_to_zones::jsonb ? $3)
      ORDER BY ldc.clause_number
    `;

    const lepResult = await pool.query(lepControlsQuery, [normalizedLGA, developmentType, zone]);

    console.log('LEP clauses with PDF info:', JSON.stringify(lepResult.rows.map(r => ({
      clause: r.clause_number,
      pdf_page: r.pdf_page,
      pdf_page_image_url: r.pdf_page_image_url,
      source_provision_id: r.source_provision_id
    })), null, 2));

    // Extract max GFA, height from LEP clauses
    let maxGFAFromClause: number | null = null;
    let maxHeight: number | null = null;
    let maxFSR: number | null = null;

    for (const clause of lepResult.rows) {
      if (clause.requirements) {
        for (const req of clause.requirements) {
          // Parse "Maximum gross floor area of 60m²"
          const gfaMatch = req.match(/(\d+)\s*m²/i);
          if (gfaMatch && req.toLowerCase().includes('maximum') && req.toLowerCase().includes('floor area')) {
            maxGFAFromClause = parseInt(gfaMatch[1]);
          }

          // Parse "Maximum height of 9m"
          const heightMatch = req.match(/(\d+\.?\d*)\s*m/i);
          if (heightMatch && req.toLowerCase().includes('height')) {
            maxHeight = parseFloat(heightMatch[1]);
          }

          // Parse "Maximum FSR of 0.5:1"
          const fsrMatch = req.match(/(\d+\.?\d*)\s*:\s*1/);
          if (fsrMatch && req.toLowerCase().includes('fsr')) {
            maxFSR = parseFloat(fsrMatch[1]);
          }
        }
      }
    }

    // 2. Calculate max GFA from FSR if available
    let maxGFAFromFSR: number | null = null;
    if (maxFSR && lotArea) {
      maxGFAFromFSR = lotArea * maxFSR;
    }

    // 3-5. DCP-derived slices — Item 5 consolidation: ONE call to the guarded
    // implementation (/pipeline/dcp-controls; is_current strict, needs_review
    // excluded, ZONE filter now applied via the zone param — previously
    // omitted, and the old inline parking/landscaping queries returned an
    // arbitrary LIMIT 3 with no ORDER BY. All guarded rows are now served in
    // the source's deterministic order.)
    const dcpProxy = await fetchDcpControls(formerCouncil, zone);
    const dcpRows: DcpControlRow[] =
      (dcpProxy.available && dcpProxy.rows ? dcpProxy.rows : []).filter(
        (r) => r.dev_type === developmentType || r.dev_type === 'universal_residential',
      );

    const setbacks = await getSetbacks(
      zone, formerCouncil, address, normalizedLGA, dcpRows, coordinates, developmentType,
    );

    const PARKING_TYPES = new Set(
      ['car_parking', 'bicycle_parking', 'driveway_width', 'driveway_gradient']);
    const LANDSCAPING_TYPES = new Set(
      ['landscaping_min', 'deep_soil_min', 'tree_canopy_min',
       'communal_open_space_min', 'private_open_space']);

    const parkingRows = dcpRows.filter((r) => PARKING_TYPES.has(r.semantic_type));
    const landscapingRows = dcpRows.filter((r) => LANDSCAPING_TYPES.has(r.semantic_type));

    // Calculate total buildable GFA
    let maxBuildableGFA = null;
    let gfaSource = '';

    if (maxGFAFromClause) {
      maxBuildableGFA = maxGFAFromClause;
      gfaSource = 'LEP dev-type clause limit';
    } else if (maxGFAFromFSR) {
      maxBuildableGFA = maxGFAFromFSR;
      gfaSource = 'FSR calculation';
    }

    // Calculate approximate storeys from height
    let approxStoreys = null;
    if (maxHeight) {
      approxStoreys = Math.floor(maxHeight / 3.0); // Assume 3m per storey
    }

    return NextResponse.json({
      success: true,
      capacity: {
        maxGFA: maxBuildableGFA,
        gfaSource: gfaSource,
        maxHeight: maxHeight,
        maxFSR: maxFSR,
        approxStoreys: approxStoreys,
        lotArea: lotArea
      },
      setbacks: setbacks,
      // DQ-32, user ruling 2026-08-13: SHOW THEM ALL, each with the condition
      // that distinguishes it.
      //
      // Both of these already returned every row. What they dropped was
      // `notes` — the condition text — so four correct Sutherland parking rates
      // arrived as 1, 1.5, 2 and 0.25 with nothing saying which is one-bedroom,
      // two-bedroom, three-plus or visitor. Several bare numbers for one slot
      // is not more information than one number; it is less, because the reader
      // cannot tell which line applies to them and has no way to find out.
      //
      // 556 of the 562 rows measured in ambiguous groups already carry this
      // text (bedrooms 220, visitor/resident 121, lot size 108, locality 95,
      // zone 56, storeys 55). The data was never the problem. `setbacks` above
      // has always passed it through as `condition`; these two are brought into
      // line with it, same field names, so consumers handle one shape.
      parking: parkingRows.map(row => ({
        text: row.source_text ?? row.requirement,
        spaces: row.value_min,
        conditional: Boolean((row.notes ?? '').trim()),
        condition: row.notes || null
      })),
      landscaping: landscapingRows.map(row => ({
        text: row.source_text ?? row.requirement,
        value: row.value_min,
        unit: row.unit,
        conditional: Boolean((row.notes ?? '').trim()),
        condition: row.notes || null,
        partName: row.source_chapter_key,
        pdfPage: row.pdf_page,
        pdfPageImageUrl: null
      })),
      lepClauses: lepResult.rows.map(row => ({
        clause_number: row.clause_number,
        clause_title: row.clause_title,
        requirements: row.requirements,
        pdfPage: row.pdf_page,
        pdfPrintedPage: row.pdf_printed_page,
        pdfPageImageUrl: row.pdf_page_image_url
      }))
    });

  } catch (error) {
    console.error('Capacity calculation error:', error);
    return NextResponse.json({
      success: false,
      error: 'Failed to calculate development capacity',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}

async function getSetbacks(
  zone: string,
  formerCouncil: string,
  address: string,
  lga: string,
  dcpRows: DcpControlRow[],
  coordinates?: { lat: number; lng: number },
  devType: string = 'dwelling_house'
): Promise<SetbackResult> {
  // STRATEGY: Precinct-specific → General provisions → Guidance fallback
  // This cascade ensures users get the most specific data available

  const pool = getPool();

  // ========================================================================
  // STEP 1: Check for precinct-specific setbacks (MOST SPECIFIC)
  // ========================================================================
  // Precinct-specific setbacks override general provisions
  // Use spatial filtering if coordinates are available
  let precinctResult;

  if (coordinates) {
    // Spatial query: Find precinct containing this coordinate, then get its requirements
    const spatialPrecinctQuery = `
      SELECT precinct_id, precinct_name
      FROM dcp_precinct_boundaries
      WHERE lga = $1
        AND ST_Contains(boundary, ST_SetSRID(ST_MakePoint($2, $3), 4326))
      LIMIT 1
    `;

    const precinctMatch = await pool.query(spatialPrecinctQuery, [lga, coordinates.lng, coordinates.lat]);

    if (precinctMatch.rows.length > 0) {
      const precinctId = precinctMatch.rows[0].precinct_id;

      // Get requirements for this specific precinct
      const requirementsQuery = `
        SELECT
          precinct_name,
          requirement_text,
          value_numeric,
          value_min,
          value_max,
          unit,
          subcategory,
          has_conditionals,
          conditional_text
        FROM dcp_precinct_requirements
        WHERE precinct_id = $1
          AND requirement_text ILIKE '%setback%'
        ORDER BY
          CASE WHEN value_numeric IS NOT NULL THEN 1 ELSE 2 END,
          subcategory
        LIMIT 10
      `;

      precinctResult = await pool.query(requirementsQuery, [precinctId]);
    } else {
      precinctResult = { rows: [] };
    }
  } else {
    // No coordinates - skip precinct filtering
    precinctResult = { rows: [] };
  }

  if (precinctResult.rows.length > 0) {
    // Found precinct-specific setbacks
    const setbacksByType: any = {
      type: 'precinct_specific',
      precinct_name: precinctResult.rows[0].precinct_name,
      source: `${formerCouncil} DCP Precinct Controls`,
      values: [],
      guidance: []
    };

    for (const row of precinctResult.rows) {
      const boundaryType = row.subcategory?.toLowerCase() ||
                          (row.requirement_text.toLowerCase().includes('front') ? 'front' :
                           row.requirement_text.toLowerCase().includes('side') ? 'side' :
                           row.requirement_text.toLowerCase().includes('rear') ? 'rear' : 'other');

      if (row.value_numeric) {
        // Numeric setback
        setbacksByType.values.push({
          boundary: boundaryType,
          value: row.value_numeric,
          unit: row.unit || 'm',
          conditional: row.has_conditionals,
          condition: row.conditional_text,
          text: row.requirement_text
        });
      } else if (row.value_min || row.value_max) {
        // Range setback
        setbacksByType.values.push({
          boundary: boundaryType,
          range: `${row.value_min || '?'}-${row.value_max || '?'}${row.unit || 'm'}`,
          text: row.requirement_text
        });
      } else {
        // Text guidance only
        setbacksByType.guidance.push({
          boundary: boundaryType,
          text: row.requirement_text
        });
      }
    }

    return setbacksByType;
  }

  // ========================================================================
  // STEP 2: Check general provisions (ZONE + COUNCIL SPECIFIC)
  // ========================================================================
  // Item 5 consolidation: these rows now come pre-guarded from the ONE
  // implementation (/pipeline/dcp-controls) via the caller — is_current
  // strict, needs_review excluded, zone filter applied, deterministic order.
  // The old LIMIT 15 is gone: all guarded setback rows are served, numeric
  // first (preserving the old values-before-guidance ordering).
  const SETBACK_TYPES = new Set(
    ['front_setback', 'side_setback', 'rear_setback', 'separation_from_dwelling']);
  const generalRows = dcpRows
    .filter((r) => SETBACK_TYPES.has(r.semantic_type))
    .sort((a, b) => {
      const numA = a.value_min != null || a.value_max != null ? 1 : 2;
      const numB = b.value_min != null || b.value_max != null ? 1 : 2;
      if (numA !== numB) return numA - numB;
      return a.semantic_type.localeCompare(b.semantic_type);
    });

  if (generalRows.length > 0) {
    // Found general setbacks
    const setbacksByType: any = {
      type: 'mixed',  // Contains both numeric and guidance
      source: `${formerCouncil} DCP ${generalRows[0].source_chapter_key || 'General Controls'}`,
      values: [],
      guidance: []
    };

    for (const row of generalRows) {
      const rowText = row.source_text ?? row.requirement ?? '';
      const boundaryType =
        row.semantic_type.replace('_setback', '').toLowerCase() ||
        (rowText.toLowerCase().includes('front') ? 'front' :
         rowText.toLowerCase().includes('side') ? 'side' :
         rowText.toLowerCase().includes('rear') ? 'rear' : 'other');

      // != null, not truthiness: a permitted ZERO-metre setback is a valid
      // numeric control, not absent guidance (Sol, 2026-08-04).
      if (row.value_min != null) {
        // Numeric setback
        setbacksByType.values.push({
          boundary: boundaryType,
          value: row.value_min,
          unit: row.unit || 'm',
          conditional: Boolean((row.notes ?? '').trim()),
          condition: row.notes || null,
          text: rowText
        });
      } else if (row.value_max != null) {
        // Range setback (value_min absent — show the bounded side)
        setbacksByType.values.push({
          boundary: boundaryType,
          range: `?-${row.value_max}${row.unit || 'm'}`,
          text: rowText
        });
      } else {
        // Text guidance only
        setbacksByType.guidance.push({
          boundary: boundaryType,
          text: rowText
        });
      }
    }

    return setbacksByType;
  }

  // ========================================================================
  // STEP 3: Fallback to general guidance (LEAST SPECIFIC)
  // ========================================================================
  // No specific data available - provide character-based guidance
  if (formerCouncil.toLowerCase().includes('marrickville')) {
    return {
      type: 'prevailing',
      message: 'Marrickville uses character-based setbacks',
      method: 'Setbacks must match prevailing street pattern',
      guidance: [
        { boundary: 'front', text: 'Match predominant building line on your street' },
        { boundary: 'side', text: 'Minimum 900mm (heritage/character areas)' },
        { boundary: 'rear', text: 'Maintain useable back garden for outdoor activities' }
      ]
    };
  } else if (formerCouncil.toLowerCase().includes('ashfield')) {
    return {
      type: 'prevailing',
      message: 'Ashfield uses character-based setbacks',
      method: 'Setbacks determined by neighbourhood character',
      guidance: [
        { boundary: 'front', text: 'Match prevailing building line established by adjoining and nearby houses' },
        { boundary: 'side', text: 'Minimum 900mm for dwelling houses' },
        { boundary: 'rear', text: 'Maintain useable back garden' }
      ]
    };
  } else if (formerCouncil.toLowerCase().includes('leichhardt')) {
    return {
      type: 'prevailing',
      message: 'Leichhardt uses neighbourhood-specific setbacks',
      method: 'Setbacks vary by neighbourhood character',
      guidance: [
        { boundary: 'front', text: 'Match prevailing setback pattern in your neighbourhood' },
        { boundary: 'side', text: 'Typically 1m-3m depending on neighbourhood' },
        { boundary: 'rear', text: 'Maintain useable outdoor space' }
      ]
    };
  } else if (formerCouncil.toLowerCase().includes('sydney') || formerCouncil.toLowerCase().includes('city_of_sydney')) {
    return {
      type: 'prevailing',
      message: 'City of Sydney uses map-based setbacks (Building Setback and Alignment Map)',
      method: 'Front setback per Building Setbacks Map; side/rear consistent with adjoining buildings',
      guidance: [
        { boundary: 'front', text: 'Consistent with Building Setbacks Map or predominant street setting' },
        { boundary: 'side', text: 'Relate to established development pattern (heritage areas)' },
        { boundary: 'rear', text: 'Consistent with adjoining buildings; adopt adjacent or average rear setback' }
      ]
    };
  }

  // Unknown council - generic guidance
  return {
    type: 'not_available',
    message: `Setback data not yet available for ${formerCouncil}`,
    method: 'Refer to DCP provisions or contact Council'
  };
}
// Updated 2025-11-03: Removed zone_setback_rules table dependency
