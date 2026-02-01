/**
 * Control Code Search API
 * Uses Phase 1 control_codes table
 * Searches individual codes from multi-code provisions (C17, C18, C19)
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

interface ControlCodeProvision {
  provisionId: number;
  code: string;
  codeGroup: string;
  controlType: string;
  sequenceNumber: number;
  isRangeStart: boolean;
  isRangeEnd: boolean;
  refNumber: string;
  provisionText: string;
  zone: string | null;
  documentId: string;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const controlType = searchParams.get('control_type');
    const zone = searchParams.get('zone');
    const limit = parseInt(searchParams.get('limit') || '50');

    if (!code && !controlType) {
      return NextResponse.json(
        { error: 'Either code or control_type parameter is required' },
        { status: 400 }
      );
    }

    let query = `
      SELECT
        cc.provision_id,
        cc.code,
        cc.code_group,
        cc.control_type,
        cc.sequence_number,
        cc.is_range_start,
        cc.is_range_end,
        rp.ref_number,
        rp.provision_text,
        rp.zone,
        rp.document_id
      FROM control_codes cc
      JOIN regulatory_provisions rp ON cc.provision_id = rp.id
      WHERE 1=1
    `;

    const params: any[] = [];

    if (code) {
      query += ` AND cc.code = $${params.length + 1}`;
      params.push(code);
    }

    if (controlType) {
      query += ` AND cc.control_type = $${params.length + 1}`;
      params.push(controlType);
    }

    if (zone) {
      query += ` AND rp.zone = $${params.length + 1}`;
      params.push(zone);
    }

    query += ` ORDER BY cc.control_type, cc.code, cc.sequence_number LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await pool.query(query, params);

    const provisions: ControlCodeProvision[] = result.rows.map(row => ({
      provisionId: row.provision_id,
      code: row.code,
      codeGroup: row.code_group,
      controlType: row.control_type,
      sequenceNumber: row.sequence_number,
      isRangeStart: row.is_range_start,
      isRangeEnd: row.is_range_end,
      refNumber: row.ref_number || 'N/A',
      provisionText: row.provision_text ? row.provision_text.substring(0, 200) : '',
      zone: row.zone,
      documentId: row.document_id
    }));

    // Group by control type
    const byControlType = provisions.reduce((acc, p) => {
      const type = p.controlType;
      if (!acc[type]) acc[type] = [];
      acc[type].push(p);
      return acc;
    }, {} as Record<string, ControlCodeProvision[]>);

    // Group by code_group for display
    const byCodeGroup = provisions.reduce((acc, p) => {
      const group = p.codeGroup;
      if (!acc[group]) acc[group] = [];
      acc[group].push(p);
      return acc;
    }, {} as Record<string, ControlCodeProvision[]>);

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        provisions,
        byControlType,
        byCodeGroup,
        totalCount: provisions.length,
        query: { code, controlType, zone }
      },
      meta: {
        responseTimeMs: responseTime,
        source: 'control_codes',
        multiCodeProvisionsExpanded: true
      }
    });

  } catch (error) {
    console.error('Control code search error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
