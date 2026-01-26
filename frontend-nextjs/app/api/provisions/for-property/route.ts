/**
 * Provisions for Property API - 4-Layer Filtering
 *
 * Returns DCP provisions filtered by the 4-layer model:
 * - Layer 1 (Generic): Always include (Part 2, Section 1)
 * - Layer 2 (Use-specific): Zone-filtered (Part 4, Section 3)
 * - Layer 3 (Condition): Heritage/flood filtered (Part 8, heritage chapters)
 * - Layer 4 (Precinct): Location-filtered by precinct ID
 *
 * Query Parameters:
 * - lga: LGA name (e.g., "Inner West")
 * - zone: Zone code (e.g., "R2", "R3")
 * - heritage: "true" if property is heritage or in HCA
 * - flood: "true" if property is flood-prone
 * - precinct_id: Precinct identifier (e.g., "12_", "G6", "Part 1")
 * - dev_type: Development type (optional)
 * - topic: Filter by topic (optional)
 * - groupBy: "topic" (default) or "toc" - how to group results
 *
 * Response includes:
 * - by_layer: provisions grouped by 4-layer model
 * - by_topic: provisions grouped by topic (always included)
 * - by_toc: provisions grouped by DCP structure (only if groupBy=toc)
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

interface PropertyFilters {
  lga?: string;
  zone?: string;
  heritage?: boolean;
  flood?: boolean;
  bushfire?: boolean;
  precinct_id?: string;
  dev_type?: string;
  topic?: string;
  assessment_type?: 'CDC' | 'DA';  // CDC = quantitative only, DA = all
  former_council?: string;  // Former council name (Ashfield, Marrickville, Leichhardt)
  hca?: string;  // Heritage Conservation Area slug (e.g., "summer_hill", "hca_1")
  groupBy?: 'topic' | 'toc';  // How to group results (default: topic)
}

interface LayerResult {
  layer: string;
  layer_name: string;
  provisions: any[];
  count: number;
}

/**
 * Normalize precinct ID format for database lookup
 *
 * Precinct service returns formats like: 9_29, 9_13, 9_30 (chapter_section for Marrickville)
 * Database uses formats like: 29_, 13_, 30_ (just section_)
 *
 * For Marrickville (chapter 9), convert 9_XX to XX_
 * For other councils (Ashfield, Leichhardt), pass through as-is
 */
function normalizePrecinctId(precinctId: string): string {
  if (!precinctId) return precinctId;

  // Marrickville chapter 9 format: 9_XX -> XX_
  const marrickvilleMatch = precinctId.match(/^9_(\d+)$/);
  if (marrickvilleMatch) {
    const normalized = `${marrickvilleMatch[1]}_`;
    console.log(`[Precinct Normalization] Marrickville: ${precinctId} -> ${normalized}`);
    return normalized;
  }

  // Ashfield format: Part 1, Part 2, etc. - pass through
  // Leichhardt format: C2.X.X.X, G1, etc. - pass through
  return precinctId;
}

/**
 * Dev type hierarchy for granular filtering (WITHOUT 'ALL' tag).
 * Generic provisions (tagged 'ALL') come from Layer 1 (v2_dcp_layer='generic'),
 * not from dev_type matching. This prevents 85% of provisions matching everything.
 */
