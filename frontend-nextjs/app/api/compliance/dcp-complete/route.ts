import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import { determineFormerCouncilArea } from '@/lib/inner-west-mapping-v2';
import { filterRequirementsByDevType } from '@/lib/dev-type-filter';
import { getZoneAliases } from '@/lib/zone-translation';
import { ComplianceCheckSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
// Force recompile

/**
 * DCP Complete API - Returns both general (Chapter F) and precinct-specific provisions
 *
 * This endpoint provides comprehensive DCP coverage for Inner West LGA:
 *
 * ASHFIELD:
 * - General provisions (Chapter F) filtered by zone + development type
 * - Data stored in dcp_general_provisions table
 *
 * MARRICKVILLE:
 * - Neighbourhood-based provisions (NOT filtered by zone/dev_type)
 * - Provisions apply to all properties within neighbourhood boundary
 * - Data stored in regulatory_provisions (legacy table)
 *
 * LEICHHARDT:
 * - Neighbourhood-based provisions (NOT filtered by zone/dev_type)
 * - Provisions apply to all properties within neighbourhood boundary
 * - Data stored in regulatory_provisions (legacy table)
 *
 * Geographic Filtering:
 * - Uses PostGIS spatial query on dcp_precinct_boundaries table
 * - Matches coordinates to neighbourhood/precinct boundaries
 */

interface DCPCompleteRequest {
  address?: string;
  coordinates?: {
    lat: number;
    lon: number;
  };
  zone: string;
  developmentType: string;
  lga: string;
  precinctId?: string; // Optional - can provide directly instead of spatial lookup
}

interface GeneralProvision {
  id: number;
  part_number: string;
  part_name: string;
  section_header: string;
  provision_text: string;
  ref_number: string;
  applicable_zones: string[];
  development_types: string[];
}

interface GeneralRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;  // Summary (prescriptive/actionable parts only)
  verbatim_source_text?: string;  // Exact text from PDF (for user verification)
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  has_conditionals: boolean;
  conditional_text?: string;
  confidence: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
  pdf_path?: string;
  // Phase 1: Contextual presentation fields
  part_name?: string;
  part_number?: string;
  objective?: string;
  user_category?: string;
  section_type?: string;
  priority_level?: number;
}

interface PrecinctProvision {
  id: number;
  precinct_id: string;
  precinct_name: string;
  section_header: string;
  provision_text: string;
  ref_number: string;
}

interface PrecinctRequirement {
  id: number;
  precinct_id: string;
  precinct_name: string;
  category: string;
  subcategory?: string;
  requirement_text: string;
  value_numeric?: number;
  unit?: string;
  has_conditionals: boolean;
  conditional_text?: string;
  confidence: string;
  pdf_page?: number;
  pdf_page_image_url?: string;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: DCPCompleteRequest = await request.json();

    // Validate required parameters
    const validation = validateRequest(ComplianceCheckSchema, body);

    if (!validation.success) {
      return NextResponse.json({
        success: false,
        error: 'Invalid request data',
        details: formatValidationErrors(validation.details),
      }, { status: 400 });
    }

    const { address, zone, developmentType } = validation.data;
    const { lga, coordinates, precinctId } = body;

    console.log('=== DCP Complete API ===');
    console.log('Zone:', zone);
    console.log('Development Type:', developmentType);
    console.log('LGA:', lga);
    console.log('Address:', address);

    // ========================================================================
    // STEP 0: Detect Neighbourhood/Precinct (Geographic) - FIRST
    // ========================================================================
    // This must happen BEFORE querying provisions so we know which neighbourhood to filter by

    let detectedPrecinctId: string | null = null;
    let detectedNeighbourhoodName: string | null = null;
    let formerCouncil: string | null = null;

    if (coordinates) {
      const spatialQuery = `
        SELECT precinct_id, precinct_name, former_council
        FROM dcp_precinct_boundaries
        WHERE ST_Contains(boundary, ST_SetSRID(ST_MakePoint($1, $2), 4326))
        LIMIT 1
      `;

      const spatialResult = await query(
        spatialQuery,
        [coordinates.lon, coordinates.lat]
      );

      if (spatialResult.rows.length > 0) {
        detectedPrecinctId = spatialResult.rows[0].precinct_id;
        detectedNeighbourhoodName = spatialResult.rows[0].precinct_name;
        formerCouncil = spatialResult.rows[0].former_council; // Will fall back to address parser if NULL
        console.log(`✓ Neighbourhood detected: ${detectedNeighbourhoodName} (${formerCouncil || 'former_council=NULL, will use address fallback'})`);
      } else {
        console.log('✓ No neighbourhood match - address not in any precinct/neighbourhood boundary');
      }
    }

    // Fallback: Determine council from address if no coordinates or no spatial match
    if (!formerCouncil && lga.toLowerCase().includes('inner west') && address) {
      formerCouncil = determineFormerCouncilArea(address, lga);
      if (formerCouncil) {
        console.log(`✓ Detected former council from address: ${formerCouncil}`);
      }
    }

    // Determine query parameters based on council
    let documentFilter = formerCouncil || lga;
    let queryLGA = lga;

    // All three former councils (Ashfield, Marrickville, Leichhardt) merged into Inner West LGA
    // Database stores them with lga = 'Inner West' (title case) and differentiates by former_council column
    if (formerCouncil?.toLowerCase() === 'ashfield' ||
        formerCouncil?.toLowerCase() === 'marrickville' ||
        formerCouncil?.toLowerCase() === 'leichhardt') {
      queryLGA = 'Inner West';  // Title case to match database
    } else if (formerCouncil) {
      queryLGA = formerCouncil.toUpperCase();
    }

    // Apply zone translation (E1 → [E1, B1, B2] for legacy DCPs)
    const zoneAliases = getZoneAliases(zone);
    console.log(`[DCP Complete] Zone translation: ${zone} → [${zoneAliases.join(', ')}]`);

    // ========================================================================
    // STEP 1: Query General Provisions (Chapter F) - ALWAYS
    // ========================================================================

    // Different councils have different filtering approaches:
    // - Ashfield: Zone + DevType filtering (both fields populated)
    // - Marrickville: No zone filtering (applicable_zones is NULL), filter by former_council only
    // - Leichhardt: Universal controls (no filtering)

    let generalProvisionsQuery: string;
    let generalProvisionsParams: any[];

