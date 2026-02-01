/**
 * Database Schema Check - Version/Amendment Fields
 * GET /api/db-schema-check
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET() {
  const pool = getPool();

  try {
    // Check for version/amendment columns
    const columns = await pool.query(`
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_name = 'regulatory_provisions'
        AND (column_name LIKE '%version%'
             OR column_name LIKE '%amendment%'
             OR column_name LIKE '%updated%'
             OR column_name LIKE '%modified%'
             OR column_name LIKE '%date%')
      ORDER BY column_name
    `);

    // Get sample columns to see what exists
    const allCols = await pool.query(`
      SELECT column_name
      FROM information_schema.columns
      WHERE table_name = 'regulatory_provisions'
      ORDER BY column_name
    `);

    return NextResponse.json({
      success: true,
      versionColumns: columns.rows,
      allColumns: allCols.rows.map(r => r.column_name),
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}
