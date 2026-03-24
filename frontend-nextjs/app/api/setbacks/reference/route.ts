/**
 * GET /api/setbacks/reference?zone=R2&lga=inner_west
 *
 * Returns structured setback reference values from the setback_rules table
 * for display as inline reference chips on DCP setback provisions.
 *
 * These are reference values only — not a compliance determination.
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export interface SetbackReference {
  side?: { ground?: number; upper?: number; source: string; document: string };
  rear?: { value: number; source: string; document: string };
  front?: { value: number; source: string; document: string };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const zone = searchParams.get('zone');
  const lga = searchParams.get('lga');

  if (!zone || !lga) {
    return NextResponse.json({ error: 'zone and lga are required' }, { status: 400 });
  }

  const lgaNormalised = lga.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const zoneCode = zone.split(' ')[0].toUpperCase();

  try {
    const pool = await getPool();
    const result = await pool.query<{
      boundary_type: string;
      storey_level: string;
      building_element: string;
      setback_meters: string;
      document_type: string;
      document_name: string;
      ref_number: string;
    }>(
      `SELECT boundary_type, storey_level, building_element,
              setback_meters, document_type, document_name, ref_number
       FROM setback_rules
       WHERE ($1 = ANY(zone) OR zone IS NULL)
         AND (lga = $2 OR lga IS NULL)
         AND building_element IN ('main_dwelling', 'all')
       ORDER BY priority ASC, boundary_type, storey_level`,
      [zoneCode, lgaNormalised]
    );

    if (result.rows.length === 0) {
      return NextResponse.json({ data: null });
    }

    const ref: SetbackReference = {};

    for (const row of result.rows) {
      const value = parseFloat(row.setback_meters);
      const source = row.ref_number
        ? `${row.document_name} ${row.ref_number}`.trim()
        : row.document_name;

      if (row.boundary_type === 'side') {
        if (!ref.side) ref.side = { source, document: row.document_name };
        if (row.storey_level === 'ground' || row.storey_level === 'all') ref.side.ground = value;
        if (row.storey_level === 'first' || row.storey_level === 'upper') ref.side.upper = value;
      }
      if (row.boundary_type === 'rear' && row.building_element === 'main_dwelling') {
        ref.rear = { value, source, document: row.document_name };
      }
      if (row.boundary_type === 'front') {
        ref.front = { value, source, document: row.document_name };
      }
    }

    return NextResponse.json({ data: ref, zone: zoneCode, lga: lgaNormalised });
  } catch (err) {
    console.error('[setbacks/reference] DB error:', err);
    return NextResponse.json({ error: 'Failed to fetch setback reference data' }, { status: 500 });
  }
}