    if (formerCouncil?.toLowerCase() === 'ashfield') {
      // Ashfield: Filter by zone, conditionally filter by devtype
      // Uses zone translation to match legacy B1/B2 zones with current E1 zone

      // Check if querying commercial zones (E1, B1, B2, etc.)
      const isCommercialZone = zoneAliases.some(z => z.startsWith('E') || z.startsWith('B'));

      if (isCommercialZone) {
        // Commercial zones: NO dev type filter (like Marrickville/Leichhardt)
        generalProvisionsQuery = `
          SELECT
            id,
            part_number,
            part_name,
            section_header,
            provision_text,
            ref_number,
            applicable_zones,
            development_types,
            display_order
          FROM dcp_general_provisions
          WHERE lga = $1
          AND applicable_zones && $2::text[]
          ORDER BY part_number, display_order
        `;
        generalProvisionsParams = [queryLGA, zoneAliases];
      } else {
        // Residential zones: Keep precise dev type filtering
        generalProvisionsQuery = `
          SELECT
            id,
            part_number,
            part_name,
            section_header,
            provision_text,
            ref_number,
            applicable_zones,
            development_types,
            display_order
          FROM dcp_general_provisions
          WHERE lga = $1
          AND applicable_zones && $2::text[]
          AND $3 = ANY(development_types)
          ORDER BY part_number, display_order
        `;
        generalProvisionsParams = [queryLGA, zoneAliases, developmentType];
      }
    } else if (formerCouncil?.toLowerCase() === 'marrickville') {
      // Marrickville: NO zone filtering (neighbourhood-based, not zone-based)
      // Note: dcp_general_provisions doesn't have former_council column
      generalProvisionsQuery = `
        SELECT
          id,
          part_number,
          part_name,
          section_header,
          provision_text,
          ref_number,
          applicable_zones,
          development_types,
          display_order
        FROM dcp_general_provisions
        WHERE lga = $1
        ORDER BY part_number, display_order
      `;
      generalProvisionsParams = [queryLGA];
    } else if (formerCouncil?.toLowerCase() === 'leichhardt') {
      // Leichhardt: Force fallback to regulatory_provisions
      // Return 0 rows to trigger fallback (no Leichhardt data in dcp_general_provisions)
      generalProvisionsQuery = `
        SELECT
          id,
          part_number,
          part_name,
          section_header,
          provision_text,
          ref_number,
          applicable_zones,
          development_types,
          display_order
        FROM dcp_general_provisions
        WHERE FALSE
      `;
      generalProvisionsParams = [];
    } else {
      // Default: Zone + DevType filtering (with zone translation for legacy DCPs)
      generalProvisionsQuery = `
        SELECT
          id,
          part_number,
          part_name,
          section_header,
          provision_text,
          ref_number,
          applicable_zones,
          development_types,
          display_order
        FROM dcp_general_provisions
        WHERE lga = $1
        AND applicable_zones && $2::text[]
        AND $3 = ANY(development_types)
        ORDER BY part_number, display_order
      `;
      generalProvisionsParams = [queryLGA, zoneAliases, developmentType];
    }

    const generalProvisions = await query(
      generalProvisionsQuery,
      generalProvisionsParams
    );

    console.log(`✓ General provisions: ${generalProvisions.rows.length}`);

    // ========================================================================
    // STEP 2: Query or Create General Requirements
    // ========================================================================

    let generalRequirements: { rows: GeneralRequirement[] } = { rows: [] };
    let precinctRequirements: PrecinctRequirement[] = []; // Declare early to avoid initialization errors
    let usedPrecinctFallback = false; // Track if fallback populated precinct requirements

    // FALLBACK: If no provisions found in new table, check old regulatory_provisions table
    // NOTE: Skip fallback for Ashfield/Marrickville (use dcp_general_requirements)
    // Leichhardt intentionally uses fallback to regulatory_provisions for universal controls
    const isInnerWestCouncil = formerCouncil?.toLowerCase() === 'ashfield' ||
                                formerCouncil?.toLowerCase() === 'marrickville';

