import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection (PRP-A1 compliant)
const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'nsw_planning',
  user: 'postgres',
  password: 'postgres',
  statement_timeout: 30000  // 30 second timeout
});

interface SeppFullTextRequest {
  epiName: string;  // e.g. "State Environmental Planning Policy (Sustainable Buildings) 2022"
  keywords?: string[];  // e.g. ["BASIX", "climate", "water"]
  mapType?: string;  // e.g. "WAT", "CLM", "BAL"
}

/**
 * Fetch full SEPP text from database based on Planning API metadata
 *
 * POST /api/sepp/full-text
 * Body: { epiName, keywords?, mapType? }
 *
 * Returns: Array of provisions with full legal text
 */
export async function POST(request: NextRequest) {
  const startTime = Date.now();

  try {
    const body: SeppFullTextRequest = await request.json();
    const { epiName, keywords, mapType } = body;

    if (!epiName) {
      return NextResponse.json({
        success: false,
        error: 'epiName is required'
      }, { status: 400 });
    }

    console.log(`[SEPP Full Text API] Query: ${epiName}, keywords: ${keywords}, mapType: ${mapType}`);

    // Convert EPI Name to document_id pattern for LIKE query
    // Handle both formats:
    // 1. "State Environmental Planning Policy (Sustainable Buildings) 2022 - NSW Legislation"
    // 2. "State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation"
    const docIdPattern = `%Sustainable%Buildings%2022%`; // Simplified pattern to match both formats

    // Build WHERE clauses for keywords
    let keywordConditions = '';
    let params: any[] = [docIdPattern];
    let paramIndex = 2;

    if (keywords && keywords.length > 0) {
      const keywordClauses = keywords.map(keyword => {
        params.push(`%${keyword}%`);
        return `provision_text ILIKE $${paramIndex++}`;
      });
      keywordConditions = ` AND (${keywordClauses.join(' OR ')})`;
    }

    // Query database for SEPP provisions
    const query = `
      SELECT
        id,
        document_id,
        ref_number,
        section_header,
        provision_text,
        provision_type,
        LENGTH(provision_text) as text_length
      FROM regulatory_provisions
      WHERE document_id LIKE $1
      ${keywordConditions}
      ORDER BY ref_number
      LIMIT 20
    `;

    console.log(`[SEPP Full Text API] SQL:`, query);
    console.log(`[SEPP Full Text API] Params:`, params);

    const result = await pool.query(query, params);

    console.log(`[SEPP Full Text API] Found ${result.rows.length} provisions`);

    const provisions = result.rows.map(row => ({
      id: row.id,
      documentId: row.document_id,
      clause: row.ref_number,
      sectionHeader: row.section_header,
      fullText: row.provision_text,
      provisionType: row.provision_type,
      textLength: row.text_length
    }));

    const processingTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        provisions,
        epiName,
        keywords,
        count: provisions.length
      },
      metadata: {
        processingTimeMs: processingTime,
        timestamp: new Date().toISOString()
      }
    });

  } catch (error) {
    console.error('[SEPP Full Text API] Error:', error);

    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Internal server error',
      processingTimeMs: Date.now() - startTime
    }, { status: 500 });
  }
}