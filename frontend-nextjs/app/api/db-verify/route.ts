/**
 * Database Verification Endpoint
 * GET /api/db-verify
 *
 * Checks database connection and table row counts for pre-implementation checklist
 */

import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';

export async function GET() {
  const pool = getPool();

  const requiredTables = [
    'contextual_guidance_real',
    'cross_reference_index',
    'housing_sepp_standards',
    'dcp_general_requirements',
    'regulatory_provisions'
  ];

  const results: Record<string, { count: number | null; error?: string }> = {};

  try {
    for (const table of requiredTables) {
      try {
        const result = await pool.query(`SELECT COUNT(*) as count FROM ${table}`);
        results[table] = { count: parseInt(result.rows[0].count) };
      } catch (err: any) {
        results[table] = { count: null, error: err.message };
      }
    }

    return NextResponse.json({
      success: true,
      tables: results,
      timestamp: new Date().toISOString()
    });

  } catch (error: any) {
    return NextResponse.json({
      success: false,
      error: error.message
    }, { status: 500 });
  }
}
