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
  epiName?: string;  // e.g. "State Environmental Planning Policy (Sustainable Buildings) 2022"
  keywords?: string[];  // e.g. ["BASIX", "climate", "water"]
  mapType?: string;  // e.g. "WAT", "CLM", "BAL"
  provisionId?: number;  // Direct provision ID lookup (alternative to epiName)
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
    const { epiName, keywords, mapType, provisionId } = body;

    if (!epiName && !provisionId) {
      return NextResponse.json({
        success: false,
        error: 'Either epiName or provisionId is required'
      }, { status: 400 });
    }

    console.log(`[SEPP Full Text API] Query: epiName=${epiName}, provisionId=${provisionId}, keywords=${keywords}, mapType=${mapType}`);

    let query: string;
    let params: any[];

    // Branch 1: Direct provision ID lookup
    if (provisionId) {
      console.log(`[SEPP Full Text API] Direct lookup by provision ID: ${provisionId}`);

      query = `
        SELECT
          id,
          document_id,
          ref_number,
          section_header,
          provision_text,
          provision_type,
          document_category,
          LENGTH(provision_text) as text_length
        FROM provisions_with_category
        WHERE id = $1
      `;
      params = [provisionId];
    }
    // Branch 2: EPI name-based search
    else {
      // Convert EPI Name to document_id pattern for LIKE query
      // Extract key terms from the EPI name for flexible matching
      // Examples:
      // "State Environmental Planning Policy (Sustainable Buildings) 2022" -> "%Sustainable%Buildings%2022%"
      // "State Environmental Planning Policy (Transport and Infrastructure) 2021" -> "%Transport%Infrastructure%2021%"
      // "State Environmental Planning Policy (Exempt and Complying Development Codes) 2008" -> "%Exempt%Complying%2008%"

      // Extract the part between parentheses and the year
      const parenthesesMatch = epiName!.match(/\(([^)]+)\)\s*(\d{4})/);
      let docIdPattern = '%';

      if (parenthesesMatch) {
        const nameInParentheses = parenthesesMatch[1];
        const year = parenthesesMatch[2];

        // Split by common words and take meaningful keywords
        const keywordsList = nameInParentheses
          .split(/\s+(?:and|the|of|for)\s+/i)
          .flatMap(part => part.split(/\s+/))
          .filter(word => word.length > 3); // Filter out short words like "and", "the"

        // Build pattern with key terms
        docIdPattern = keywordsList.slice(0, 2).map(k => `%${k}%`).join('') + `${year}%`;
      } else {
        // Fallback: use the full name with wildcards
        const cleanName = epiName!.replace(/[^a-zA-Z0-9\s]/g, '');
        const words = cleanName.split(/\s+/).filter(w => w.length > 3);
        docIdPattern = words.slice(0, 3).map(w => `%${w}%`).join('');
      }

      console.log(`[SEPP Full Text API] Generated pattern: ${docIdPattern}`);

      // Build WHERE clauses for keywords
      let keywordConditions = '';
      params = [docIdPattern];
      let paramIndex = 2;

      if (keywords && keywords.length > 0) {
        const keywordClauses = keywords.map(keyword => {
          params.push(`%${keyword}%`);
          return `provision_text ILIKE $${paramIndex++}`;
        });
        keywordConditions = ` AND (${keywordClauses.join(' OR ')})`;
      }

      // Query database for SEPP provisions using new VIEW
      query = `
        SELECT
          id,
          document_id,
          ref_number,
          section_header,
          provision_text,
          provision_type,
          document_category,
          LENGTH(provision_text) as text_length
        FROM provisions_with_category
        WHERE document_category = 'SEPP'
        AND document_id LIKE $1
        ${keywordConditions}
        ORDER BY ref_number
        LIMIT 20
      `;
    }

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