    if (generalProvisions.rows.length === 0 && !isInnerWestCouncil) {
      console.log(`⚠ No provisions in dcp_general_provisions for ${documentFilter}`);

      let fallbackQuery: string = '';
      let fallbackParams: any[] = [];
      let fallbackResult: any = null;
      let fallbackAlreadyProcessed = false;

      if (detectedNeighbourhoodName && detectedPrecinctId) {
        // Return provisions for the specific neighbourhood + general provisions
        console.log(`  → Filtering by neighbourhood: ${detectedNeighbourhoodName}`);
        console.log(`  → Using precinct_id: ${detectedPrecinctId}`);
        console.log(`  → Plus general provisions (Parts 2, 4, 7, 8, 10)`);

        // CRITICAL FIX: For Marrickville, also fetch general provisions from regulatory_provisions
        // This ensures users see BOTH precinct-specific AND general controls (setbacks, parking, etc.)
        if (formerCouncil?.toLowerCase() === 'marrickville') {
          // Step 1: Get precinct requirements from dcp_precinct_requirements
          console.log(`  → Fetching precinct requirements for ${detectedPrecinctId}...`);
          const precinctReqQuery = `
            SELECT
              dpr.id,
              'PRECINCT_REQUIREMENT' as part_number,
              NULL as part_name,
              dpr.precinct_name as section_header,
              dpr.requirement_text as provision_text,
              dpr.precinct_id as ref_number,
              ARRAY[]::text[] as applicable_zones,
              ARRAY[]::text[] as development_types,
              0 as display_order,
              dpr.pdf_pages[1] as pdf_page,
              dpr.pdf_page_image_url,
              NULL as pdf_path,
              dpr.precinct_id as document_id,
              dpr.category as category_name
            FROM dcp_precinct_requirements dpr
            WHERE dpr.precinct_id = $1
            ORDER BY
              CASE dpr.confidence
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
              END,
              dpr.category,
              dpr.id
          `;

          const precinctReqResult = await query(precinctReqQuery, [detectedPrecinctId]);

          // Step 2: Get general provisions from regulatory_provisions (Parts 2, 4.1, 7)
          console.log(`  → Fetching general Marrickville provisions (Parts 2, 4.1, 7)...`);
          const generalProvQuery = `
            SELECT
              id,
              provision_type as part_number,
              NULL as part_name,
              section_header,
              provision_text,
              ref_number,
              ARRAY[]::text[] as applicable_zones,
              ARRAY[]::text[] as development_types,
              0 as display_order,
              pdf_page,
              pdf_page_image_url,
              pdf_source_file as pdf_path,
              document_id,
              NULL as category_name
            FROM regulatory_provisions
            WHERE document_id ILIKE $1
            AND page_number != '0'  -- Exclude TOC pages
            AND provision_text NOT LIKE '%........%'  -- Exclude TOC pages with dots
            AND NOT (provision_text ~ '^[\s\r\n]*i{1,3}[\s\r\n]+\d+\.\d+')  -- Exclude TOC starting with roman numerals
            -- v2_is_actionable not filtered: document-level PDF page query needs all provisions
            AND (
              document_id ~ '_2011_[247][_.]'  -- Parts 2, 4, 7
              OR document_id ILIKE '%_4.1_%'   -- Low density residential
              OR document_id ILIKE '%_2__1%'   -- Urban Design (Part 2.1)
              OR document_id ILIKE '%_2__10%'  -- Parking (Part 2.10)
              OR document_id ILIKE '%_2__18%'  -- Landscaping (Part 2.18)
            )
            ORDER BY pdf_page, id
          `;

          const generalProvResult = await query(generalProvQuery, [`%Marrickville%`]);

          console.log(`  → Found ${precinctReqResult.rows.length} precinct requirements`);
          console.log(`  → Found ${generalProvResult.rows.length} general provisions`);

          // For Marrickville, process precinct and general separately
          // Don't combine into fallbackResult - handle directly

          // Process precinct requirements
          precinctRequirements = precinctReqResult.rows.map((prov: any) => ({
            id: prov.id,
            precinct_id: prov.ref_number || detectedPrecinctId,
            precinct_name: prov.section_header || detectedNeighbourhoodName,
            category: prov.category_name,
            subcategory: undefined,
            requirement_text: prov.provision_text,
            value_numeric: undefined,
            unit: undefined,
            has_conditionals: false,
            conditional_text: undefined,
            confidence: 'high',
            pdf_page: prov.pdf_page,
            pdf_page_image_url: prov.pdf_page_image_url
          }));

          // Process general provisions using the mapping function
          const mapPartToCategory = (partNumber: string | null, docId: string): string => {
            if (!partNumber) {
              const marrickvilleMatch = docId.match(/_2011_(\d+(?:_\d+)?(?:\.\d+)?)/);
              if (marrickvilleMatch) {
                partNumber = marrickvilleMatch[1];
              } else {
                return 'General Provisions';
              }
            }

            // Part 2: General Development Controls
            if (partNumber.startsWith('2_1')) return 'Urban Design';
            if (partNumber.startsWith('2_10')) return 'Parking';
            if (partNumber.startsWith('2_18')) return 'Landscaping';
            if (partNumber.startsWith('2_6')) return 'Privacy';
            if (partNumber.startsWith('2_7')) return 'Solar Access';
            if (partNumber.startsWith('2_25')) return 'Stormwater';

            // Part 4: Development Types
            if (partNumber.startsWith('4.1') || partNumber.startsWith('4_1')) return 'Setbacks & Building Form';

            // Part 7: Specific Uses
            if (partNumber.startsWith('7')) return 'Specific Uses';

            return `Part ${partNumber}`;
          };

          generalRequirements = {
            rows: generalProvResult.rows.map((prov: any) => ({
              id: prov.id,
              category: mapPartToCategory(prov.part_number, prov.document_id),
              subcategory: prov.section_header,
              requirement_text: prov.provision_text,
              verbatim_source_text: prov.provision_text, // For legacy data, provision_text IS the verbatim
              value_numeric: undefined,
              value_min: undefined,
              value_max: undefined,
              unit: undefined,
              has_conditionals: false,
              conditional_text: undefined,
              confidence: 'high',
              pdf_page: prov.pdf_page,
              pdf_page_image_url: prov.pdf_page_image_url,
              pdf_path: prov.pdf_path
            }))
          };

          usedPrecinctFallback = true; // Mark as handled
          generalProvisions.rows = []; // Keep empty to avoid double processing below

          console.log(`✓ Marrickville fallback complete: ${precinctRequirements.length} precinct + ${generalRequirements.rows.length} general`);

          // Skip the rest of fallback processing for Marrickville
          fallbackAlreadyProcessed = true;
        } else {
          // Ashfield or Leichhardt: Fetch precinct + general provisions
          console.log(`  → Fetching precinct requirements for ${detectedPrecinctId}...`);

          const precinctReqQuery = `
            SELECT
              dpr.id,
              'PRECINCT_REQUIREMENT' as part_number,
              NULL as part_name,
              dpr.precinct_name as section_header,
              dpr.requirement_text as provision_text,
              dpr.precinct_id as ref_number,
              ARRAY[]::text[] as applicable_zones,
              ARRAY[]::text[] as development_types,
              0 as display_order,
              dpr.pdf_pages[1] as pdf_page,
              dpr.pdf_page_image_url,
              NULL as pdf_path,
              dpr.precinct_id as document_id,
              dpr.category as category_name
            FROM dcp_precinct_requirements dpr
            WHERE dpr.precinct_id = $1
            ORDER BY
              CASE dpr.confidence
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
              END,
              dpr.category,
              dpr.id
          `;

          const precinctReqResult = await query(precinctReqQuery, [detectedPrecinctId]);

          // Step 2: Get general provisions from regulatory_provisions
          console.log(`  → Fetching general ${formerCouncil} provisions...`);

          let generalProvQuery: string;
          if (formerCouncil?.toLowerCase() === 'ashfield') {
            // Ashfield: Look for Chapter F provisions
            generalProvQuery = `
              SELECT
                id,
                provision_type as part_number,
                NULL as part_name,
                section_header,
                provision_text,
                ref_number,
                ARRAY[]::text[] as applicable_zones,
                ARRAY[]::text[] as development_types,
                0 as display_order,
                pdf_page,
                pdf_page_image_url,
                pdf_source_file as pdf_path,
                document_id,
                NULL as category_name
              FROM regulatory_provisions
              WHERE document_id ILIKE $1
              AND page_number != '0'  -- Exclude TOC pages
              AND provision_text NOT LIKE '%........%'  -- Exclude TOC pages with dots
              AND NOT (provision_text ~ '^[\s\r\n]*i{1,3}[\s\r\n]+\d+\.\d+')  -- Exclude TOC starting with roman numerals
              -- v2_is_actionable not filtered: document-level PDF page query needs all provisions
              AND (
                document_id ILIKE '%Chapter_F%'
                OR document_id ILIKE '%Chapter F%'
              )
              ORDER BY pdf_page, id
            `;
          } else {
            // Leichhardt: Fetch general provisions from Parts A-F
            // Part structure: A=Intro, B=Access, C=Place, D=Energy, E=Water, F=Food
            // Exclude: Part C Section 2 (Distinctive Neighbourhoods) and Part G (Neighbourhoods)
            generalProvQuery = `
              SELECT
                id,
                provision_type as part_number,
                NULL as part_name,
                section_header,
                provision_text,
                ref_number,
                ARRAY[]::text[] as applicable_zones,
                ARRAY[]::text[] as development_types,
                0 as display_order,
                pdf_page,
                pdf_page_image_url,
                pdf_source_file as pdf_path,
                document_id,
                v2_topic,
                NULL as category_name
              FROM regulatory_provisions
              WHERE document_id ILIKE $1
              AND page_number != '0'  -- Exclude TOC pages
              AND provision_text NOT LIKE '%........%'  -- Exclude TOC pages with dots
              AND NOT (provision_text ~ '^[\s\r\n]*i{1,3}[\s\r\n]+\d+\.\d+')  -- Exclude TOC starting with roman numerals
              -- v2_is_actionable not filtered: document-level PDF page query needs all provisions
              AND (
                -- General Parts A, B, D, E, F
                document_id ILIKE '%Part A%'
                OR document_id ILIKE '%Part B%'
                OR document_id ILIKE '%Part D%'
                OR document_id ILIKE '%Part E%'
                OR document_id ILIKE '%Part F%'
                -- Part C Section 1 only (general place controls)
                OR document_id ILIKE '%Part C%Section 1%'
                OR document_id ILIKE '%Part C Place Section 1%'
              )
              -- Exclude Part C Section 2 (Distinctive Neighbourhoods) and Part G
              AND document_id NOT ILIKE '%Section 2%'
              AND document_id NOT ILIKE '%Part G%'
              AND document_id NOT ILIKE '%Distinctive_Neighbour%'
              ORDER BY pdf_page, id
            `;
          }

          const generalProvResult = await query(generalProvQuery, [`%${formerCouncil}%`]);

          console.log(`  → Found ${precinctReqResult.rows.length} precinct requirements`);
          console.log(`  → Found ${generalProvResult.rows.length} general provisions`);

          // Process precinct requirements
          precinctRequirements = precinctReqResult.rows.map((prov: any) => ({
            id: prov.id,
            precinct_id: prov.ref_number || detectedPrecinctId,
            precinct_name: prov.section_header || detectedNeighbourhoodName,
            category: prov.category_name,
            subcategory: undefined,
            requirement_text: prov.provision_text,
            value_numeric: undefined,
            unit: undefined,
            has_conditionals: false,
            conditional_text: undefined,
            confidence: 'high',
            pdf_page: prov.pdf_page,
            pdf_page_image_url: prov.pdf_page_image_url
          }));

          // Process general provisions using the mapping function
          // Use v2_topic preferentially if available (55% of Leichhardt provisions have it)
          const mapPartToCategory = (partNumber: string | null, docId: string, v2Topic?: string | null): string => {
            // Use v2_topic if available (enriched data from LLM categorization)
            if (v2Topic) {
              return v2Topic;
            }

            if (!partNumber) {
              // Try to extract from document_id
              if (docId.includes('Chapter_F') || docId.includes('Chapter F')) {
                // Ashfield Chapter F
                const chapterMatch = docId.match(/Part[_\s](\d+)/i);
                if (chapterMatch) {
                  partNumber = `F.${chapterMatch[1]}`;
                } else {
                  return 'General Provisions';
                }
              } else if (docId.includes('Leichhardt')) {
                const partMatch = docId.match(/Part[_\s]([A-Z])/i);
                if (partMatch) {
                  partNumber = partMatch[1];
                } else {
                  return 'General Provisions';
                }
              } else {
                return 'General Provisions';
              }
            }

            // Ashfield Chapter F parts
            if (partNumber.startsWith('F.1')) return 'Introduction & Objectives';
            if (partNumber.startsWith('F.2')) return 'Setbacks & Building Form';
            if (partNumber.startsWith('F.3')) return 'Parking & Access';
            if (partNumber.startsWith('F.4')) return 'Landscaping & Open Space';
            if (partNumber.startsWith('F.5')) return 'Heritage & Character';

            // Leichhardt general parts (mapped to meaningful categories)
            if (partNumber.startsWith('A')) return 'Administration';
            if (partNumber.startsWith('B')) return 'Access & Mobility';
            if (partNumber.startsWith('C')) return 'Place & Character';
            if (partNumber.startsWith('D')) return 'Energy & Sustainability';
            if (partNumber.startsWith('E')) return 'Water Management';
            if (partNumber.startsWith('F')) return 'Food Production';

            return `Part ${partNumber}`;
          };

          generalRequirements = {
            rows: generalProvResult.rows.map((prov: any) => ({
              id: prov.id,
              category: mapPartToCategory(prov.part_number, prov.document_id, prov.v2_topic),
              subcategory: prov.section_header,
              requirement_text: prov.provision_text,
              verbatim_source_text: prov.provision_text, // For legacy data, provision_text IS the verbatim
              value_numeric: undefined,
              value_min: undefined,
              value_max: undefined,
              unit: undefined,
              has_conditionals: false,
              conditional_text: undefined,
              confidence: 'high',
              pdf_page: prov.pdf_page,
              pdf_page_image_url: prov.pdf_page_image_url,
              pdf_path: prov.pdf_path
            }))
          };

          usedPrecinctFallback = true; // Mark as handled
          generalProvisions.rows = []; // Keep empty to avoid double processing

          if (generalProvResult.rows.length === 0) {
            console.log(`  ⚠️ No general provisions found for ${formerCouncil} (data may not be extracted yet)`);
          } else {
            const topicCount = generalProvResult.rows.filter((p: any) => p.v2_topic).length;
            console.log(`  ✅ ${formerCouncil} fallback complete: ${precinctRequirements.length} precinct + ${generalRequirements.rows.length} general (${topicCount} with v2_topic)`);
          }

          // Skip the rest of fallback processing
          fallbackAlreadyProcessed = true;
        }
      } else {
        // No neighbourhood detected - return only general provisions
        console.log(`  → No neighbourhood detected, returning general provisions only`);

        fallbackQuery = `
          SELECT
            id,
            provision_type as part_number,
            NULL as part_name,
            section_header,
            provision_text,
            ref_number,
            ARRAY[]::text[] as applicable_zones,
            ARRAY[]::text[] as development_types,
            0 as display_order,
            pdf_page,
            pdf_page_image_url,
            pdf_source_file as pdf_path,
            document_id
          FROM regulatory_provisions
          WHERE document_id ILIKE $1
          AND page_number != '0'  -- Exclude TOC pages
          AND provision_text NOT LIKE '%........%'  -- Exclude TOC pages with dots
          AND NOT (provision_text ~ '^[\s\r\n]*i{1,3}[\s\r\n]+\d+\.\d+')  -- Exclude TOC starting with roman numerals
          -- v2_is_actionable not filtered: document-level PDF page query needs all provisions
          AND (
            document_id ~ '_2011_[2478][_.]'  -- General provisions (Parts 2, 4, 7, 8) after _2011_
            OR document_id ILIKE '%_10.%'  -- Definitions
            OR document_id ILIKE '%_4.1_%' -- Low density residential
          )
          ORDER BY pdf_page, id
        `;

        fallbackParams = [`%${documentFilter}%`];
      }

      // Only execute fallback query if not already handled (Marrickville/Leichhardt path)
      if (fallbackAlreadyProcessed) {
        console.log(`✓ Fallback already processed above`);
      } else if (fallbackQuery && fallbackParams.length > 0) {
        // Only execute if query was set in one of the branches above
        fallbackResult = await query(
          fallbackQuery,
          fallbackParams
        );

        console.log(`✓ Fallback provisions: ${fallbackResult.rows.length}`);
        generalProvisions.rows = fallbackResult.rows;
      } else {
        console.log(`⚠ No fallback query configured`);
      }

      // For fallback, also create "requirements" from provisions so PDF buttons work
      // (Skip if already handled for Marrickville above)
      if (fallbackResult !== null) {
        // Map provisions to requirements format with PDF info
        // Use simple part number → category mapping for legacy Marrickville/Leichhardt data
        const mapPartToCategory = (partNumber: string | null, docId: string): string => {
        // If no part_number, extract from document_id
        if (!partNumber) {
          // Extract part from document pattern like "Marrickville_DCP_2011_9_13_Henson_Park"
          // or "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_3_2_West_Leichhardt"
          const marrickvilleMatch = docId.match(/_2011_(\d+(?:_\d+)?(?:\.\d+)?)/);
          if (marrickvilleMatch) {
            partNumber = marrickvilleMatch[1];
          } else {
            const leichMatch = docId.match(/_2013_Part_C_Section_2_(C2_2_\d+_\d+)/);
            if (leichMatch) {
              partNumber = leichMatch[1].replace(/_/g, '.');
            } else {
              return 'General Provisions';
            }
          }
        }

        // Part 2: General Development Controls
        if (partNumber.startsWith('2_1')) return 'Urban Design';
        if (partNumber.startsWith('2_3')) return 'Site Analysis';
        if (partNumber.startsWith('2_5')) return 'Access & Mobility';
        if (partNumber.startsWith('2_6')) return 'Privacy';
        if (partNumber.startsWith('2_7')) return 'Solar Access';
        if (partNumber.startsWith('2_8')) return 'Social Impact';
        if (partNumber.startsWith('2_9')) return 'Community Safety';
        if (partNumber.startsWith('2_10')) return 'Parking';
        if (partNumber.startsWith('2_11')) return 'Fencing';
        if (partNumber.startsWith('2_12')) return 'Signage';
        if (partNumber.startsWith('2_13')) return 'Biodiversity';
        if (partNumber.startsWith('2_14')) return 'Environmental Features';
        if (partNumber.startsWith('2_16')) return 'Energy Efficiency';
        if (partNumber.startsWith('2_17')) return 'Water Management';
        if (partNumber.startsWith('2_18')) return 'Landscaping';
        if (partNumber.startsWith('2_25')) return 'Stormwater';

        // Part 4: Development Types
        if (partNumber.startsWith('4.1') || partNumber.startsWith('4_1')) return 'Low Density Residential';
        if (partNumber.startsWith('4_3')) return 'Boarding Houses';

        // Part 7: Specific Uses
        if (partNumber.startsWith('7.3') || partNumber.startsWith('7_3')) return 'Adult Premises';

        // Part 8: Heritage
        if (partNumber.startsWith('8.0') || partNumber.startsWith('8_0')) return 'Heritage';

        // Part 9: Precincts/Neighbourhoods (extract neighbourhood name)
        if (partNumber.startsWith('9_') || docId.includes('_9_')) {
          // Extract neighbourhood name from document_id
          const match = docId.match(/_9_\d+_(.+?)(?:_with_IWLEP)?$/);
          if (match) {
            return match[1].replace(/_/g, ' ').replace(/Precinct \d+/, '').trim() || 'Precinct Controls';
          }
          return 'Precinct Controls';
        }

        // Part 10: Definitions
        if (partNumber.startsWith('10')) return 'Definitions';

        // Leichhardt Part C: Distinctive Neighbourhoods
        if (partNumber.startsWith('C2.2')) {
          const match = docId.match(/_C2_2_\d+_\d+_(.+?)_Distinctive_Neighbourhood/);
          if (match) {
            return match[1].replace(/_/g, ' ') + ' Neighbourhood';
          }
          return 'Neighbourhood Character';
        }

        // Special case: LLM-categorized precinct requirements
        if (partNumber === 'PRECINCT_REQUIREMENT') {
          return 'PRECINCT_REQUIREMENT'; // Will be replaced by actual category name below
        }

        return `Part ${partNumber}`;
      };

      // Check if fallback is for precinct requirements (from dcp_precinct_requirements)
      const isPrecinctFallback = detectedNeighbourhoodName && detectedPrecinctId && fallbackResult.rows.length > 0 &&
                                   fallbackResult.rows[0].category_name !== undefined;

      if (isPrecinctFallback) {
        // This is precinct data - assign to precinct variables, not general
        precinctRequirements = fallbackResult.rows.map((prov: any) => ({
          id: prov.id,
          precinct_id: prov.ref_number || detectedPrecinctId,
          precinct_name: prov.section_header || detectedNeighbourhoodName,
          category: prov.category_name,
          subcategory: undefined,
          requirement_text: prov.provision_text,
          value_numeric: undefined,
          unit: undefined,
          has_conditionals: false,
          conditional_text: undefined,
          confidence: 'high',
          pdf_page: prov.pdf_page,
          pdf_page_image_url: prov.pdf_page_image_url
        }));

        // Set general to empty for Leichhardt (no general provisions)
        generalRequirements = { rows: [] };
        usedPrecinctFallback = true;

        console.log(`✓ Fallback precinct requirements: ${precinctRequirements.length}`);
      } else {
        // This is general data - assign to general variables
        generalRequirements = {
          rows: fallbackResult.rows.map((prov: any) => ({
            id: prov.id,
            category: prov.category_name || mapPartToCategory(prov.part_number, prov.document_id),
            subcategory: prov.section_header,
            requirement_text: prov.provision_text,
            verbatim_source_text: prov.provision_text, // For legacy data, provision_text IS the verbatim
            value_numeric: undefined,
            value_min: undefined,
            value_max: undefined,
            unit: undefined,
            has_conditionals: false,
            conditional_text: undefined,
            confidence: 'high',
            pdf_page: prov.pdf_page,
            pdf_page_image_url: prov.pdf_page_image_url,
            pdf_path: prov.pdf_path
          }))
        };
        console.log(`✓ Fallback requirements (converted): ${generalRequirements.rows.length}`);
        }
      } // End if (fallbackResult !== null)
    } else {
      // Not using fallback, query requirements normally
      // Different councils have different filtering approaches:
      // - Ashfield: Zone + DevType filtering (both fields populated)
      // - Marrickville: No zone filtering (applicable_zones is NULL), some devtype filtering
      // - Leichhardt: Universal controls (both fields NULL)

      // If formerCouncil is still null, return empty rather than wrong council's data
      if (!formerCouncil) {
        console.warn(`⚠️  Former council detection failed — returning empty requirements. Address: ${address}, LGA: ${lga}`);
        return NextResponse.json({
          general_provisions: [],
          precinct_provisions: [],
          precinct_name: detectedNeighbourhoodName,
          requirements: [],
          metadata: {
            council_detection_failed: true,
            message: 'Could not determine former council area for this address. DCP requirements unavailable.',
          }
        });
      }
      const councilForQuery = formerCouncil;

      let generalRequirementsQuery: string;
      let queryParams: any[];

      if (councilForQuery?.toLowerCase() === 'ashfield') {
        // Ashfield: Filter by zone, conditionally filter by devtype
        // Uses zone translation to match legacy B1/B2 zones with current E1 zone

        // Check if querying commercial zones (E1, B1, B2, etc.)
        const isCommercialZone = zoneAliases.some(z => z.startsWith('E') || z.startsWith('B'));
        console.log(`[Ashfield Query] zoneAliases: ${JSON.stringify(zoneAliases)}, isCommercialZone: ${isCommercialZone}`);

        if (isCommercialZone) {
          console.log('[Ashfield Query] Taking COMMERCIAL zone path (NO dev type filter)');
          // Commercial zones: NO dev type filter (like Marrickville/Leichhardt)
          // Reason: Database has specific types (shop, food_and_drink_premises) but
          // frontend infers generic "commercial" → mismatch → 0 results
          generalRequirementsQuery = `
            SELECT DISTINCT ON (dgr.id)
              dgr.id,
              dgr.category,
              dgr.subcategory,
              dgr.requirement_text,
              dgr.verbatim_source_text,
              dgr.value_numeric,
              dgr.value_min,
              dgr.value_max,
              dgr.unit,
              dgr.has_conditionals,
              dgr.conditional_text,
              dgr.confidence,
              COALESCE(dgr.pdf_page, dgp.pdf_page) as pdf_page,
              COALESCE(dgr.pdf_page_image_url, dgp.pdf_page_image_url) as pdf_page_image_url,
              COALESCE(dgr.pdf_path, dgp.pdf_path) as pdf_path,
              dgr.part_name,
              dgr.part_number,
              dgr.objective,
              dgr.user_category,
              dgr.section_type,
              dgr.priority_level
            FROM dcp_general_requirements dgr
            LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
            WHERE dgr.lga = $1
            AND (dgr.applicable_zones && $2::text[] OR array_length(dgr.applicable_zones, 1) IS NULL)
            AND dgr.former_council = $3
            ORDER BY dgr.id
          `;
          queryParams = [queryLGA, zoneAliases, councilForQuery];
          console.log(`[Ashfield Query] Query params (commercial): ${JSON.stringify(queryParams)}`);
        } else {
          console.log('[Ashfield Query] Taking RESIDENTIAL zone path (WITH dev type filter)');
          // Residential zones: Keep precise dev type filtering
          generalRequirementsQuery = `
            SELECT DISTINCT ON (dgr.id)
              dgr.id,
              dgr.category,
              dgr.subcategory,
              dgr.requirement_text,
              dgr.verbatim_source_text,
              dgr.value_numeric,
              dgr.value_min,
              dgr.value_max,
              dgr.unit,
              dgr.has_conditionals,
              dgr.conditional_text,
              dgr.confidence,
              COALESCE(dgr.pdf_page, dgp.pdf_page) as pdf_page,
              COALESCE(dgr.pdf_page_image_url, dgp.pdf_page_image_url) as pdf_page_image_url,
              COALESCE(dgr.pdf_path, dgp.pdf_path) as pdf_path,
              dgr.part_name,
              dgr.part_number,
              dgr.objective,
              dgr.user_category,
              dgr.section_type,
              dgr.priority_level
            FROM dcp_general_requirements dgr
            LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
            WHERE dgr.lga = $1
            AND (dgr.applicable_zones && $2::text[] OR array_length(dgr.applicable_zones, 1) IS NULL)
            AND $3 = ANY(dgr.development_types)
            AND dgr.former_council = $4
            ORDER BY dgr.id
          `;
          queryParams = [queryLGA, zoneAliases, developmentType, councilForQuery];
          console.log(`[Ashfield Query] Query params (residential): ${JSON.stringify(queryParams)}`);
        }
      } else if (councilForQuery?.toLowerCase() === 'marrickville') {
        // Marrickville: No zone filtering (zones are NULL in DB)
        generalRequirementsQuery = `
          SELECT DISTINCT ON (dgr.id)
            dgr.id,
            dgr.category,
            dgr.subcategory,
            dgr.requirement_text,
            dgr.verbatim_source_text,
            dgr.value_numeric,
            dgr.value_min,
            dgr.value_max,
            dgr.unit,
            dgr.has_conditionals,
            dgr.conditional_text,
            dgr.confidence,
            COALESCE(dgr.pdf_page, dgp.pdf_page) as pdf_page,
            COALESCE(dgr.pdf_page_image_url, dgp.pdf_page_image_url) as pdf_page_image_url,
            COALESCE(dgr.pdf_path, dgp.pdf_path) as pdf_path,
            dgr.part_name,
            dgr.part_number,
            dgr.objective,
            dgr.user_category,
            dgr.section_type,
            dgr.priority_level
          FROM dcp_general_requirements dgr
          LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
          WHERE dgr.lga = $1
          AND dgr.former_council = $2
          ORDER BY dgr.id
        `;
        queryParams = [queryLGA, councilForQuery];
      } else if (councilForQuery?.toLowerCase() === 'leichhardt') {
        // Leichhardt: Universal controls (no zone or devtype filtering)
        generalRequirementsQuery = `
          SELECT DISTINCT ON (dgr.id)
            dgr.id,
            dgr.category,
            dgr.subcategory,
            dgr.requirement_text,
            dgr.verbatim_source_text,
            dgr.value_numeric,
            dgr.value_min,
            dgr.value_max,
            dgr.unit,
            dgr.has_conditionals,
            dgr.conditional_text,
            dgr.confidence,
            COALESCE(dgr.pdf_page, dgp.pdf_page) as pdf_page,
            COALESCE(dgr.pdf_page_image_url, dgp.pdf_page_image_url) as pdf_page_image_url,
            COALESCE(dgr.pdf_path, dgp.pdf_path) as pdf_path,
            dgr.part_name,
            dgr.part_number,
            dgr.objective,
            dgr.user_category,
            dgr.section_type,
            dgr.priority_level
          FROM dcp_general_requirements dgr
          LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
          WHERE dgr.lga = $1
          AND dgr.former_council = $2
          ORDER BY dgr.id
        `;
        queryParams = [queryLGA, councilForQuery];
      } else {
        // Unknown council, use generic query
        generalRequirementsQuery = `
          SELECT DISTINCT ON (dgr.id)
            dgr.id,
            dgr.category,
            dgr.subcategory,
            dgr.requirement_text,
            dgr.verbatim_source_text,
            dgr.value_numeric,
            dgr.value_min,
            dgr.value_max,
            dgr.unit,
            dgr.has_conditionals,
            dgr.conditional_text,
            dgr.confidence,
            COALESCE(dgr.pdf_page, dgp.pdf_page) as pdf_page,
            COALESCE(dgr.pdf_page_image_url, dgp.pdf_page_image_url) as pdf_page_image_url,
            COALESCE(dgr.pdf_path, dgp.pdf_path) as pdf_path,
            dgr.part_name,
            dgr.part_number,
            dgr.objective,
            dgr.user_category,
            dgr.section_type,
            dgr.priority_level
          FROM dcp_general_requirements dgr
          LEFT JOIN dcp_general_provisions dgp ON dgp.id = dgr.source_provision_ids[1]
          WHERE dgr.lga = $1
          AND dgr.former_council = $2
          ORDER BY dgr.id
        `;
        queryParams = [queryLGA, councilForQuery];
      }

      console.log(`[DEBUG] Query params: queryLGA="${queryLGA}", councilForQuery="${councilForQuery}", queryParams:`, queryParams);

      generalRequirements = await query(
        generalRequirementsQuery,
        queryParams
      );

      console.log(`✓ General requirements: ${generalRequirements.rows.length} (former_council=${councilForQuery})`);
    }

