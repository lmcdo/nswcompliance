/**
 * POST /api/constraint-arithmetic
 *
 * Gathers DCP controls + SEPP standards from the DB, combines with
 * client-supplied property data, and calls the Python constraint
 * arithmetic engine on Railway.
 *
 * Body: { lot_area_m2, dev_type, zone, formerCouncil, lga,
 *         maxHeight, maxFsr, frontage, depth }
 */

import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';

export const dynamic = 'force-dynamic';
export const maxDuration = 15;

const PYTHON_API = process.env.PYTHON_API_URL;

interface RequestBody {
  lot_area_m2: number;
  dev_type?: string;
  zone?: string;
  formerCouncil?: string;
  lga?: string;
  maxHeight?: number | null;
  maxFsr?: number | null;
  frontage?: number | null;
  depth?: number | null;
}

export async function POST(request: NextRequest) {
  let body: RequestBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!body.lot_area_m2 || body.lot_area_m2 <= 0) {
    return NextResponse.json({ error: 'lot_area_m2 is required and must be > 0' }, { status: 400 });
  }

  if (!PYTHON_API) {
    return NextResponse.json({ error: 'PYTHON_API_URL not configured' }, { status: 503 });
  }

  const {
    lot_area_m2,
    dev_type = 'dwelling_house',
    zone,
    formerCouncil,
    lga,
    maxHeight,
    maxFsr,
    frontage,
    depth,
  } = body;

  try {
    const pool = getPool();

    // Gather DCP controls + SEPP standards in parallel
    const [dcpResult, seppResult] = await Promise.all([
      fetchDcpControls(pool, formerCouncil, zone),
      fetchSeppStandards(pool, zone),
    ]);

    // Compute SEPP-LEP overrides (where SEPP > LEP)
    const seppLepOverrides = computeSeppLepOverrides(seppResult, maxHeight, maxFsr);

    // Call Railway Python endpoint
    const railwayResp = await fetch(`${PYTHON_API}/constraint-arithmetic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lot_area_m2,
        dev_type,
        lep_height_str: maxHeight != null ? String(maxHeight) : null,
        lep_fsr_str: maxFsr != null ? String(maxFsr) : null,
        frontage_m: frontage ?? null,
        depth_m: depth ?? null,
        dcp_controls: dcpResult,
        sepp_standards: seppResult,
        sepp_lep_overrides: seppLepOverrides,
      }),
    });

    if (!railwayResp.ok) {
      const text = await railwayResp.text();
      console.error('[constraint-arithmetic] Railway error:', railwayResp.status, text);
      return NextResponse.json(
        { error: 'Constraint computation failed', detail: text },
        { status: 502 },
      );
    }

    const result = await railwayResp.json();
    return NextResponse.json({ success: true, data: result });
  } catch (err) {
    console.error('[constraint-arithmetic] Error:', err);
    return NextResponse.json(
      { error: 'Internal error', detail: err instanceof Error ? err.message : 'Unknown' },
      { status: 500 },
    );
  }
}


// ---------------------------------------------------------------------------
// DB queries — DCP controls from dcp_setback_controls
// ---------------------------------------------------------------------------

interface DCPControl {
  control_type: string;
  dev_type: string;
  value_min: number | null;
  value_max: number | null;
  unit: string | null;
  condition: string | null;
  source_ref: string | null;
}

async function fetchDcpControls(
  pool: ReturnType<typeof getPool>,
  formerCouncil?: string,
  zone?: string,
): Promise<DCPControl[]> {
  if (!formerCouncil) return [];

  try {
    const result = await pool.query(
      `SELECT dev_type, control_type, value_min, value_max, unit,
              condition, section_ref
       FROM dcp_setback_controls
       WHERE lga = $1 AND is_current = TRUE
       ORDER BY dev_type, control_type`,
      [formerCouncil.toLowerCase()],
    );

    return result.rows.map((r: any) => ({
      control_type: r.control_type,
      dev_type: r.dev_type ?? 'dwelling_house',
      value_min: r.value_min,
      value_max: r.value_max,
      unit: r.unit ?? 'm',
      condition: r.condition,
      source_ref: r.section_ref,
    }));
  } catch (err) {
    console.error('[constraint-arithmetic] DCP query error:', err);
    return [];
  }
}


// ---------------------------------------------------------------------------
// DB queries — SEPP Housing standards
// ---------------------------------------------------------------------------

interface SEPPStandard {
  dev_type: string;
  eligible: boolean;
  min_lot_area_m2: number | null;
  max_gfa_m2: number | null;
  max_fsr: number | null;
  max_height_m: number | null;
  setback_front_m: number | null;
  setback_rear_m: number | null;
  setback_side_m: number | null;
  reason_ineligible: string | null;
  min_lot_width_m: number | null;
  parking_spaces: number | null;
}

async function fetchSeppStandards(
  pool: ReturnType<typeof getPool>,
  zone?: string,
): Promise<SEPPStandard[]> {
  try {
    const zonePrefix = zone?.split(' ')[0]?.toUpperCase();
    let query: string;
    let params: any[];

    if (zonePrefix) {
      query = `
        SELECT development_type, standard_type, numeric_value, unit,
               applicable_zones, source_clause
        FROM housing_sepp_standards
        WHERE $1 = ANY(applicable_zones)
        ORDER BY development_type, standard_type
      `;
      params = [zonePrefix];
    } else {
      query = `
        SELECT development_type, standard_type, numeric_value, unit,
               applicable_zones, source_clause
        FROM housing_sepp_standards
        ORDER BY development_type, standard_type
      `;
      params = [];
    }

    const result = await pool.query(query, params);

    // Group rows by development_type and build SEPPStandard objects
    const byDevType = new Map<string, any[]>();
    for (const row of result.rows) {
      const dt = row.development_type;
      if (!byDevType.has(dt)) byDevType.set(dt, []);
      byDevType.get(dt)!.push(row);
    }

    const standards: SEPPStandard[] = [];
    for (const [devType, rows] of byDevType) {
      const std: SEPPStandard = {
        dev_type: devType,
        eligible: true,
        min_lot_area_m2: null,
        max_gfa_m2: null,
        max_fsr: null,
        max_height_m: null,
        setback_front_m: null,
        setback_rear_m: null,
        setback_side_m: null,
        reason_ineligible: null,
        min_lot_width_m: null,
        parking_spaces: null,
      };

      for (const row of rows) {
        const val = row.numeric_value;
        switch (row.standard_type) {
          case 'min_lot_area': std.min_lot_area_m2 = val; break;
          case 'max_gfa': std.max_gfa_m2 = val; break;
          case 'max_fsr': std.max_fsr = val; break;
          case 'max_height': std.max_height_m = val; break;
          case 'setback_front': std.setback_front_m = val; break;
          case 'setback_rear': std.setback_rear_m = val; break;
          case 'setback_side': std.setback_side_m = val; break;
          case 'min_lot_width': std.min_lot_width_m = val; break;
          case 'parking_spaces': std.parking_spaces = val; break;
        }
      }

      standards.push(std);
    }

    return standards;
  } catch (err) {
    console.error('[constraint-arithmetic] SEPP query error:', err);
    return [];
  }
}


// ---------------------------------------------------------------------------
// SEPP-LEP override computation
// ---------------------------------------------------------------------------

interface SeppLepOverride {
  dev_type: string;
  control: string;
  lep_value: number;
  sepp_value: number;
  source_clause: string | null;
  note: string;
}

function computeSeppLepOverrides(
  seppStandards: SEPPStandard[],
  lepHeight: number | null | undefined,
  lepFsr: number | null | undefined,
): SeppLepOverride[] {
  const overrides: SeppLepOverride[] = [];

  for (const std of seppStandards) {
    if (!std.eligible) continue;

    // Height override: SEPP max_height > LEP max_height
    if (std.max_height_m != null && lepHeight != null && std.max_height_m > lepHeight) {
      overrides.push({
        dev_type: std.dev_type,
        control: 'height',
        lep_value: lepHeight,
        sepp_value: std.max_height_m,
        source_clause: null,
        note: 'SEPP standard exceeds LEP control — SEPP prevails where more generous',
      });
    }

    // FSR override: SEPP max_fsr > LEP max_fsr
    if (std.max_fsr != null && lepFsr != null && std.max_fsr > lepFsr) {
      overrides.push({
        dev_type: std.dev_type,
        control: 'fsr',
        lep_value: lepFsr,
        sepp_value: std.max_fsr,
        source_clause: null,
        note: 'SEPP standard exceeds LEP control — SEPP prevails where more generous',
      });
    }
  }

  return overrides;
}
