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
import { Pool } from 'pg';

// Database pool with 30-second timeout per CLAUDE.md
// SSL required for Supabase pooler (port 6543)
const rawDbUrl = process.env.DATABASE_URL || process.env.SUPABASE_DB_URL;
const isSupabase = rawDbUrl?.includes('supabase');
const isProduction = process.env.NODE_ENV === 'production';

// Parse URL and use individual params to ensure SSL config is respected
let poolConfig: any = {
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 10000,
  statement_timeout: 30000,
  query_timeout: 30000,
};

if (rawDbUrl) {
  const url = new URL(rawDbUrl);
  poolConfig.host = url.hostname;
  poolConfig.port = parseInt(url.port) || 5432;
  poolConfig.user = decodeURIComponent(url.username);
  poolConfig.password = decodeURIComponent(url.password);
  poolConfig.database = url.pathname.slice(1);

  if (isSupabase || isProduction) {
    poolConfig.ssl = {
      rejectUnauthorized: false,
      requestCert: false,
    };
  }
}

const pool = new Pool(poolConfig);

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
    };

    console.log(`[4-Layer API] Filters: ${JSON.stringify(filters)}`);

    const client = await pool.connect();

    try {
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

      return NextResponse.json({
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

async function queryLayer(
  client: any,
  layer: string,
  filters: PropertyFilters
): Promise<any[]> {
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

  // Layer-specific filtering
  if (layer === 'use_specific' && filters.zone) {
    // For use-specific layer, filter by zone applicability
    sql += ` AND (v2_applicable_zones IS NULL OR $${paramIndex++} = ANY(v2_applicable_zones))`;
    params.push(filters.zone);
  }

  if (layer === 'condition') {
    // For condition layer, only include if property has that condition
    const conditions: string[] = [];
    if (filters.heritage) conditions.push('heritage');
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
  if (filters.dev_type) {
    // Expand dev_type to include parent types (e.g., dwelling_addition_rear -> [dwelling_addition_rear, dwelling_addition, dwelling_house])
    // Include provisions tagged with 'ALL' (applies to all development types)
    const expandedTypes = expandDevTypeHierarchy(filters.dev_type);
    sql += ` AND (v2_applicable_dev_types && $${paramIndex++}::text[] OR 'ALL' = ANY(v2_applicable_dev_types))`;
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