    // ========================================================================
    // STEP 2.5: Apply Development Type Filtering (Strategy 4: Hybrid Multi-Signal)
    // ========================================================================
    // Only apply to Marrickville and Leichhardt (neighbourhood-based DCPs without zone/devtype fields)
    // Ashfield already filters by dev type in the SQL query

    const shouldApplyDevTypeFilter =
      formerCouncil?.toLowerCase() === 'marrickville' ||
      formerCouncil?.toLowerCase() === 'leichhardt';

    // DEBUG: Log first few PDF URLs
    if (generalRequirements.rows.length > 0) {
      console.log('[DEBUG] First 3 general requirements PDF URLs:');
      generalRequirements.rows.slice(0, 3).forEach((r, i) => {
        console.log(`  [${i}] pdf_page_image_url: ${r.pdf_page_image_url}`);
      });
    }

    if (shouldApplyDevTypeFilter && generalRequirements.rows.length > 0) {
      const beforeFilterCount = generalRequirements.rows.length;

      generalRequirements.rows = filterRequirementsByDevType(
        generalRequirements.rows,
        developmentType
      );

      const afterFilterCount = generalRequirements.rows.length;
      const removedCount = beforeFilterCount - afterFilterCount;
      const removalPercent = ((removedCount / beforeFilterCount) * 100).toFixed(1);

      console.log(`✓ Dev type filter applied (${formerCouncil}):`);
      console.log(`  Before: ${beforeFilterCount} requirements`);
      console.log(`  After: ${afterFilterCount} requirements`);
      console.log(`  Removed: ${removedCount} (${removalPercent}%)`);
    }

