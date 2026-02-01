/**
 * DRAFT: Provisions for Property API - 4-Layer Filtering with Relevance Scoring
 *
 * CHANGES FROM CURRENT VERSION:
 * 1. REMOVED dev_type exclusion filtering (legal compliance issue per EP&A Act s 4.15)
 * 2. ADDED relevance scoring based on dev_type matching
 * 3. ALL provisions returned, ranked by relevance to user's dev_type
 *
 * Legal Basis:
 * - EP&A Act s 4.15 requires considering ALL relevant DCP provisions achieving objectives
 * - Dev type listings are ADVISORY, not exclusive (*Wehbe v Pittwater Council* NSWLEC 827)
 * - Consent authorities use inclusive approach (Inner West practice)
 * - Excluding provisions = high liability risk for missed merits-based application
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
 * - dev_type: Development type (OPTIONAL - used for relevance scoring, NOT filtering)
 * - topic: Filter by topic (optional)
 * - groupBy: "topic" (default) or "toc" - how to group results
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';


export const dynamic = 'force-dynamic';
interface PropertyFilters {
  lga?: string;
  zone?: string;
  heritage?: boolean;
  flood?: boolean;
  bushfire?: boolean;
  precinct_id?: string;
  dev_type?: string;  // NOW OPTIONAL: Used for relevance scoring, not exclusion
  topic?: string;
  assessment_type?: 'CDC' | 'DA';
  former_council?: string;
  hca?: string;
  groupBy?: 'topic' | 'toc';
}

interface LayerResult {
  layer: string;
  layer_name: string;
  provisions: any[];
  count: number;
}

/**
 * Relevance levels for dev_type matching
 * - primary: Provision explicitly lists user's dev_type (most relevant)
 * - general: Provision applies universally (NULL or 'ALL')
 * - secondary: Provision lists other dev_types but may apply if objectives relevant
 */
type RelevanceLevel = 'primary' | 'general' | 'secondary';

interface ProvisionWithRelevance {
  id: number;
  provision_text: string;
  relevance_level: RelevanceLevel;
  relevance_reason: string;
  // ... other provision fields
}

/**
 * Normalize precinct ID format for database lookup
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

  return precinctId;
}

/**
 * Dev type hierarchy for relevance scoring
 * Expands specific types to include parent types (e.g., dwelling_house_new -> dwelling_house)
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

  // Simplified category groupings
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
 * Expand a dev_type to its full hierarchy for relevance matching
 */
function expandDevTypeHierarchy(devType: string): string[] {
  if (DEV_TYPE_HIERARCHY[devType]) {
    return DEV_TYPE_HIERARCHY[devType];
  }
  return [devType];
}

/**
 * Lookup db_slug from heritage_conservation_areas by h_id (Planning Portal C-code)
 */
