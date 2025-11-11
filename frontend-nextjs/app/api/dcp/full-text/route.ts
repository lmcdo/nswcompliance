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
        id,
        document_id,
        ref_number,
        section_header,
        provision_text
      FROM regulatory_provisions_canonical
      WHERE document_id = $1
    `;

    const params: any[] = [documentId];
    let paramIndex = 2;

    // Add control number filter if provided
    if (controlNumber) {
      query += ` AND (ref_number = $${paramIndex}
                      OR ref_number LIKE $${paramIndex + 1})`;
      params.push(controlNumber, `${controlNumber}%`);
      paramIndex += 2;
    }

    // Add category filter if provided (for semantic search)
    if (category) {
      query += ` AND (provision_text ILIKE $${paramIndex}
                      OR section_header ILIKE $${paramIndex})`;
      params.push(`%${category}%`);
      paramIndex++;
    }

    query += ` ORDER BY ref_number LIMIT 20`;

    console.log('[DCP Full Text] Query:', query);
    console.log('[DCP Full Text] Params:', params);

    const result = await pool.query(query, params);

    console.log('[DCP Full Text] Found', result.rows.length, 'provisions');

    // If no results with control number, try searching in full text
    if (result.rows.length === 0 && controlNumber) {
      console.log('[DCP Full Text] No provisions found, trying full text search...');

      const fullTextQuery = `
        SELECT
          id,
          document_id,
          ref_number,
          section_header,
          provision_text
        FROM regulatory_provisions_canonical
        WHERE document_id = $1
        AND provision_text ILIKE $2
        ORDER BY ref_number
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
          provisions: fullTextResult.rows
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
        provisions: result.rows
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