    // ========================================================================
    // STEP 3: Query Precinct Provisions (if applicable) - CONDITIONAL
    // ========================================================================
    // Note: Spatial detection already happened in Step 0, use detectedPrecinctId variable

    // Allow override via direct precinctId parameter
    if (precinctId) {
      detectedPrecinctId = precinctId;
      console.log(`✓ Using directly provided precinct ID: ${precinctId}`);
    }

    let precinctProvisions: PrecinctProvision[] = [];
    // precinctRequirements already declared earlier to avoid initialization errors
    let precinctInfo: { precinct_id: string; precinct_name: string } | null = null;

    if (detectedPrecinctId && !usedPrecinctFallback) {
      // Only query if we haven't already populated from fallback
      // Get precinct provisions
      const precinctProvisionsQuery = `
        SELECT
          id,
          precinct_id,
          precinct_name,
          section_header,
          provision_text,
          ref_number,
          display_order
        FROM dcp_precinct_provisions
        WHERE precinct_id = $1
        ORDER BY display_order
      `;

      const precinctProvisionsResult = await query(
        precinctProvisionsQuery,
        [detectedPrecinctId]
      );

      precinctProvisions = precinctProvisionsResult.rows;

      // Get precinct requirements (with page numbers from source provisions)
      const precinctRequirementsQuery = `
        SELECT
          dpr.id,
          dpr.precinct_id,
          dpr.precinct_name,
          dpr.category,
          dpr.subcategory,
          dpr.requirement_text,
          dpr.value_numeric,
          dpr.unit,
          dpr.has_conditionals,
          dpr.conditional_text,
          dpr.confidence,
          dpr.pdf_pages[1] as pdf_page,
          dpr.pdf_page_image_url
        FROM dcp_precinct_requirements dpr
        WHERE dpr.precinct_id = $1
        ORDER BY dpr.category, dpr.id
      `;

      const precinctRequirementsResult = await query(
        precinctRequirementsQuery,
        [detectedPrecinctId]
      );

      precinctRequirements = precinctRequirementsResult.rows;

      // Set precinctInfo from provisions OR requirements (requirements are more common)
      if (precinctProvisions.length > 0) {
        precinctInfo = {
          precinct_id: precinctProvisions[0].precinct_id,
          precinct_name: precinctProvisions[0].precinct_name
        };
      } else if (precinctRequirements.length > 0) {
        precinctInfo = {
          precinct_id: precinctRequirements[0].precinct_id || detectedPrecinctId,
          precinct_name: precinctRequirements[0].precinct_name || detectedNeighbourhoodName || 'Unknown Precinct'
        };
      }

      console.log(`✓ Precinct provisions: ${precinctProvisions.length}`);
      console.log(`✓ Precinct requirements: ${precinctRequirements.length}`);
    } else if (usedPrecinctFallback) {
      // Set precinct info from fallback data
      if (precinctRequirements.length > 0) {
        precinctInfo = {
          precinct_id: precinctRequirements[0].precinct_id,
          precinct_name: precinctRequirements[0].precinct_name
        };
      }
      console.log(`✓ Precinct requirements (from fallback): ${precinctRequirements.length}`);
    }

