/**
 * Cross-Reference Resolution API
 * Uses Phase 1 cross_reference_index table for instant lookup
 * Returns resolved provisions with confidence scores
 */

import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';


export const dynamic = 'force-dynamic';
const pool = new Pool({
  host: process.env.DB_HOST || process.env.DATABASE_HOST || 'localhost',
  database: process.env.DB_NAME || process.env.DATABASE_NAME || 'nsw_planning',
  user: process.env.DB_USER || process.env.DATABASE_USER || 'postgres',
  password: process.env.DB_PASSWORD || process.env.DATABASE_PASSWORD || '',
  port: parseInt(process.env.DB_PORT || process.env.DATABASE_PORT || '5432'),
});

interface CrossReference {
  id: number;
  referenceType: string;
  referenceNumber: string;
  referenceText: string;
  targetProvisionId: number | null;
  targetReference: string | null;
  targetText: string | null;
  resolutionStatus: string;
  resolutionConfidence: number;
  isMandatory: boolean;
  contextSnippet: string;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;
    const provisionId = searchParams.get('provision_id');
    const referenceType = searchParams.get('type');
    const resolvedOnly = searchParams.get('resolved_only') === 'true';

    if (!provisionId) {
      return NextResponse.json(
        { error: 'provision_id is required' },
        { status: 400 }
      );
    }

    let query = `
      SELECT
        xr.id,
        xr.reference_type,
        xr.reference_number,
        xr.reference_text,
        xr.target_provision_id,
        xr.resolution_status,
        xr.resolution_confidence,
        xr.is_mandatory,
        xr.context_snippet,
        rp_target.ref_number as target_reference,
        rp_target.provision_text as target_text
      FROM cross_reference_index xr
      LEFT JOIN regulatory_provisions rp_target
        ON xr.target_provision_id = rp_target.id
      WHERE xr.source_provision_id = $1
    `;

    const params: any[] = [parseInt(provisionId)];

    if (referenceType) {
      query += ` AND xr.reference_type = $${params.length + 1}`;
      params.push(referenceType);
    }

    if (resolvedOnly) {
      query += ` AND xr.resolution_status = 'resolved'`;
    }

    query += ` ORDER BY xr.is_mandatory DESC, xr.resolution_confidence DESC`;

    const result = await pool.query(query, params);

    const crossReferences: CrossReference[] = result.rows.map(row => ({
      id: row.id,
      referenceType: row.reference_type,
      referenceNumber: row.reference_number,
      referenceText: row.reference_text,
      targetProvisionId: row.target_provision_id,
      targetReference: row.target_reference,
      targetText: row.target_text ? row.target_text.substring(0, 200) : null,
      resolutionStatus: row.resolution_status,
      resolutionConfidence: row.resolution_confidence,
      isMandatory: row.is_mandatory,
      contextSnippet: row.context_snippet
    }));

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        provisionId: parseInt(provisionId),
        crossReferences,
        totalCount: crossReferences.length,
        resolvedCount: crossReferences.filter(r => r.resolutionStatus === 'resolved').length
      },
      meta: {
        responseTimeMs: responseTime,
        source: 'cross_reference_index'
      }
    });

  } catch (error) {
    console.error('Cross-reference lookup error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
