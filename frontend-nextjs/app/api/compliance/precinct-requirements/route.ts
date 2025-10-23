import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

/**
 * Week 3: Categorized Precinct Requirements API
 * Returns LLM-categorized requirements from dcp_precinct_requirements table
 */

interface PrecinctRequirementQuery {
  address?: string;
  precinctId?: string;
  precinctName?: string;
  lga?: string;
}

interface CategorizedRequirement {
  id: number;
  category: string;
  subcategory?: string;
  requirement_text: string;
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  confidence: 'high' | 'medium' | 'low';
  confidence_score?: number;
  has_conditionals: boolean;
  conditional_text?: string;
  validated: boolean;
  validated_by?: string;
  validated_at?: string;
  source_provision_ids: number[];
  source_document_ids: string[];
  pdf_pages?: number[];
  extraction_context?: any;
}

interface CategoryGroup {
  category: string;
  display_name: string;
  requirements: CategorizedRequirement[];
  total_count: number;
  high_confidence_count: number;
  validated_count: number;
}

export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: PrecinctRequirementQuery = await request.json();
    const { address, precinctId, precinctName, lga } = body;

    // Must provide at least one identifier
    if (!precinctId && !precinctName && !address) {
      return NextResponse.json({
        success: false,
        error: 'Must provide precinctId, precinctName, or address'
      }, { status: 400 });
    }

    // Query categorized requirements
    let requirementsQuery = `
      SELECT
        pr.id,
        pr.precinct_id,
        pr.precinct_name,
        pr.lga,
        pr.category,
        pr.subcategory,
        pr.requirement_text,
        pr.value_numeric,
        pr.value_min,
        pr.value_max,
        pr.unit,
        pr.confidence,
        pr.confidence_score,
        pr.has_conditionals,
        pr.conditional_text,
        pr.validated,
        pr.validated_by,
        pr.validated_at,
        pr.source_provision_ids,
        pr.source_document_ids,
        pr.pdf_pages,
        pr.extraction_context,
        rc.display_name as category_display_name
      FROM dcp_precinct_requirements pr
      LEFT JOIN requirement_categories rc ON pr.category = rc.category
      WHERE 1=1
    `;

    const queryParams: any[] = [];
    let paramIndex = 1;

    if (precinctId) {
      requirementsQuery += ` AND pr.precinct_id = $${paramIndex}`;
      queryParams.push(precinctId);
      paramIndex++;
    }

    if (precinctName) {
      requirementsQuery += ` AND pr.precinct_name ILIKE $${paramIndex}`;
      queryParams.push(`%${precinctName}%`);
      paramIndex++;
    }

    if (lga) {
      requirementsQuery += ` AND pr.lga ILIKE $${paramIndex}`;
      queryParams.push(`%${lga}%`);
      paramIndex++;
    }

    // Order by category and confidence
    requirementsQuery += `
      ORDER BY
        CASE pr.confidence
          WHEN 'high' THEN 1
          WHEN 'medium' THEN 2
          WHEN 'low' THEN 3
        END,
        pr.category,
        pr.subcategory,
        pr.id
    `;

    console.log('[Precinct Requirements API] Query params:', queryParams);

    const result = await query(requirementsQuery, queryParams);

    console.log(`[Precinct Requirements API] Found ${result.rows.length} requirements`);

    // Group by category
    const categoryGroups: Map<string, CategoryGroup> = new Map();

    for (const row of result.rows) {
      const category = row.category;
      const displayName = row.category_display_name || category.replace(/_/g, ' ');

      if (!categoryGroups.has(category)) {
        categoryGroups.set(category, {
          category,
          display_name: displayName,
          requirements: [],
          total_count: 0,
          high_confidence_count: 0,
          validated_count: 0
        });
      }

      const group = categoryGroups.get(category)!;
      group.requirements.push({
        id: row.id,
        category: row.category,
        subcategory: row.subcategory,
        requirement_text: row.requirement_text,
        value_numeric: row.value_numeric,
        value_min: row.value_min,
        value_max: row.value_max,
        unit: row.unit,
        confidence: row.confidence,
        confidence_score: row.confidence_score,
        has_conditionals: row.has_conditionals,
        conditional_text: row.conditional_text,
        validated: row.validated,
        validated_by: row.validated_by,
        validated_at: row.validated_at,
        source_provision_ids: row.source_provision_ids || [],
        source_document_ids: row.source_document_ids || [],
        pdf_pages: row.pdf_pages || [],
        extraction_context: row.extraction_context
      });

      group.total_count++;
      if (row.confidence === 'high') group.high_confidence_count++;
      if (row.validated) group.validated_count++;
    }

    // Convert map to array and sort by count (descending)
    const categories = Array.from(categoryGroups.values()).sort(
      (a, b) => b.total_count - a.total_count
    );

    // Calculate overall metrics
    const totalRequirements = result.rows.length;
    const highConfidence = result.rows.filter((r: any) => r.confidence === 'high').length;
    const validated = result.rows.filter((r: any) => r.validated).length;
    const withConditionals = result.rows.filter((r: any) => r.has_conditionals).length;

    // Get precinct info if we have results
    let precinctInfo = null;
    if (result.rows.length > 0) {
      const firstRow = result.rows[0];
      precinctInfo = {
        precinct_id: firstRow.precinct_id,
        precinct_name: firstRow.precinct_name,
        lga: firstRow.lga
      };
    }

    const processingTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        precinct: precinctInfo,
        categories,
        raw_requirements: result.rows  // Include raw data for debugging
      },
      metrics: {
        total_requirements: totalRequirements,
        high_confidence_count: highConfidence,
        high_confidence_percent: totalRequirements > 0 ? Math.round((highConfidence / totalRequirements) * 100) : 0,
        validated_count: validated,
        validated_percent: totalRequirements > 0 ? Math.round((validated / totalRequirements) * 100) : 0,
        with_conditionals: withConditionals,
        category_count: categories.length
      },
      metadata: {
        query: {
          precinct_id: precinctId,
          precinct_name: precinctName,
          lga
        },
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[Precinct Requirements API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}

/**
 * GET endpoint for testing
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const precinctId = searchParams.get('precinctId');
  const precinctName = searchParams.get('precinctName');
  const lga = searchParams.get('lga');

  // Convert to POST body and call POST handler
  const mockRequest = {
    json: async () => ({
      precinctId: precinctId || undefined,
      precinctName: precinctName || undefined,
      lga: lga || undefined
    })
  } as NextRequest;

  return POST(mockRequest);
}