    // ========================================================================
    // STEP 5: Combine and Categorize Requirements
    // ========================================================================

    // Group general requirements by category
    const generalByCategory = generalRequirements.rows.reduce((acc, req) => {
      if (!acc[req.category]) {
        acc[req.category] = [];
      }
      acc[req.category].push(req);
      return acc;
    }, {} as Record<string, GeneralRequirement[]>);

    // Group precinct requirements by category
    const precinctByCategory = precinctRequirements.reduce((acc, req) => {
      if (!acc[req.category]) {
        acc[req.category] = [];
      }
      acc[req.category].push(req);
      return acc;
    }, {} as Record<string, PrecinctRequirement[]>);

    // Merge all categories
    const allCategories = new Set([
      ...Object.keys(generalByCategory),
      ...Object.keys(precinctByCategory)
    ]);

    const combinedRequirements = Array.from(allCategories).map(category => ({
      category,
      general_count: generalByCategory[category]?.length || 0,
      precinct_count: precinctByCategory[category]?.length || 0,
      total_count: (generalByCategory[category]?.length || 0) + (precinctByCategory[category]?.length || 0),
      general_requirements: generalByCategory[category] || [],
      precinct_requirements: precinctByCategory[category] || []
    }));

    // ========================================================================
    // STEP 5.5: Part-Level Grouping & DA Requirements Filtering (Phase 1)
    // ========================================================================

