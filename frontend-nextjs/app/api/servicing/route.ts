// prior-art-checked: no existing route queries sydney_water_gsp_servicing. The Python
// pipeline (services/gsp_servicing.py) feeds the Site Report + conveyancer PDF; the
// /assessment workbench uses the client TS constraint pipeline which can't reach this
// table, so this thin route exposes the same point-in-polygon lookup via @/lib/db
// (same pattern as /api/dcp-interest). No new table.

import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

interface ServicingRow {
  product: 'WW' | 'DW';
  polygon_name: string | null;
  growth_area: string | null;
  status_code: string;
  constrained: boolean;
  timeframe: string | null;
  dsp_price_per_et: number | null;
}

export async function POST(request: NextRequest) {
  try {
    const { lat, lng } = await request.json();
    if (typeof lat !== 'number' || typeof lng !== 'number') {
      return NextResponse.json({ error: 'lat and lng (numbers) are required' }, { status: 400 });
    }

    const result = await query(
      // ST_Covers (not ST_Contains): a point on a polygon boundary counts as inside,
      // so a lot on a GSP edge is not falsely reported as outside every precinct.
      `SELECT product, polygon_name, growth_area, status_code, constrained,
              timeframe, dsp_price_per_et
       FROM sydney_water_gsp_servicing
       WHERE ST_Covers(geom, ST_SetSRID(ST_MakePoint($1, $2), 4326))`,
      [lng, lat], // ST_MakePoint is (x=lng, y=lat)
    );

    const rows = result.rows as ServicingRow[];
    if (rows.length === 0) {
      // Point resolved but sits in NO growth precinct — the established-suburb gap.
      // This is a real answer (Section 73 territory), NOT a failure.
      return NextResponse.json({ status: 'empty' });
    }

    const byProduct = (p: string) => rows.find((r) => r.product === p) ?? null;
    return NextResponse.json({
      status: 'found',
      ww: byProduct('WW'),
      dw: byProduct('DW'),
    });
  } catch (err) {
    console.error('[servicing] POST error:', err);
    // Fail closed — the caller renders nothing rather than a false "clear".
    return NextResponse.json({ status: 'failed' }, { status: 200 });
  }
}
