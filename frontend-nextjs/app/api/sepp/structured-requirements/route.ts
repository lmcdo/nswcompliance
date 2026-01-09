import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { getSEPPCache, createCacheKey } from '@/lib/cache';

interface StructuredRequirementsRequest {
  seppId: string;  // e.g. "sustainable_buildings_2022"
  developmentType: string;  // e.g. "dwelling_house", "commercial"
  schedule?: string;  // Optional: filter by schedule number
}

interface RequirementCategory {
  name: string;
  reference: string;
  requirements: Array<{
    [key: string]: string;
  }>;
}

interface StructuredRequirement {
  id: number;
  seppId: string;
  seppName: string;
  schedule: string;
  scheduleName: string;
  section: string | null;
  sectionName: string | null;
  developmentTypeCategory: string;
  requirementData: {
    title: string;
    categories: RequirementCategory[];
  };
  sourceProvisionId: number | null;
  pdfPageImageUrl: string | null;
  pdfPage: number | null;
}

/**
 * Fetch structured SEPP requirements (manually curated, 100% reliable)
 *
 * POST /api/sepp/structured-requirements
 * Body: { seppId, developmentType, schedule? }
 *
 * Returns: Structured requirements with actionable checklist format
 */
export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: StructuredRequirementsRequest = await request.json();
    const { seppId, developmentType, schedule } = body;

    if (!seppId || !developmentType) {
      return NextResponse.json({
        success: false,
        error: 'Both seppId and developmentType are required'
      }, { status: 400 });
    }

    // Check cache first
    const cacheKey = createCacheKey('sepp-structured', { seppId, developmentType, schedule: schedule || 'all' });
    const cache = getSEPPCache();
    const cached = cache.get(cacheKey);

    if (cached) {
      console.log(`[Structured Requirements API] Cache HIT: ${cacheKey}`);
      return NextResponse.json({
        ...cached,
        metadata: {
          ...cached.metadata,
          fromCache: true,
          cacheHit: true
        }
      });
    }

    console.log(`[Structured Requirements API] Cache MISS: ${cacheKey}`);
    console.log(`[Structured Requirements API] Query: seppId=${seppId}, developmentType=${developmentType}, schedule=${schedule}`);

    // Map development type to category
    const residentialTypes = [
      'dwelling_house',
      'secondary_dwelling',
      'multi_dwelling',
      'residential_flat',
      'boarding_house',
      'dual_occupancy',
      'semi_detached',
      'attached_dwelling'
    ];

    const commercialTypes = [
      'commercial',
      'shop_top_housing',
      'retail',
      'office',
      'business_premises',
      'industrial'
    ];

    let developmentCategory: string;
    if (residentialTypes.includes(developmentType)) {
      developmentCategory = 'residential';
    } else if (commercialTypes.includes(developmentType)) {
      developmentCategory = 'commercial';
    } else {
      developmentCategory = 'mixed';
    }

    console.log(`[Structured Requirements API] Development category: ${developmentCategory}`);

    // Build query with LEFT JOIN to get PDF URLs
    let query = `
      SELECT
        ssr.id,
        ssr.sepp_id,
        ssr.sepp_name,
        ssr.schedule,
        ssr.schedule_name,
        ssr.section,
        ssr.section_name,
        ssr.development_type_category,
        ssr.requirement_data,
        ssr.source_provision_id,
        rp.pdf_page_image_url,
        rp.pdf_page
      FROM sepp_structured_requirements ssr
      LEFT JOIN regulatory_provisions rp ON ssr.source_provision_id = rp.id
      WHERE ssr.sepp_id = $1
      AND (ssr.sepp_id = 'resilience_hazards_2021' OR ssr.development_type_category = $2)
    `;

    const params: any[] = [seppId, developmentCategory];

    // Optional schedule filter
    if (schedule) {
      query += ` AND schedule = $3`;
      params.push(schedule);
    }

    query += ` ORDER BY schedule, section`;

    console.log(`[Structured Requirements API] SQL:`, query);
    console.log(`[Structured Requirements API] Params:`, params);

    const pool = getPool();
    const result = await pool.query(query, params);

    console.log(`[Structured Requirements API] Found ${result.rows.length} structured requirements`);

    if (result.rows.length === 0) {
      return NextResponse.json({
        success: true,
        data: {
          hasStructuredRequirements: false,
          message: 'No manually curated requirements available for this SEPP and development type. Use full-text API instead.'
        },
        metadata: {
          processingTimeMs: Date.now() - startTime,
          timestamp: new Date().toISOString()
        }
      });
    }

    // Format response
    const structuredRequirements: StructuredRequirement[] = result.rows.map(row => ({
      id: row.id,
      seppId: row.sepp_id,
      seppName: row.sepp_name,
      schedule: row.schedule,
      scheduleName: row.schedule_name,
      section: row.section,
      sectionName: row.section_name,
      developmentTypeCategory: row.development_type_category,
      requirementData: row.requirement_data,
      sourceProvisionId: row.source_provision_id,
      pdfPageImageUrl: row.pdf_page_image_url,
      pdfPage: row.pdf_page
    }));

    const processingTime = Date.now() - startTime;

    const response = {
      success: true,
      data: {
        hasStructuredRequirements: true,
        requirements: structuredRequirements,
        count: structuredRequirements.length,
        developmentType,
        developmentCategory,
        seppId
      },
      metadata: {
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString(),
        fromCache: false
      }
    };

    // Cache the response (SEPP data is static)
    cache.set(cacheKey, response);
    console.log(`[Structured Requirements API] Cached: ${cacheKey}`);

    return NextResponse.json(response);

  } catch (error) {
    console.error('[Structured Requirements API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