    // Filter DA requirements (documentation/process provisions)
    const daRequirements = generalRequirements.rows.filter(req =>
      req.category === 'da_requirements' ||
      req.user_category === 'documentation' ||
      req.category === 'process'
    );

    // Group by Part → Category → Requirements
    const byPart: Record<string, any> = {};

    for (const requirement of generalRequirements.rows) {
      const partName = requirement.part_name || 'General Provisions';
      const category = requirement.user_category || requirement.category || 'other';

      if (!byPart[partName]) {
        byPart[partName] = {
          part_number: requirement.part_number || null,
          provision_count: 0,
          objectives: [],
          categories: {}
        };
      }

      // Collect unique objectives for this Part
      if (requirement.objective && requirement.objective.trim()) {
        if (!byPart[partName].objectives.includes(requirement.objective)) {
          byPart[partName].objectives.push(requirement.objective);
        }
      }

      // Group by category within part
      if (!byPart[partName].categories[category]) {
        byPart[partName].categories[category] = [];
      }
      byPart[partName].categories[category].push(requirement);
      byPart[partName].provision_count++;
    }

    // ========================================================================
    // STEP 6: Build Response
    // ========================================================================

    const elapsedTime = Date.now() - startTime;

    // Determine applicable_to text based on council's filtering approach
    let applicableToText: string;
    if (formerCouncil?.toLowerCase() === 'ashfield') {
      // Ashfield: Zone + DevType filtering
      applicableToText = `All properties in ${zone} zone with ${developmentType.replace(/_/g, ' ')} development`;
    } else if (formerCouncil?.toLowerCase() === 'marrickville') {
      // Marrickville: Neighbourhood + some devtype filtering
      applicableToText = `All properties in Marrickville LGA`;
    } else if (formerCouncil?.toLowerCase() === 'leichhardt') {
      // Leichhardt: Universal controls
      applicableToText = `All properties in Leichhardt LGA`;
    } else {
      // Fallback for unknown council
      applicableToText = `All properties in ${lga}`;
    }

