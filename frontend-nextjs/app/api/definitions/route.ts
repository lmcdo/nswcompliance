/**
 * Regulatory Definitions API
 *
 * Query the 465+ regulatory definitions extracted from:
 * - Marrickville DCP 2011
 * - Leichhardt DCP 2013
 * - Ashfield DCP 2016
 * - SEPP Housing 2021
 * - Inner West LEP 2022 Standard Instrument
 *
 * GET /api/definitions?term=habitable
 * GET /api/definitions?source=SEPP%20Housing%202021
 * GET /api/definitions?domain=heritage
 * GET /api/definitions?legislation_type=DCP
 */

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/database/pool-manager';


export const dynamic = 'force-dynamic';
interface DefinitionResult {
  id: number;
  term: string;
  definition_text: string;
  definition_summary: string | null;
  source_document: string;
  source_clause: string | null;
  legislation_type: string;
  lga: string | null;
  former_council: string | null;
  domain_tags: string[] | null;
  pdf_page: number | null;
  pdf_source_file: string | null;
}

interface DefinitionResponse {
  success: boolean;
  count: number;
  definitions: DefinitionResult[];
  meta: {
    term_searched?: string;
    filters_applied: Record<string, string>;
    response_time_ms: number;
  };
}

export async function GET(request: NextRequest): Promise<NextResponse<DefinitionResponse | { error: string; details?: string }>> {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;

    // Parse query parameters
    const term = searchParams.get('term');
    const source = searchParams.get('source');
    const domain = searchParams.get('domain');
    const legislationType = searchParams.get('legislation_type');
    const limit = Math.min(parseInt(searchParams.get('limit') || '50'), 200);
    const exact = searchParams.get('exact') === 'true';

    // Build dynamic query
    const conditions: string[] = [];
    const params: (string | number)[] = [];
    let paramIndex = 1;

    // Term search - fuzzy or exact
    if (term) {
      if (exact) {
        conditions.push(`term_normalized = $${paramIndex++}`);
        params.push(term.toLowerCase().trim());
      } else {
        // Full-text search on term and definition
        conditions.push(`(
          term_normalized ILIKE $${paramIndex++}
          OR to_tsvector('english', term || ' ' || definition_text) @@ plainto_tsquery('english', $${paramIndex++})
        )`);
        params.push(`%${term.toLowerCase().trim()}%`);
        params.push(term);
      }
    }

    // Source document filter
    if (source) {
      conditions.push(`source_document ILIKE $${paramIndex++}`);
      params.push(`%${source}%`);
    }

    // Domain tag filter (array contains)
    if (domain) {
      conditions.push(`$${paramIndex++} = ANY(domain_tags)`);
      params.push(domain.toLowerCase());
    }

    // Legislation type filter
    if (legislationType) {
      conditions.push(`legislation_type = $${paramIndex++}`);
      params.push(legislationType.toUpperCase());
    }

    // Build final query
    const whereClause = conditions.length > 0
      ? `WHERE ${conditions.join(' AND ')}`
      : '';

    const sql = `
      SELECT
        id,
        term,
        definition_text,
        definition_summary,
        source_document,
        source_clause,
        legislation_type,
        lga,
        former_council,
        domain_tags,
        pdf_page,
        pdf_source_file
      FROM regulatory_definitions
      ${whereClause}
      ORDER BY
        ${term ? `
          CASE
            WHEN term_normalized = $1 THEN 1
            WHEN term_normalized LIKE $1 || '%' THEN 2
            WHEN term_normalized LIKE '%' || $1 || '%' THEN 3
            ELSE 4
          END,
        ` : ''}
        term_normalized ASC
      LIMIT $${paramIndex}
    `;

    params.push(limit);

    console.log(`[Definitions API] Query: term=${term}, source=${source}, domain=${domain}, type=${legislationType}`);

    const result = await query(sql, params);
    const definitions = result.rows as DefinitionResult[];

    const responseTime = Date.now() - startTime;

    // Build filters applied object
    const filtersApplied: Record<string, string> = {};
    if (term) filtersApplied.term = term;
    if (source) filtersApplied.source = source;
    if (domain) filtersApplied.domain = domain;
    if (legislationType) filtersApplied.legislation_type = legislationType;

    console.log(`[Definitions API] Found ${definitions.length} definitions in ${responseTime}ms`);

    return NextResponse.json({
      success: true,
      count: definitions.length,
      definitions,
      meta: {
        term_searched: term || undefined,
        filters_applied: filtersApplied,
        response_time_ms: responseTime
      }
    });

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('[Definitions API] Error:', error);

    return NextResponse.json(
      {
        error: 'Failed to query definitions',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
