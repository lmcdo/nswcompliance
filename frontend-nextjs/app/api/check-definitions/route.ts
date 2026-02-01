/**
 * Check Definitions Table
 * GET /api/check-definitions
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET() {
  const pool = getPool();

  try {
    // Check if table exists
    const tableCheck = await pool.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
        AND table_name LIKE '%definition%'
    `);

    // If definitions table exists, check its structure and content
    if (tableCheck.rows.length > 0) {
      const tableName = tableCheck.rows[0].table_name;

      const columns = await pool.query(`
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position
      `, [tableName]);

      const sampleData = await pool.query(`SELECT * FROM ${tableName} LIMIT 10`);

      const count = await pool.query(`SELECT COUNT(*) FROM ${tableName}`);

      return NextResponse.json({
        success: true,
        table: tableName,
        columns: columns.rows,
        sampleData: sampleData.rows,
        totalCount: parseInt(count.rows[0].count),
        timestamp: new Date().toISOString()
      });
    }

    return NextResponse.json({
      success: true,
      table: null,
      message: 'No definitions table found',
      allTables: tableCheck.rows
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}
