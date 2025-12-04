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
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

// Use the shared database pool from lib/db.ts
// It uses PGHOST, PGDATABASE, PGUSER, PGPASSWORD, PGPORT env vars

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
}

interface LayerResult {
  layer: string;
  layer_name: string;
  provisions: any[];
  count: number;
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
      precinct_id: searchParams.get('precinct_id') || undefined,
      dev_type: searchParams.get('dev_type') || undefined,
      topic: searchParams.get('topic') || undefined,
      assessment_type: (searchParams.get('assessment_type') as 'CDC' | 'DA') || undefined,
      former_council: searchParams.get('former_council') || undefined,
      hca: searchParams.get('hca') || undefined,
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
      const layer1 = await queryLayer(client, 'generic', filters);
      results.push({
        layer: 'generic',
        layer_name: 'General Requirements',
        provisions: layer1,
        count: layer1.length
      });

      // Layer 2: Use-specific provisions (zone-filtered)
      const layer2 = await queryLayer(client, 'use_specific', filters);
      results.push({
        layer: 'use_specific',
        layer_name: 'Zone-Specific Requirements',
        provisions: layer2,
        count: layer2.length
      });

      // Layer 3: Condition provisions (heritage/flood filtered)
      const layer3 = await queryLayer(client, 'condition', filters);
      results.push({
        layer: 'condition',
        layer_name: 'Site Condition Requirements',
        provisions: layer3,
        count: layer3.length
      });

      // Layer 4: Precinct provisions (location-filtered)
      const layer4 = await queryLayer(client, 'precinct', filters);
      results.push({
        layer: 'precinct',
        layer_name: 'Precinct-Specific Requirements',
        provisions: layer4,
        count: layer4.length
      });

      const totalCount = results.reduce((sum, r) => sum + r.count, 0);
      const responseTime = Date.now() - startTime;

      // Group by topic for display
      const byTopic = groupByTopic(results);

      // Include dev_type hierarchy info if filtering by dev_type
      const devTypeInfo = filters.dev_type ? {
        selected: filters.dev_type,
        expanded_hierarchy: expandDevTypeHierarchy(filters.dev_type),
      } : undefined;

      // Cache for 5 minutes on edge, 1 minute stale-while-revalidate
      const response = NextResponse.json({
        success: true,
        data: {
          by_layer: results,
          by_topic: byTopic,
          summary: {
            total_provisions: totalCount,
            layer_1_generic: results[0].count,
            layer_2_use_specific: results[1].count,
            layer_3_condition: results[2].count,
            layer_4_precinct: results[3].count,
          }
        },
        meta: {
          filters_applied: filters,
          dev_type_hierarchy: devTypeInfo,
          response_time_ms: responseTime,
          api_version: 'v2_4layer_granular'
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
async function queryHeritageFromDcpGeneralRequirements(
  client: any,
  filters: PropertyFilters
): Promise<any[]> {
  const params: any[] = [];
  let paramIndex = 1;

  let sql = `
    SELECT
      id,
      COALESCE(verbatim_source_text, requirement_text) as provision_text,
      'condition' as v2_dcp_layer,
      part_name as v2_dcp_part,
      INITCAP(REPLACE(category, '_', ' ')) as v2_topic,
      'control' as v2_provision_type,
      NULL as v2_precinct_id,
      NULL as v2_marker,
      NULL as v2_display_behavior,
      pdf_page,
      pdf_path as pdf_source_file,
      pdf_page_image_url,
      NULL as v2_heritage_type,
      NULL as v2_heritage_element,
      NULL as v2_heritage_hca
    FROM dcp_general_requirements
    WHERE (category = 'heritage' OR part_name ILIKE '%Heritage%')
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
  // 1. If property is NOT heritage (heritage=false), exclude heritage provisions entirely
  // 2. If heritage=true with HCA, exclude heritage from non-condition layers (comes from queryHeritageByHca)
  // 3. If heritage=true without HCA, include heritage but filter by precinct
  if (!filters.heritage && layer !== 'condition') {
    // Property is not heritage - exclude all heritage provisions
    sql += ` AND LOWER(v2_topic) != 'heritage'`;
  } else if (filters.hca && layer !== 'condition') {
    // Heritage with HCA - exclude from non-condition layers (handled by queryHeritageByHca)
    sql += ` AND LOWER(v2_topic) != 'heritage'`;
  } else if (filters.heritage && !filters.hca && layer !== 'condition') {
    // Heritage without HCA - include but filter by precinct to avoid showing ALL precincts
    if (filters.precinct_id) {
      sql += ` AND (LOWER(v2_topic) != 'heritage' OR v2_precinct_id IS NULL OR v2_precinct_id = $${paramIndex++})`;
      params.push(filters.precinct_id);
    } else {
      // No precinct specified - only show non-precinct heritage provisions
      sql += ` AND (LOWER(v2_topic) != 'heritage' OR v2_precinct_id IS NULL)`;
    }
  }

  // Layer-specific filtering
  if (layer === 'use_specific' && filters.zone) {
    // For use-specific layer, filter by zone applicability
    sql += ` AND (v2_applicable_zones IS NULL OR $${paramIndex++} = ANY(v2_applicable_zones))`;
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

  if (layer === 'precinct' && filters.precinct_id) {
    // For precinct layer, filter by precinct ID
    sql += ` AND v2_precinct_id = $${paramIndex++}`;
    params.push(filters.precinct_id);
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
