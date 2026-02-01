/**
 * Detailed Database Check for Pre-Implementation
 * GET /api/db-detailed
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET() {
  const pool = getPool();

  try {
    // Total provisions
    const total = await pool.query('SELECT COUNT(*) as count FROM regulatory_provisions');

    // By document type
    const byDoc = await pool.query(`
      SELECT
        CASE
          WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
          WHEN document_id LIKE '%LEP%' THEN 'LEP'
          WHEN document_id LIKE '%DCP%' THEN 'DCP'
          ELSE 'Other'
        END as doc_type,
        COUNT(*) as count
      FROM regulatory_provisions
      GROUP BY 1
      ORDER BY count DESC
    `);

    // Cross-reference table structure
    const crossRefCount = await pool.query('SELECT COUNT(*) as count FROM cross_reference_index');

    const crossRefColumns = await pool.query(`
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_name = 'cross_reference_index'
      ORDER BY ordinal_position
    `);

    // Sample a few cross-references if any exist
    const crossRefSample = await pool.query('SELECT * FROM cross_reference_index LIMIT 5');

    return NextResponse.json({
      success: true,
      regulatory_provisions: {
        total: parseInt(total.rows[0].count),
        by_type: byDoc.rows
      },
      cross_reference_index: {
        count: parseInt(crossRefCount.rows[0].count),
        columns: crossRefColumns.rows,
        sample: crossRefSample.rows
      },
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}
