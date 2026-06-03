/**
 * POST /api/constraint-arithmetic
 *
 * Proxy to Railway's /constraint-arithmetic/full endpoint.
 * Railway handles all DB queries (DCP controls, SEPP standards,
 * SEPP-LEP overrides) server-side — this route just forwards.
 */

import { NextRequest, NextResponse } from 'next/server';

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

  try {
    const railwayResp = await fetch(`${PYTHON_API}/constraint-arithmetic/full`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lot_area_m2: body.lot_area_m2,
        dev_type: body.dev_type ?? 'dwelling_house',
        zone: body.zone ?? null,
        lga: body.formerCouncil ?? body.lga ?? null,
        lep_height_str: body.maxHeight != null ? String(body.maxHeight) : null,
        lep_fsr_str: body.maxFsr != null ? String(body.maxFsr) : null,
        frontage_m: body.frontage ?? null,
        depth_m: body.depth ?? null,
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