    // Determine DCP instrument name based on council
    let dcpInstrumentName: string;
    if (formerCouncil?.toLowerCase() === 'ashfield') {
      dcpInstrumentName = 'Inner West Ashfield DCP 2016';
    } else if (formerCouncil?.toLowerCase() === 'marrickville') {
      dcpInstrumentName = 'Marrickville DCP 2011';
    } else if (formerCouncil?.toLowerCase() === 'leichhardt') {
      dcpInstrumentName = 'Leichhardt DCP 2013';
    } else {
      dcpInstrumentName = `${lga} Development Control Plan`;
    }

    const response = {
      success: true,
      elapsed_ms: elapsedTime,
      query: {
        address,
        zone,
        developmentType,
        lga,
        formerCouncil
      },
      general_provisions: {
        source: dcpInstrumentName,
        applicable_to: applicableToText,
        count: generalProvisions.rows.length,
        requirements_count: generalRequirements.rows.length,
        provisions: generalProvisions.rows,
        requirements: generalRequirements.rows,
        by_category: generalByCategory,
        // Phase 1: Part-level grouping
        by_part: byPart
      },
      // Phase 1: DA Requirements filtering
      da_requirements: {
        count: daRequirements.length,
        requirements: daRequirements
      },
      precinct_provisions: precinctInfo ? {
        source: precinctInfo.precinct_name,
        precinct_id: precinctInfo.precinct_id,
        precinct_name: precinctInfo.precinct_name,
        applicable_to: 'Properties within precinct boundary',
        count: precinctProvisions.length,
        requirements_count: precinctRequirements.length,
        provisions: precinctProvisions,
        requirements: precinctRequirements,
        by_category: precinctByCategory
      } : null,
      combined: {
        total_provisions: generalProvisions.rows.length + precinctProvisions.length,
        total_requirements: generalRequirements.rows.length + precinctRequirements.length,
        categories: combinedRequirements.sort((a, b) => b.total_count - a.total_count)
      }
    };

    console.log('=== Response Summary ===');
    console.log(`General: ${response.general_provisions.count} provisions, ${response.general_provisions.requirements_count} requirements`);
    console.log(`Precinct: ${response.precinct_provisions?.count || 0} provisions, ${response.precinct_provisions?.requirements_count || 0} requirements`);
    console.log(`Total: ${response.combined.total_provisions} provisions, ${response.combined.total_requirements} requirements`);
    console.log(`Elapsed: ${elapsedTime}ms`);

    return NextResponse.json(response);

  } catch (error) {
    console.error('DCP Complete API Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }, { status: 500 });
  }
}
// Force recompile
 