const DEV_TYPE_HIERARCHY: Record<string, string[]> = {
  // Dwelling house variants
  dwelling_house_new: ['dwelling_house_new', 'dwelling_house'],
  dwelling_house_alteration: ['dwelling_house_alteration', 'dwelling_house'],
  dwelling_addition: ['dwelling_addition', 'dwelling_house'],
  dwelling_addition_ground: ['dwelling_addition_ground', 'dwelling_addition', 'dwelling_house'],
  dwelling_addition_first: ['dwelling_addition_first', 'dwelling_addition', 'dwelling_house'],
  dwelling_addition_rear: ['dwelling_addition_rear', 'dwelling_addition', 'dwelling_house'],

  // Secondary dwelling
  secondary_dwelling: ['secondary_dwelling'],
  secondary_dwelling_new: ['secondary_dwelling_new', 'secondary_dwelling'],
  secondary_dwelling_conversion: ['secondary_dwelling_conversion', 'secondary_dwelling'],

  // Dual occupancy
  dual_occupancy: ['dual_occupancy'],
  dual_occupancy_attached: ['dual_occupancy_attached', 'dual_occupancy'],
  dual_occupancy_detached: ['dual_occupancy_detached', 'dual_occupancy'],

  // Multi-dwelling
  multi_dwelling_housing: ['multi_dwelling_housing'],
  residential_flat_building: ['residential_flat_building'],
  shop_top_housing: ['shop_top_housing'],

  // Commercial
  retail_premises: ['retail_premises', 'commercial_premises'],
  office_premises: ['office_premises', 'commercial_premises'],
  food_and_drink_premises: ['food_and_drink_premises', 'commercial_premises'],
  commercial_premises: ['commercial_premises'],

  // Industrial
  light_industry: ['light_industry', 'industrial_development'],
  warehouse: ['warehouse', 'industrial_development'],
  industrial_development: ['industrial_development'],

  // Fallback for legacy types
  dwelling_house: ['dwelling_house'],
  boarding_house: ['boarding_house'],
  child_care_centre: ['child_care_centre'],

  // Simplified category groupings (for Leichhardt dropdown)
  residential: [
    'dwelling_house', 'dual_occupancy', 'secondary_dwelling',
    'multi_dwelling_housing', 'residential_flat_building', 'boarding_house',
    'dwelling_addition', 'dwelling_house_new', 'dwelling_house_alteration'
  ],
  commercial: [
    'commercial_premises', 'retail_premises', 'office_premises',
    'food_and_drink_premises', 'shop_top_housing', 'child_care_centre'
  ],
  industrial: [
    'industrial_development', 'warehouse', 'light_industry'
  ],
};

/**
 * Expand a dev_type to its full hierarchy for matching.
 * Returns array of dev_types that should match provisions.
 * Does NOT include 'ALL' - generic provisions come from Layer 1.
 */
function expandDevTypeHierarchy(devType: string): string[] {
  // Check if we have a defined hierarchy
  if (DEV_TYPE_HIERARCHY[devType]) {
    return DEV_TYPE_HIERARCHY[devType];
  }

  // Fallback: match exact type only (no ALL)
  return [devType];
}

/**
 * Lookup db_slug from heritage_conservation_areas by h_id (Planning Portal C-code)
 * Returns the db_slug that matches v2_heritage_hca in regulatory_provisions
 */
