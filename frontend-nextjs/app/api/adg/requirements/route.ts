import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';
import { getSEPPCache, createCacheKey } from '@/lib/cache';
import { ComplianceCheckSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';


export const dynamic = 'force-dynamic';
// Database connection (PRP-A1 compliant)
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : undefined,
  statement_timeout: 30000  // 30 second timeout
});

interface ADGRequirement {
  id: number;
  sectionCode: string;
  sectionName: string;
  criteriaNumber: number;
  criteriaId: string;
  requirementType: string;
  requirementText: string;
  requirementSummary: string;
  hasNumericStandard: boolean;
  numericValue: number | null;
  numericUnit: string | null;
  numericComparator: string | null;
  secondaryValue: number | null;
  secondaryUnit: string | null;
  metricCategory: string;
  appliesTo: string[];
  buildingHeightCategory: string;
  sourcePdf: string;
  sourcePage: number;
  sourceUrl: string;
  authorityReference: string;
}

/**
 * Fetch ADG Design Criteria
 *
 * GET /api/adg/requirements
 * Query params:
 *   - section: Filter by section code (3D, 4A, etc.)
 *   - metric: Filter by metric category (solar_access, ventilation, etc.)
 *   - numeric_only: Only return criteria with numeric standards (true/false)
 *
 * Returns: All ADG Design Criteria matching filters
 */
export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;
    const section = searchParams.get('section');
    const metric = searchParams.get('metric');
    const numericOnly = searchParams.get('numeric_only') === 'true';

    // Check cache first
    const cacheKey = createCacheKey('adg-requirements', {
      section: section || 'all',
      metric: metric || 'all',
      numericOnly: numericOnly.toString()
    });
    const cache = getSEPPCache();
    const cached = cache.get(cacheKey);

    if (cached) {
      console.log(`[ADG Requirements API] Cache HIT: ${cacheKey}`);
      return NextResponse.json({
        ...cached,
        metadata: {
          ...cached.metadata,
          fromCache: true,
          cacheHit: true
        }
      });
    }

    console.log(`[ADG Requirements API] Cache MISS: ${cacheKey}`);

    // Build query
    let query = `
      SELECT
        id,
        section_code,
        section_name,
        criteria_number,
        criteria_id,
        requirement_type,
        requirement_text,
        requirement_summary,
        has_numeric_standard,
        numeric_value,
        numeric_unit,
        numeric_comparator,
        secondary_value,
        secondary_unit,
        metric_category,
        applies_to,
        building_height_category,
        source_pdf,
        source_page,
        source_url,
        authority_reference
      FROM sepp_adg_requirements
      WHERE requirement_type = 'design_criteria'
    `;

    const params: any[] = [];
    let paramIndex = 1;

    if (section) {
      query += ` AND section_code = $${paramIndex}`;
      params.push(section);
      paramIndex++;
    }

    if (metric) {
      query += ` AND metric_category = $${paramIndex}`;
      params.push(metric);
      paramIndex++;
    }

    if (numericOnly) {
      query += ` AND has_numeric_standard = true`;
    }

    query += ` ORDER BY section_code, criteria_number`;

    const result = await pool.query(query, params);

    console.log(`[ADG Requirements API] Found ${result.rows.length} requirements`);

    // Format response
    const requirements: ADGRequirement[] = result.rows.map(row => ({
      id: row.id,
      sectionCode: row.section_code,
      sectionName: row.section_name,
      criteriaNumber: row.criteria_number,
      criteriaId: row.criteria_id,
      requirementType: row.requirement_type,
      requirementText: row.requirement_text,
      requirementSummary: row.requirement_summary,
      hasNumericStandard: row.has_numeric_standard,
      numericValue: row.numeric_value ? parseFloat(row.numeric_value) : null,
      numericUnit: row.numeric_unit,
      numericComparator: row.numeric_comparator,
      secondaryValue: row.secondary_value ? parseFloat(row.secondary_value) : null,
      secondaryUnit: row.secondary_unit,
      metricCategory: row.metric_category,
      appliesTo: row.applies_to,
      buildingHeightCategory: row.building_height_category,
      sourcePdf: row.source_pdf,
      sourcePage: row.source_page,
      sourceUrl: row.source_url,
      authorityReference: row.authority_reference
    }));

    const processingTime = Date.now() - startTime;

    const response = {
      success: true,
      data: {
        requirements,
        count: requirements.length,
        filters: {
          section: section || 'all',
          metric: metric || 'all',
          numericOnly
        }
      },
      metadata: {
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString(),
        source: 'NSW Apartment Design Guide (March 2023)',
        authority: 'SEPP (Housing) 2021',
        fromCache: false
      }
    };

    // Cache the response (ADG data is static)
    cache.set(cacheKey, response);
    console.log(`[ADG Requirements API] Cached: ${cacheKey}`);

    return NextResponse.json(response);

  } catch (error) {
    console.error('[ADG Requirements API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
