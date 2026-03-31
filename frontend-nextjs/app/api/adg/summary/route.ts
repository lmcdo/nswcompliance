import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { getSEPPCache, createCacheKey } from '@/lib/cache';
import { ComplianceCheckSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

// Key metrics to display in summary card (in order of importance)
const KEY_METRICS = [
  { criteriaId: '4A-1', label: 'Solar Access' },
  { criteriaId: '4B-1', label: 'Natural Ventilation' },
  { criteriaId: '3F-1', label: 'Building Separation' },
  { criteriaId: '3D-1', label: 'Communal Open Space' },
  { criteriaId: '3E-1', label: 'Deep Soil' },
  { criteriaId: '4C-1', label: 'Ceiling Heights' },
  { criteriaId: '4D-1', label: 'Apartment Sizes' },
  { criteriaId: '4G-1', label: 'Storage' }
];

interface SummaryMetric {
  criteriaId: string;
  label: string;
  summary: string;
  numericValue: number | null;
  numericUnit: string | null;
  secondaryValue: number | null;
  secondaryUnit: string | null;
  sectionCode: string;
  sourcePage: number;
  sourceUrl: string;
  pdfUrl: string | null;
}

/**
 * Fetch ADG Summary for multi-dwelling developments
 *
 * GET /api/adg/summary
 *
 * Returns: Key ADG metrics for display in summary card
 */
export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    // Check cache first
    const cacheKey = createCacheKey('adg-summary', {});
    const cache = getSEPPCache();
    const cached = cache.get(cacheKey);

    if (cached) {
      console.log(`[ADG Summary API] Cache HIT: ${cacheKey}`);
      return NextResponse.json({
        ...cached,
        metadata: {
          ...cached.metadata,
          fromCache: true,
          cacheHit: true
        }
      });
    }

    console.log(`[ADG Summary API] Cache MISS: ${cacheKey}`);

    const pool = getPool();

    // Fetch key metrics
    const criteriaIds = KEY_METRICS.map(m => m.criteriaId);
    const placeholders = criteriaIds.map((_, i) => `$${i + 1}`).join(', ');

    const query = `
      SELECT
        criteria_id,
        section_code,
        requirement_summary,
        numeric_value,
        numeric_unit,
        secondary_value,
        secondary_unit,
        source_page,
        source_url,
        r2_pdf_url
      FROM sepp_adg_requirements
      WHERE criteria_id IN (${placeholders})
    `;

    const result = await pool.query(query, criteriaIds);

    // Map results to summary metrics (preserve KEY_METRICS order)
    const metricsMap = new Map(result.rows.map(row => [row.criteria_id, row]));

    const summaryMetrics: SummaryMetric[] = KEY_METRICS
      .map(metric => {
        const row = metricsMap.get(metric.criteriaId);
        if (!row) return null;
        return {
          criteriaId: row.criteria_id,
          label: metric.label,
          summary: row.requirement_summary,
          numericValue: row.numeric_value ? parseFloat(row.numeric_value) : null,
          numericUnit: row.numeric_unit,
          secondaryValue: row.secondary_value ? parseFloat(row.secondary_value) : null,
          secondaryUnit: row.secondary_unit,
          sectionCode: row.section_code,
          sourcePage: row.source_page,
          sourceUrl: row.source_url,
          pdfUrl: row.r2_pdf_url ?? null
        };
      })
      .filter((m): m is SummaryMetric => m !== null);

    // Get total count
    const countResult = await pool.query(
      `SELECT COUNT(*) as count FROM sepp_adg_requirements WHERE requirement_type = 'design_criteria'`
    );
    const totalCriteria = parseInt(countResult.rows[0].count);

    const processingTime = Date.now() - startTime;

    const response = {
      success: true,
      data: {
        keyMetrics: summaryMetrics,
        totalCriteria,
        appliesTo: ['residential_flat', 'multi_dwelling', 'shop_top_housing'],
        documentInfo: {
          name: 'NSW Apartment Design Guide',
          version: 'March 2023',
          authority: 'SEPP (Housing) 2021',
          legalStatus: 'statutory',
          parts: [
            { number: 3, name: 'Siting the Development', pages: '43-76' },
            { number: 4, name: 'Designing the Building', pages: '77-148' }
          ]
        }
      },
      metadata: {
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString(),
        fromCache: false
      }
    };

    // Cache the response (ADG data is static)
    cache.set(cacheKey, response);
    console.log(`[ADG Summary API] Cached: ${cacheKey}`);

    return NextResponse.json(response);

  } catch (error) {
    console.error('[ADG Summary API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}
