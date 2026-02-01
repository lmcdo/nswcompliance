/**
 * Check Contextual Guidance Columns
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET() {
  const pool = getPool();

  try {
    const columns = await pool.query(`
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_name = 'contextual_guidance_real'
      ORDER BY ordinal_position
    `);

    return NextResponse.json({
      success: true,
      columns: columns.rows
    });
  } catch (error: any) {
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}
