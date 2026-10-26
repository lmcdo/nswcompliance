import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';
import { quoteColumns, withCouncilWords } from '@/lib/council-quote';

// Database connection (PRP-A1 compliant)
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  statement_timeout: 30000  // 30 second timeout
});

/**
 * Extract DCP provisions from database
 *
 * DCPs provide detailed development controls including:
 * - Setbacks (front/side/rear)
 * - Car parking rates
 * - Landscaping requirements
 * - Heritage controls
 * - Building design guidelines
 */
export async function POST(request: NextRequest) {
  try {
    const { documentId, controlNumber, chapter, category } = await request.json();

    if (!documentId) {
      return NextResponse.json(
        { success: false, error: 'Missing documentId' },
        { status: 400 }
      );
    }

    console.log('[DCP Full Text] Fetching:', { documentId, controlNumber, chapter, category });

    // Build query based on what's provided
    let query = `
      SELECT
        rp.id,
        rp.document_id,
        rp.ref_number,
        rp.section_header,
        rp.provision_text,
        live.source_council,
        ${quoteColumns('live')}
      FROM regulatory_provisions_canonical rp
      -- only the CURRENT live row carries the council quote (same join as app/api/clause/[id])
      LEFT JOIN regulatory_provisions live ON live.id = rp.id AND live.is_current = TRUE
      WHERE rp.document_id = $1
    `;

    const params: any[] = [documentId];
    let paramIndex = 2;

    // Add control number filter if provided
    if (controlNumber) {
      query += ` AND (rp.ref_number = $${paramIndex}
                      OR rp.ref_number LIKE $${paramIndex + 1})`;
      params.push(controlNumber, `${controlNumber}%`);
      paramIndex += 2;
    }

    // Add category filter if provided (for semantic search)
    if (category) {
      query += ` AND (rp.provision_text ILIKE $${paramIndex}
                      OR rp.section_header ILIKE $${paramIndex})`;
      params.push(`%${category}%`);
      paramIndex++;
    }

    query += ` ORDER BY rp.ref_number LIMIT 20`;

    console.log('[DCP Full Text] Query:', query);
    console.log('[DCP Full Text] Params:', params);

    const result = await pool.query(query, params);

    console.log('[DCP Full Text] Found', result.rows.length, 'provisions');

    // If no results with control number, try searching in full text
    if (result.rows.length === 0 && controlNumber) {
      console.log('[DCP Full Text] No provisions found, trying full text search...');

      const fullTextQuery = `
        SELECT
          rp.id,
          rp.document_id,
          rp.ref_number,
          rp.section_header,
          rp.provision_text,
          live.source_council,
          ${quoteColumns('live')}
        FROM regulatory_provisions_canonical rp
        LEFT JOIN regulatory_provisions live ON live.id = rp.id AND live.is_current = TRUE
        WHERE rp.document_id = $1
        AND rp.provision_text ILIKE $2
        ORDER BY rp.ref_number
        LIMIT 10
      `;

      const fullTextResult = await pool.query(fullTextQuery, [
        documentId,
        `%${controlNumber}%`
      ]);

      console.log('[DCP Full Text] Full text search found', fullTextResult.rows.length, 'provisions');

      return NextResponse.json({
        success: true,
        data: {
          provisions: fullTextResult.rows.map((row: any) => withCouncilWords(row))
        },
        metadata: {
          documentId,
          controlNumber,
          chapter,
          category,
          count: fullTextResult.rows.length,
          searchMethod: 'full_text'
        }
      });
    }

    return NextResponse.json({
      success: true,
      data: {
        provisions: result.rows.map((row: any) => withCouncilWords(row))
      },
      metadata: {
        documentId,
        controlNumber,
        chapter,
        category,
        count: result.rows.length,
        searchMethod: 'direct'
      }
    });

  } catch (error) {
    console.error('[DCP Full Text] Database error:', error);
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch DCP text'
      },
      { status: 500 }
    );
  }
}