async function resolveHcaCode(client: any, hcaCode: string): Promise<string | null> {
  // If already looks like a db_slug (e.g., "hca_35", "summer_hill"), return as-is
  if (!hcaCode.match(/^[CA]\d+$/i)) {
    return hcaCode;
  }

  const result = await client.query(
    `SELECT db_slug FROM heritage_conservation_areas WHERE h_id = $1 LIMIT 1`,
    [hcaCode.toUpperCase()]
  );

  if (result.rows.length > 0 && result.rows[0].db_slug) {
    console.log(`[HCA Lookup] ${hcaCode} -> ${result.rows[0].db_slug}`);
    return result.rows[0].db_slug;
  }

  console.log(`[HCA Lookup] ${hcaCode} -> no mapping found`);
  return null;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const { searchParams } = new URL(request.url);

    // Parse filters
    const filters: PropertyFilters = {
      lga: searchParams.get('lga') || undefined,
      zone: searchParams.get('zone') || undefined,
      heritage: searchParams.get('heritage') === 'true',
      flood: searchParams.get('flood') === 'true',
      bushfire: searchParams.get('bushfire') === 'true',
      precinct_id: searchParams.get('precinct_id') ? normalizePrecinctId(searchParams.get('precinct_id')!) : undefined,
      dev_type: searchParams.get('dev_type') || undefined,
      topic: searchParams.get('topic') || undefined,
      assessment_type: (searchParams.get('assessment_type') as 'CDC' | 'DA') || undefined,
      former_council: searchParams.get('former_council') || undefined,
      hca: searchParams.get('hca') || undefined,
      groupBy: (searchParams.get('groupBy') as 'topic' | 'toc') || 'topic',
    };

    console.log(`[4-Layer API] Filters: ${JSON.stringify(filters)}`);

    const pool = getPool();
    const client = await pool.connect();

    try {
      // Resolve HCA code (e.g., "C98") to db_slug (e.g., "summer_hill")
      if (filters.hca) {
        const resolvedHca = await resolveHcaCode(client, filters.hca);
        if (resolvedHca) {
          filters.hca = resolvedHca;
        } else {
          // No mapping found - clear the filter to avoid false matches
          filters.hca = undefined;
        }
      }

      const results: LayerResult[] = [];

      // Layer 1: Generic provisions (always include)
      const layer1Raw = await queryLayer(client, 'generic', filters);
      const layer1 = await enrichWithTocSections(client, layer1Raw);
      results.push({
        layer: 'generic',
        layer_name: 'General Requirements',
        provisions: layer1,
        count: layer1.length
      });

      // Layer 2: Use-specific provisions (zone-filtered)
      const layer2Raw = await queryLayer(client, 'use_specific', filters);
      const layer2 = await enrichWithTocSections(client, layer2Raw);
      results.push({
        layer: 'use_specific',
        layer_name: 'Zone-Specific Requirements',
        provisions: layer2,
        count: layer2.length
      });

      // Layer 3: Condition provisions (heritage/flood filtered)
      const layer3Raw = await queryLayer(client, 'condition', filters);
      const layer3 = await enrichWithTocSections(client, layer3Raw);
      results.push({
        layer: 'condition',
        layer_name: 'Site Condition Requirements',
        provisions: layer3,
        count: layer3.length
      });

      // Layer 4: Precinct provisions (location-filtered)
      const layer4Raw = await queryLayer(client, 'precinct', filters);
      const layer4 = await enrichWithTocSections(client, layer4Raw);
      results.push({
        layer: 'precinct',
        layer_name: 'Precinct-Specific Requirements',
        provisions: layer4,
        count: layer4.length
      });

      // No URL adjustment needed - PDF files are correctly named
      // page_N.png contains DCP page N+1 content (verified 2024-12-10)
      const adjustedResults = results;

      const totalCount = adjustedResults.reduce((sum, r) => sum + r.count, 0);
      const responseTime = Date.now() - startTime;

      // Group provisions based on groupBy parameter
      const byTopic = groupByTopic(adjustedResults);
      const byToc = filters.groupBy === 'toc'
        ? groupByTocStructure(adjustedResults, filters.former_council)
        : undefined;

      // Include dev_type hierarchy info if filtering by dev_type
      const devTypeInfo = filters.dev_type ? {
        selected: filters.dev_type,
        expanded_hierarchy: expandDevTypeHierarchy(filters.dev_type),
      } : undefined;

      // Cache for 5 minutes on edge, 1 minute stale-while-revalidate
      const response = NextResponse.json({
        success: true,
        data: {
          by_layer: adjustedResults,
          by_topic: byTopic,
          by_toc: byToc,
          summary: {
            total_provisions: totalCount,
            layer_1_generic: adjustedResults[0].count,
            layer_2_use_specific: adjustedResults[1].count,
            layer_3_condition: adjustedResults[2].count,
            layer_4_precinct: adjustedResults[3].count,
          }
        },
        meta: {
          filters_applied: filters,
          dev_type_hierarchy: devTypeInfo,
          response_time_ms: responseTime,
          api_version: 'v2_4layer_toc'
        }
      });
      response.headers.set('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=60');
      return response;

    } finally {
      client.release();
    }

  } catch (error) {
    console.error('[4-Layer API] Error:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

/**
 * Query heritage provisions filtered by specific HCA from regulatory_provisions
 * Returns provisions for the property's HCA + general heritage controls
 */
async function queryHeritageByHca(
  client: any,
  filters: PropertyFilters
): Promise<any[]> {
  const params: any[] = [];
  let paramIndex = 1;

  // Query regulatory_provisions for HCA-specific provisions
  let sql = `
    SELECT
      id,
      document_id,
      provision_text,
      v2_dcp_layer,
      v2_dcp_part,
      v2_topic,
      v2_provision_type,
      v2_precinct_id,
      v2_marker,
      v2_display_behavior,
      pdf_page,
      pdf_source_file,
      pdf_page_image_url,
      v2_heritage_type,
      v2_heritage_element,
      v2_heritage_hca
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND (LOWER(v2_topic) = 'heritage' OR v2_topic = 'Heritage')
      AND (
        v2_heritage_hca IS NULL  -- General heritage controls
        OR v2_heritage_hca = $${paramIndex++}  -- Property's specific HCA
      )
  `;
  params.push(filters.hca);

  // Filter by former council
  if (filters.former_council) {
    const councilName = filters.former_council.charAt(0).toUpperCase() + filters.former_council.slice(1).toLowerCase();
    sql += ` AND document_id ILIKE $${paramIndex++}`;
    params.push(`%${councilName}%`);
  }

  // Filter by precinct - only include general provisions or property's precinct
  // Exclude Part 9 precinct-specific provisions for other precincts
  if (filters.precinct_id) {
    sql += ` AND (v2_precinct_id IS NULL OR v2_precinct_id = $${paramIndex++})`;
    params.push(filters.precinct_id);
  } else {
    // No precinct specified - exclude all precinct-specific provisions
    sql += ` AND v2_precinct_id IS NULL`;
  }

  sql += ` ORDER BY v2_dcp_part, id LIMIT 200`;

  const result = await client.query(sql, params);
  return result.rows;
}

/**
 * Query heritage provisions from dcp_general_requirements (LLM-extracted, curated data)
 * Maps columns to match the UI's expected interface
 */
/**
 * Enrich provisions with TOC section info (section_number, section_title)
 * Uses document_id + pdf_page to find matching TOC entry
 */
async function enrichWithTocSections(
  client: any,
  provisions: any[]
): Promise<any[]> {
  if (provisions.length === 0) return provisions;

  // Get unique document_id + pdf_page combinations
  const docPages = provisions
    .filter(p => p.pdf_page != null)
    .map(p => ({ doc_id: p.document_id, page: p.pdf_page, id: p.id }));

  if (docPages.length === 0) return provisions;

  // Batch query TOC sections for all provisions
  // Uses exact match OR fuzzy match (for IWLEP suffix variations)
  const sql = `
    WITH provision_pages AS (
      SELECT DISTINCT document_id, pdf_page
      FROM regulatory_provisions
      WHERE id = ANY($1::int[])
    )
    SELECT DISTINCT ON (pp.document_id, pp.pdf_page)
      pp.document_id,
      pp.pdf_page,
      t.section_number as toc_section_number,
      t.section_title as toc_section_title
    FROM provision_pages pp
    LEFT JOIN dcp_table_of_contents t ON (
      t.document_id = pp.document_id
      OR t.document_id LIKE REGEXP_REPLACE(pp.document_id, '_with_IWLEP.*$', '') || '%'
    )
    AND pp.pdf_page >= t.page_start
    AND (t.page_end IS NULL OR pp.pdf_page <= t.page_end)
    ORDER BY pp.document_id, pp.pdf_page, t.page_start DESC
  `;

  const provisionIds = provisions.map(p => p.id);
  const result = await client.query(sql, [provisionIds]);

  // Create lookup map: "doc_id|page" -> TOC info
  const tocMap = new Map<string, { section_number: string; section_title: string }>();
  for (const row of result.rows) {
    if (row.toc_section_number) {
      const key = `${row.document_id}|${row.pdf_page}`;
      tocMap.set(key, {
        section_number: row.toc_section_number,
        section_title: row.toc_section_title
      });
    }
  }

  // Enrich provisions with TOC info
  return provisions.map(p => {
    const key = `${p.document_id}|${p.pdf_page}`;
    const tocInfo = tocMap.get(key);
    return {
      ...p,
      toc_section_number: tocInfo?.section_number || null,
      toc_section_title: tocInfo?.section_title || null
    };
  });
}

async function queryHeritageFromDcpGeneralRequirements(
  client: any,
  filters: PropertyFilters
): Promise<any[]> {
  const params: any[] = [];
  let paramIndex = 1;

  let sql = `
    SELECT
      id,
      NULL as document_id,
      COALESCE(verbatim_source_text, requirement_text) as provision_text,
      'condition' as v2_dcp_layer,
      COALESCE(part_number, part_name) as v2_dcp_part,
      CASE
        WHEN part_name = 'Heritage' THEN 'Heritage'
        ELSE INITCAP(REPLACE(category, '_', ' '))
      END as v2_topic,
      'control' as v2_provision_type,
      NULL as v2_precinct_id,
      NULL as v2_marker,
      NULL as v2_display_behavior,
      pdf_page,
      pdf_path as pdf_source_file,
      pdf_page_image_url,
      NULL as v2_heritage_type,
      NULL as v2_heritage_element,
      NULL as v2_heritage_hca,
      INITCAP(REPLACE(category, '_', ' ')) as v2_heritage_subcategory
    FROM dcp_general_requirements
    WHERE (category = 'heritage' OR part_name ILIKE '%Heritage%')
    -- Exclude non-heritage sections that just mention heritage
    AND (part_name IS NULL OR part_name NOT IN ('Energy Management', 'Waste Management', 'Landscaping and Open Spaces', 'Fencing'))
  `;

  // Filter by former council
  if (filters.former_council) {
    const councilName = filters.former_council.charAt(0).toUpperCase() + filters.former_council.slice(1).toLowerCase();
    sql += ` AND former_council = $${paramIndex++}`;
    params.push(councilName);
  }

  sql += ` ORDER BY part_name, id LIMIT 500`;

  const result = await client.query(sql, params);
  return result.rows;
}

async function queryLayer(
  client: any,
  layer: string,
  filters: PropertyFilters
): Promise<any[]> {
  // For condition layer with heritage, use appropriate source based on HCA filter
  const isAshfield = filters.former_council?.toLowerCase() === 'ashfield';
  if (layer === 'condition' && (filters.heritage || isAshfield)) {
    // If specific HCA is provided, query regulatory_provisions filtered by that HCA
    // This gives specific HCA provisions + general heritage provisions
    if (filters.hca) {
      return queryHeritageByHca(client, filters);
    }
    // Otherwise return general heritage provisions from dcp_general_requirements
    // but limit to a smaller set (not 500+)
    return queryHeritageFromDcpGeneralRequirements(client, filters);
  }

  const params: any[] = [];
  let paramIndex = 1;

  let sql = `
    SELECT
      id,
      document_id,
      provision_text,
      v2_dcp_layer,
      v2_dcp_part,
      v2_topic,
      v2_provision_type,
      v2_precinct_id,
      v2_marker,
      v2_display_behavior,
      pdf_page,
      pdf_source_file,
      pdf_page_image_url,
      v2_heritage_type,
      v2_heritage_element,
      v2_heritage_hca
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = $${paramIndex++}
  `;
  params.push(layer);

  // Filter by former council (Ashfield/Marrickville/Leichhardt) via document_id pattern
  if (filters.former_council) {
    // Capitalize first letter for matching (e.g., "marrickville" -> "Marrickville")
    const councilName = filters.former_council.charAt(0).toUpperCase() + filters.former_council.slice(1).toLowerCase();
    sql += ` AND document_id ILIKE $${paramIndex++}`;
    params.push(`%${councilName}%`);
  }

  // Heritage filtering logic:
  // 1. Generic/use-specific layers: Only include heritage provisions if LEP heritage = true
  // 2. Precinct layer: ALWAYS include provisions if in that precinct (precinct defines scope)
  // 3. Condition layer: Handled separately below
  // IMPORTANT: Check both v2_topic and v2_marker for heritage (provisions tagged with either)
  //
  // Authority: EP&A Act s 3.42 - DCP precinct provisions apply to all properties within
  // precinct boundaries, independently of LEP heritage schedules (precinct maps define scope)
  if (!filters.heritage && layer !== 'condition' && layer !== 'precinct') {
    // Property is not heritage - exclude all heritage provisions from generic/use-specific layers
    sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
  } else if (filters.hca && layer !== 'condition' && layer !== 'precinct') {
    // Heritage with HCA - exclude from non-condition layers (handled by queryHeritageByHca)
    sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
  } else if (filters.heritage && !filters.hca && layer !== 'condition' && layer !== 'precinct') {
    // Heritage without HCA - include but filter by precinct to avoid showing ALL precincts
    if (filters.precinct_id) {
      sql += ` AND ((LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage')) OR v2_precinct_id IS NULL OR v2_precinct_id = $${paramIndex++})`;
      params.push(filters.precinct_id);
    } else {
      // No precinct specified - only show non-precinct heritage provisions
      sql += ` AND ((LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage')) OR v2_precinct_id IS NULL)`;
    }
  }
  // Note: Precinct layer (layer === 'precinct') is NOT filtered by heritage status
  // Precinct provisions (including heritage-tagged ones) apply to ALL properties in precinct

  // Layer-specific filtering
  if (layer === 'use_specific' && filters.zone) {
    // For use-specific layer, filter by zone applicability
    // Include provisions where: zone is NULL (universal), zone matches, OR 'ALL' is in zones
    sql += ` AND (v2_applicable_zones IS NULL OR $${paramIndex++} = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))`;
    params.push(filters.zone);
  }

  if (layer === 'condition') {
    // For condition layer (non-heritage), only include if property has that condition
    const conditions: string[] = [];
    if (filters.flood) conditions.push('flood');
    if (filters.bushfire) conditions.push('bushfire');

    if (conditions.length === 0) {
      // No conditions apply, skip condition layer
      return [];
    }

    sql += ` AND v2_site_condition_required = ANY($${paramIndex++}::text[])`;
    params.push(conditions);
  }

  if (layer === 'precinct') {
    if (filters.precinct_id) {
      // For precinct layer, filter by precinct ID
      console.log(`[4-Layer API] Precinct filter: v2_precinct_id = '${filters.precinct_id}'`);
      sql += ` AND v2_precinct_id = $${paramIndex++}`;
      params.push(filters.precinct_id);
    } else {
      // No precinct ID - exclude all precinct-specific provisions
      console.log(`[4-Layer API] No precinct_id provided - excluding all precinct provisions`);
      sql += ` AND v2_precinct_id IS NULL`;
    }
  }

  // Optional topic filter (case-insensitive, handle underscore vs space)
  // DB has "Building Form", UI sends "building_form"
  if (filters.topic) {
    sql += ` AND LOWER(REPLACE(v2_topic, ' ', '_')) = LOWER($${paramIndex++})`;
    params.push(filters.topic.replace(/ /g, '_'));
  }

  // Optional dev_type filter with hierarchical matching
  // Applies to ALL layers - provisions tagged with specific dev types or 'ALL' are included
  if (filters.dev_type) {
    // Expand dev_type to include related types (e.g., 'residential' -> all residential types)
    // Include provisions tagged with 'ALL' (applies to all development types)
    const expandedTypes = expandDevTypeHierarchy(filters.dev_type);
    sql += ` AND (v2_applicable_dev_types && $${paramIndex++}::text[] OR 'ALL' = ANY(v2_applicable_dev_types) OR v2_applicable_dev_types IS NULL)`;
    params.push(expandedTypes);
  }

  // Assessment type filter (CDC = quantitative only, DA = all)
  if (filters.assessment_type === 'CDC') {
    // CDC requires quantitative, checkable controls with numeric values
    sql += ` AND v2_provision_type = 'control' AND v2_has_numeric_value = true`;
  }
  // DA shows all provisions (no additional filter)

  sql += ` ORDER BY v2_topic, v2_dcp_part, id LIMIT 500`;

  const result = await client.query(sql, params);
  return result.rows;
}

function groupByTopic(layers: LayerResult[]): Record<string, any[]> {
  const byTopic: Record<string, any[]> = {};

  for (const layer of layers) {
    for (const provision of layer.provisions) {
      // Normalize topic: "Building Form" → "building_form" for consistent UI keys
      const rawTopic = provision.v2_topic || 'other';
      const topic = rawTopic.toLowerCase().replace(/ /g, '_');
      if (!byTopic[topic]) {
        byTopic[topic] = [];
      }
      byTopic[topic].push({
        ...provision,
        layer: layer.layer
      });
    }
  }

  return byTopic;
}

/**
 * Group provisions by DCP TOC structure (Part → Section → Provisions)
 * Handles Leichhardt Part C Section 1 specially by grouping via C markers
 */
interface TocSection {
  section_id: string;
  section_title: string;
  provision_count: number;
  provisions: any[];
  sub_groups?: Record<string, TocSection>;  // For Leichhardt C markers
}

interface TocPart {
  part_id: string;
  part_name: string;
  provision_count: number;
  sections: Record<string, TocSection>;
}

function groupByTocStructure(
  layers: LayerResult[],
  formerCouncil?: string
): Record<string, TocPart> {
  const byToc: Record<string, TocPart> = {};

  // Flatten all provisions from all layers
  // Deduplicate by provision ID to prevent same provision appearing multiple times
  const provisionMap = new Map<number, any>();
  for (const layer of layers) {
    for (const provision of layer.provisions) {
      // Keep first occurrence (preserves layer priority order)
      if (!provisionMap.has(provision.id)) {
        provisionMap.set(provision.id, { ...provision, layer: layer.layer });
      }
    }
  }

  // Second pass: deduplicate by text content (database may have multiple IDs with same text)
  // Use first 100 chars + page as dedup key to catch true duplicates while allowing
  // legitimately similar provisions on different pages
  const textDeduped = new Map<string, any>();
  for (const provision of provisionMap.values()) {
    const textKey = `${(provision.provision_text || '').substring(0, 100)}|${provision.pdf_page || 0}`;
    if (!textDeduped.has(textKey)) {
      textDeduped.set(textKey, provision);
    }
  }
  const allProvisions = Array.from(textDeduped.values());

  // Group by v2_dcp_part first
  for (const provision of allProvisions) {
    const partId = provision.v2_dcp_part || 'Other';
    const partName = formatPartName(partId);

    if (!byToc[partId]) {
      byToc[partId] = {
        part_id: partId,
        part_name: partName,
        provision_count: 0,
        sections: {}
      };
    }

    // Determine section ID from TOC or marker
    let sectionId = provision.toc_section_number || 'unsectioned';
    let sectionTitle = provision.toc_section_title || 'General';

    // Special handling for Leichhardt Part C Section 1 - use C markers as sub-groups
    const isLeichhardtPartC = formerCouncil?.toLowerCase() === 'leichhardt' &&
      partId?.includes('Part C') && partId?.includes('Section 1');

    if (isLeichhardtPartC && provision.v2_marker) {
      // Use C marker as section for Leichhardt Part C Section 1
      sectionId = provision.v2_marker;
      sectionTitle = `Control ${provision.v2_marker}`;
    }

    if (!byToc[partId].sections[sectionId]) {
      byToc[partId].sections[sectionId] = {
        section_id: sectionId,
        section_title: sectionTitle,
        provision_count: 0,
        provisions: []
      };
    }

    byToc[partId].sections[sectionId].provisions.push(provision);
    byToc[partId].sections[sectionId].provision_count++;
    byToc[partId].provision_count++;
  }

  // Sort sections within each part by section_id
  for (const partId of Object.keys(byToc)) {
    const sortedSections: Record<string, TocSection> = {};
    const sectionKeys = Object.keys(byToc[partId].sections).sort((a, b) => {
      // Sort C markers numerically (C1, C2, C10, C11...)
      if (a.startsWith('C') && b.startsWith('C')) {
        const numA = parseInt(a.slice(1)) || 0;
        const numB = parseInt(b.slice(1)) || 0;
        return numA - numB;
      }
      // Sort numeric sections (2.10, 2.11...)
      return a.localeCompare(b, undefined, { numeric: true });
    });
    for (const key of sectionKeys) {
      sortedSections[key] = byToc[partId].sections[key];
    }
    byToc[partId].sections = sortedSections;
  }

  return byToc;
}

/**
 * Format DCP part ID to readable name
 */
function formatPartName(partId: string): string {
  if (!partId || partId === 'Other') return 'Other Provisions';

  // Already formatted
  if (partId.includes(':')) return partId;

  // Common patterns
  const patterns: Record<string, string> = {
    'Part 2': 'Part 2: General Provisions',
    'Part 4': 'Part 4: Residential Development',
    'Part 4.1': 'Part 4.1: Low Density Residential',
    'Part 4.2': 'Part 4.2: Multi-Dwelling Housing',
    'Part 5': 'Part 5: Commercial Development',
    'Part 6': 'Part 6: Industrial Development',
    'Part 8': 'Part 8: Heritage',
    'Part 9': 'Part 9: Precincts',
    'Part C Section 1': 'Part C Section 1: General Controls',
    'Part C Section 2': 'Part C Section 2: Distinctive Neighbourhoods',
    'Part C Section 3': 'Part C Section 3: Residential',
    'Part D': 'Part D: Energy',
    'Part E': 'Part E: Water',
    'Part F': 'Part F: Food',
    'Part G': 'Part G: Neighbourhoods',
    'Chapter A': 'Chapter A: Miscellaneous',
    'Chapter B': 'Chapter B: Public Domain',
    'Chapter C': 'Chapter C: Sustainability',
    'Chapter D': 'Chapter D: Precincts',
    'Chapter E1': 'Chapter E1: Heritage',
    'Chapter F': 'Chapter F: Development Category',
  };

  return patterns[partId] || partId;
}
