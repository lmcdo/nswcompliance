/**
 * Zone Applicability Query API
 * Uses Phase 1 provision_applicability table
 * Handles NULL zones via explicit applicability rules
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

interface ProvisionApplicability {
  provisionId: number;
  refNumber: string;
  provisionText: string;
  explicitZone: string | null;
  appliesToZone: string | null;
  appliesToAllZones: boolean;
  appliesToLGA: string | null;
  appliesStateWide: boolean;
  applicabilitySource: string;
  confidenceScore: number;
  documentId: string;
  provisionCategory: string;
  displayPriority: number;
}

export async function GET(request: NextRequest) {
  const startTime = Date.now();

  try {
    const searchParams = request.nextUrl.searchParams;
    const zone = searchParams.get('zone');
    const lga = searchParams.get('lga');
    const documentType = searchParams.get('document_type');
    const limit = parseInt(searchParams.get('limit') || '50');

    if (!zone && !lga) {
      return NextResponse.json(
        { error: 'Either zone or lga parameter is required' },
        { status: 400 }
      );
    }

    let query = `
      SELECT
        rp.id as provision_id,
        rp.ref_number,
        rp.provision_text,
        rp.zone as explicit_zone,
        rp.document_id,
        rp.provision_category,
        rp.display_priority,
        pa.applies_to_zone,
        pa.applies_to_all_zones,
        pa.applies_to_lga,
        pa.applies_state_wide,
        pa.applicability_source,
        pa.confidence_score
      FROM regulatory_provisions_canonical rp
      JOIN provision_applicability pa ON rp.id = pa.provision_id
      WHERE 1=1
    `;

    const params: any[] = [];

    if (zone) {
      query += ` AND (
        pa.applies_to_zone = $${params.length + 1}
        OR pa.applies_to_all_zones = TRUE
        OR pa.applies_state_wide = TRUE
      )`;
      params.push(zone);
    }

    if (lga) {
      query += ` AND (
        pa.applies_to_lga = $${params.length + 1}
        OR pa.applies_state_wide = TRUE
      )`;
      params.push(lga);
    }

    if (documentType) {
      if (documentType === 'SEPP') {
        query += ` AND rp.document_id LIKE '%SEPP%'`;
      } else if (documentType === 'LEP') {
        query += ` AND rp.document_id LIKE '%LEP%'`;
      } else if (documentType === 'DCP') {
        query += ` AND rp.document_id LIKE '%DCP%'`;
      }
    }

    query += ` ORDER BY rp.display_priority, rp.ref_number LIMIT $${params.length + 1}`;
    params.push(limit);

    const result = await pool.query(query, params);

    const provisions: ProvisionApplicability[] = result.rows.map(row => ({
      provisionId: row.provision_id,
      refNumber: row.ref_number || 'N/A',
      provisionText: row.provision_text ? row.provision_text.substring(0, 2000) : '', // Increased from 300 to 2000 chars
      explicitZone: row.explicit_zone,
      appliesToZone: row.applies_to_zone,
      appliesToAllZones: row.applies_to_all_zones,
      appliesToLGA: row.applies_to_lga,
      appliesStateWide: row.applies_state_wide,
      applicabilitySource: row.applicability_source,
      confidenceScore: row.confidence_score,
      documentId: row.document_id,
      provisionCategory: row.provision_category || 'general',
      displayPriority: row.display_priority || 5
    }));

    // Group by priority for progressive disclosure
    const byPriority = provisions.reduce((acc, p) => {
      const priority = p.displayPriority;
      if (!acc[priority]) acc[priority] = [];
      acc[priority].push(p);
      return acc;
    }, {} as Record<number, ProvisionApplicability[]>);

    const responseTime = Date.now() - startTime;

    return NextResponse.json({
      success: true,
      data: {
        provisions,
        byPriority,
        totalCount: provisions.length,
        query: { zone, lga, documentType }
      },
      meta: {
        responseTimeMs: responseTime,
        source: 'provision_applicability',
        nullZonesHandled: true
      }
    });

  } catch (error) {
    console.error('Zone applicability query error:', error);
    return NextResponse.json(
      {
        error: 'Internal server error',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