async function resolveHcaCode(client: any, hcaCode: string): Promise<string | null> {
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
    const searchParams = request.nextUrl.searchParams;

    // Parse filters
    const filters: PropertyFilters = {
      lga: searchParams.get('lga') || undefined,
      zone: searchParams.get('zone') || undefined,
      heritage: searchParams.get('heritage') === 'true',
      flood: searchParams.get('flood') === 'true',
      bushfire: searchParams.get('bushfire') === 'true',
      precinct_id: searchParams.get('precinct_id') ? normalizePrecinctId(searchParams.get('precinct_id')!) : undefined,
      dev_type: searchParams.get('dev_type') || undefined,  // OPTIONAL: For relevance only
      topic: searchParams.get('topic') || undefined,
      assessment_type: (searchParams.get('assessment_type') as 'CDC' | 'DA') || undefined,
      former_council: searchParams.get('former_council') || undefined,
      hca: searchParams.get('hca') || undefined,
      groupBy: (searchParams.get('groupBy') as 'topic' | 'toc') || 'topic',
    };

    console.log(`[4-Layer API v2 Relevance] Filters: ${JSON.stringify(filters)}`);

    const pool = getPool();
    const client = await pool.connect();

    try {
      // Resolve HCA code
      if (filters.hca) {
        const resolvedHca = await resolveHcaCode(client, filters.hca);
        if (resolvedHca) {
          filters.hca = resolvedHca;
        } else {
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

      const adjustedResults = results;
      const totalCount = adjustedResults.reduce((sum, r) => sum + r.count, 0);
      const responseTime = Date.now() - startTime;

      // Group provisions based on groupBy parameter
      const byTopic = groupByTopic(adjustedResults);
      const byToc = filters.groupBy === 'toc'
        ? groupByTocStructure(adjustedResults, filters.former_council)
        : undefined;

      // Relevance summary if dev_type provided
      const relevanceSummary = filters.dev_type ? calculateRelevanceSummary(adjustedResults) : undefined;

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
            relevance_breakdown: relevanceSummary,  // NEW: Relevance stats
          }
        },
        meta: {
          filters_applied: filters,
          dev_type_approach: filters.dev_type
            ? 'inclusive_with_relevance_scoring'
            : 'show_all_provisions',
          legal_note: 'All provisions shown per EP&A Act s 4.15 (consider all relevant provisions). Dev type used for relevance ranking only.',
          response_time_ms: responseTime,
          api_version: 'v3_relevance_scoring'
        }
      });

      response.headers.set('Cache-Control', 'no-store, must-revalidate');
      return response;

    } finally {
      client.release();
    }

  } catch (error) {
    console.error('[4-Layer API v2] Error:', error);
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
 * Calculate relevance summary for provisions when dev_type is provided
 */
function calculateRelevanceSummary(layers: LayerResult[]): any {
  const summary = {
    primary: 0,
    general: 0,
    secondary: 0,
  };

  for (const layer of layers) {
    for (const provision of layer.provisions) {
      if (provision.relevance_level) {
        summary[provision.relevance_level as RelevanceLevel]++;
      }
    }
  }

  return summary;
}

/**
 * Query heritage provisions filtered by specific HCA
 */
async function queryHeritageByHca(
  client: any,
  filters: PropertyFilters
): Promise<any[]> {
  const params: any[] = [];
  let paramIndex = 1;

  // Build relevance scoring for dev_type
  let relevanceSelect = '';
  if (filters.dev_type) {
    const expandedTypes = expandDevTypeHierarchy(filters.dev_type);
    relevanceSelect = `,
      CASE
        WHEN v2_applicable_dev_types && $${paramIndex++}::text[] THEN 'primary'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'general'
        ELSE 'secondary'
      END as relevance_level,
      CASE
        WHEN v2_applicable_dev_types && $${paramIndex}::text[] THEN 'Specifically written for ${filters.dev_type}'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'Applies to all development types'
        ELSE 'May apply if objectives relevant (EP&A Act s 4.15)'
      END as relevance_reason
    `;
    params.push(expandedTypes, expandedTypes);
  } else {
    relevanceSelect = `, NULL as relevance_level, NULL as relevance_reason`;
  }

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
      v2_heritage_hca,
      v2_applicable_dev_types
      ${relevanceSelect}
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND (LOWER(v2_topic) = 'heritage' OR v2_topic = 'Heritage')
      AND (
        v2_heritage_hca IS NULL
        OR v2_heritage_hca = $${paramIndex++}
      )
  `;
  params.push(filters.hca);

  // Filter by former council
  if (filters.former_council) {
    const councilName = filters.former_council.charAt(0).toUpperCase() + filters.former_council.slice(1).toLowerCase();
    sql += ` AND document_id ILIKE $${paramIndex++}`;
    params.push(`%${councilName}%`);
  }

  // Filter by precinct
  if (filters.precinct_id) {
    sql += ` AND (v2_precinct_id IS NULL OR v2_precinct_id = $${paramIndex++})`;
    params.push(filters.precinct_id);
  } else {
    sql += ` AND v2_precinct_id IS NULL`;
  }

  sql += ` ORDER BY v2_dcp_part, id LIMIT 200`;

  const result = await client.query(sql, params);
  return result.rows;
}

/**
 * Enrich provisions with TOC section info
 */
async function enrichWithTocSections(
  client: any,
  provisions: any[]
): Promise<any[]> {
  if (provisions.length === 0) return provisions;

  const docPages = provisions
    .filter(p => p.pdf_page != null)
    .map(p => ({ doc_id: p.document_id, page: p.pdf_page, id: p.id }));

  if (docPages.length === 0) return provisions;

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

/**
 * Query heritage provisions from dcp_general_requirements
 */
async function queryHeritageFromDcpGeneralRequirements(
  client: any,
  filters: PropertyFilters
): Promise<any[]> {
  const params: any[] = [];
  let paramIndex = 1;

  // Build relevance scoring
  let relevanceSelect = '';
  if (filters.dev_type) {
    const expandedTypes = expandDevTypeHierarchy(filters.dev_type);
    relevanceSelect = `,
      'general' as relevance_level,
      'Applies to all development types' as relevance_reason
    `;
  } else {
    relevanceSelect = `, NULL as relevance_level, NULL as relevance_reason`;
  }

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
      NULL as v2_applicable_dev_types,
      INITCAP(REPLACE(category, '_', ' ')) as v2_heritage_subcategory
      ${relevanceSelect}
    FROM dcp_general_requirements
    WHERE (category = 'heritage' OR part_name ILIKE '%Heritage%')
    AND (part_name IS NULL OR part_name NOT IN ('Energy Management', 'Waste Management', 'Landscaping and Open Spaces', 'Fencing'))
  `;

  if (filters.former_council) {
    const councilName = filters.former_council.charAt(0).toUpperCase() + filters.former_council.slice(1).toLowerCase();
    sql += ` AND former_council = $${paramIndex++}`;
    params.push(councilName);
  }

  sql += ` ORDER BY part_name, id LIMIT 500`;

  const result = await client.query(sql, params);
  return result.rows;
}

/**
 * Query layer with RELEVANCE SCORING instead of dev_type FILTERING
 *
 * CRITICAL CHANGE: dev_type parameter NO LONGER filters provisions out.
 * Instead, it adds relevance_level and relevance_reason metadata to each provision.
 */
async function queryLayer(
  client: any,
  layer: string,
  filters: PropertyFilters
): Promise<any[]> {
  // For condition layer with heritage, use appropriate source
  const isAshfield = filters.former_council?.toLowerCase() === 'ashfield';
  if (layer === 'condition' && (filters.heritage || isAshfield)) {
    if (filters.hca) {
      return queryHeritageByHca(client, filters);
    }
    return queryHeritageFromDcpGeneralRequirements(client, filters);
  }

  const params: any[] = [];
  let paramIndex = 1;

  // Build relevance scoring for dev_type (NOT filtering!)
  let relevanceSelect = '';
  if (filters.dev_type) {
    const expandedTypes = expandDevTypeHierarchy(filters.dev_type);
    relevanceSelect = `,
      CASE
        WHEN v2_applicable_dev_types && $${paramIndex++}::text[] THEN 'primary'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'general'
        ELSE 'secondary'
      END as relevance_level,
      CASE
        WHEN v2_applicable_dev_types && $${paramIndex}::text[] THEN 'Specifically written for ${filters.dev_type}'
        WHEN v2_applicable_dev_types IS NULL OR 'ALL' = ANY(v2_applicable_dev_types) THEN 'Applies to all development types'
        ELSE 'May apply if objectives relevant (EP&A Act s 4.15)'
      END as relevance_reason
    `;
    params.push(expandedTypes, expandedTypes);
  } else {
    relevanceSelect = `, NULL as relevance_level, NULL as relevance_reason`;
  }

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
      v2_heritage_hca,
      v2_applicable_dev_types
      ${relevanceSelect}
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = $${paramIndex++}
  `;
  params.push(layer);

  // Filter by former council
  if (filters.former_council) {
    const councilName = filters.former_council.charAt(0).toUpperCase() + filters.former_council.slice(1).toLowerCase();
    sql += ` AND document_id ILIKE $${paramIndex++}`;
    params.push(`%${councilName}%`);
  }

  // Heritage filtering logic (unchanged)
  if (!filters.heritage && layer !== 'condition' && layer !== 'precinct') {
    sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
  } else if (filters.hca && layer !== 'condition' && layer !== 'precinct') {
    sql += ` AND (LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage'))`;
  } else if (filters.heritage && !filters.hca && layer !== 'condition' && layer !== 'precinct') {
    if (filters.precinct_id) {
      sql += ` AND ((LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage')) OR v2_precinct_id IS NULL OR v2_precinct_id = $${paramIndex++})`;
      params.push(filters.precinct_id);
    } else {
      sql += ` AND ((LOWER(v2_topic) != 'heritage' AND (v2_marker IS NULL OR v2_marker != 'heritage')) OR v2_precinct_id IS NULL)`;
    }
  }

  // Layer-specific filtering
  if (layer === 'use_specific' && filters.zone) {
    sql += ` AND (v2_applicable_zones IS NULL OR $${paramIndex++} = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))`;
    params.push(filters.zone);
  }

  if (layer === 'condition') {
    const conditions: string[] = [];
    if (filters.flood) conditions.push('flood');
    if (filters.bushfire) conditions.push('bushfire');

    if (conditions.length === 0) {
      return [];
    }

    sql += ` AND v2_site_condition_required = ANY($${paramIndex++}::text[])`;
    params.push(conditions);
  }

  if (layer === 'precinct') {
    if (filters.precinct_id) {
      console.log(`[4-Layer API v2] Precinct filter: v2_precinct_id = '${filters.precinct_id}'`);
      sql += ` AND v2_precinct_id = $${paramIndex++}`;
      params.push(filters.precinct_id);
    } else {
      console.log(`[4-Layer API v2] No precinct_id provided - excluding all precinct provisions`);
      sql += ` AND v2_precinct_id IS NULL`;
    }
  }

  // Optional topic filter
  if (filters.topic) {
    sql += ` AND LOWER(REPLACE(v2_topic, ' ', '_')) = LOWER($${paramIndex++})`;
    params.push(filters.topic.replace(/ /g, '_'));
  }

  // ⚠️ CRITICAL CHANGE: NO dev_type filtering here!
  // Old code (line 625-631) REMOVED:
  // if (filters.dev_type) {
  //   sql += ` AND (v2_applicable_dev_types && $expandedTypes ...)`;  // ❌ DELETED
  // }
  // Dev type now only affects relevance scoring (added in SELECT above)

  // Assessment type filter
  if (filters.assessment_type === 'CDC') {
    sql += ` AND v2_provision_type = 'control' AND v2_has_numeric_value = true`;
  }

  sql += ` ORDER BY
    CASE
      WHEN relevance_level = 'primary' THEN 1
      WHEN relevance_level = 'general' THEN 2
      WHEN relevance_level = 'secondary' THEN 3
      ELSE 4
    END,
    v2_topic, v2_dcp_part, id
    LIMIT 500`;

  const result = await client.query(sql, params);
  return result.rows;
}

function groupByTopic(layers: LayerResult[]): Record<string, any[]> {
  const byTopic: Record<string, any[]> = {};

  for (const layer of layers) {
    for (const provision of layer.provisions) {
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

interface TocSection {
  section_id: string;
  section_title: string;
  provision_count: number;
  provisions: any[];
  sub_groups?: Record<string, TocSection>;
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

  const provisionMap = new Map<number, any>();
  for (const layer of layers) {
    for (const provision of layer.provisions) {
      if (!provisionMap.has(provision.id)) {
        provisionMap.set(provision.id, { ...provision, layer: layer.layer });
      }
    }
  }

  const textDeduped = new Map<string, any>();
  const idDedupedProvisions = [...provisionMap.values()];
  for (const provision of idDedupedProvisions) {
    const textKey = `${(provision.provision_text || '').substring(0, 100)}|${provision.pdf_page || 0}`;
    if (!textDeduped.has(textKey)) {
      textDeduped.set(textKey, provision);
    }
  }
  const allProvisions = [...textDeduped.values()];

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

    let sectionId = provision.toc_section_number || 'unsectioned';
    let sectionTitle = provision.toc_section_title || 'General';

    const isLeichhardtPartC = formerCouncil?.toLowerCase() === 'leichhardt' &&
      partId?.includes('Part C') && partId?.includes('Section 1');

    if (isLeichhardtPartC && provision.v2_marker) {
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

  for (const partId of Object.keys(byToc)) {
    const sortedSections: Record<string, TocSection> = {};
    const sectionKeys = Object.keys(byToc[partId].sections).sort((a, b) => {
      if (a.startsWith('C') && b.startsWith('C')) {
        const numA = parseInt(a.slice(1)) || 0;
        const numB = parseInt(b.slice(1)) || 0;
        return numA - numB;
      }
      return a.localeCompare(b, undefined, { numeric: true });
    });
    for (const key of sectionKeys) {
      sortedSections[key] = byToc[partId].sections[key];
    }
    byToc[partId].sections = sortedSections;
  }

  return byToc;
}

function formatPartName(partId: string): string {
  if (!partId || partId === 'Other') return 'Other Provisions';
  if (partId.includes(':')) return partId;

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
