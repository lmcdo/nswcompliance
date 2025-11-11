import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection (PRP-A1 compliant)
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  statement_timeout: 30000  // 30 second timeout
});

interface SeppFullTextRequest {
  epiName?: string;  // e.g. "State Environmental Planning Policy (Sustainable Buildings) 2022"
  keywords?: string[];  // e.g. ["BASIX", "climate", "water"]
  mapType?: string;  // e.g. "WAT", "CLM", "BAL"
  provisionId?: number;  // Direct provision ID lookup (alternative to epiName)
  developmentType?: string;  // e.g. "dwelling_house", "commercial", "shop_top_housing"
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
    const { epiName, keywords, mapType, provisionId, developmentType } = body;

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

      // Build schedule filter based on development type
      // This ensures we show only relevant compliance methods for the development type
      let scheduleFilter = '';

      if (developmentType) {
        console.log(`[SEPP Full Text API] Filtering for development type: ${developmentType}`);

        // Residential development types → BASIX (Schedules 1 & 2)
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

        // Commercial development types → Large Commercial (Schedule 3)
        const commercialTypes = [
          'commercial',
          'shop_top_housing',
          'retail',
          'office',
          'business_premises',
          'industrial'
        ];

        if (residentialTypes.includes(developmentType)) {
          // Show residential BASIX schedules (Schedule 1: new buildings, Schedule 2: alterations)
          scheduleFilter = ` AND (
            ref_number LIKE 'Schedule 1%' OR
            ref_number LIKE 'Schedule 2%' OR
            ref_number LIKE '2.1%'
          )`;
          console.log('[SEPP Full Text API] Applying residential filter (Schedules 1 & 2)');
        } else if (commercialTypes.includes(developmentType)) {
          // Show commercial schedules (Schedule 3: large commercial development)
          scheduleFilter = ` AND (
            ref_number LIKE 'Schedule 3%' OR
            ref_number LIKE '3.3%'
          )`;
          console.log('[SEPP Full Text API] Applying commercial filter (Schedule 3)');
        }
        // If development type not recognized, show all schedules (no filter)
      }

      // Exclude generic clauses that don't provide actionable compliance info
      const excludeGenericClauses = `
        AND ref_number NOT LIKE '1.1%'
        AND ref_number NOT LIKE '1.2%'
        AND ref_number NOT LIKE '1.5%'
        AND ref_number NOT LIKE '1.6%'
        AND ref_number NOT LIKE '1.7%'
        AND section_header NOT ILIKE '%name of policy%'
        AND section_header NOT ILIKE '%commencement%'
        AND section_header NOT ILIKE '%maps%'
        AND section_header NOT ILIKE '%relationship with other%'
      `;

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
          LENGTH(provision_text) as text_length,
          CASE
            WHEN ref_number LIKE 'Schedule%' THEN 100
            WHEN ref_number LIKE 'Chapter 3%' THEN 80
            WHEN ref_number LIKE 'Chapter 2%' THEN 70
            WHEN provision_type ILIKE '%standard%' THEN 60
            WHEN provision_type ILIKE '%requirement%' THEN 50
            WHEN ref_number LIKE 'Chapter 1%' THEN 20
            ELSE 30
          END as relevance_score
        FROM provisions_with_category
        WHERE document_category = 'SEPP'
        AND document_id LIKE $1
        ${keywordConditions}
        ${scheduleFilter}
        ${excludeGenericClauses}
        ORDER BY
          relevance_score DESC,
          ref_number
        LIMIT 10
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