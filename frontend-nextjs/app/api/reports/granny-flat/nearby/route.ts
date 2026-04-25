/**
 * GET /api/reports/granny-flat/nearby?lat=X&lng=Y&radius=1000
 *
 * Returns up to 5 recently completed, granny_flat_buildable=true reports
 * within `radius` metres of the given coordinates.
 *
 * Uses a bounding-box pre-filter (cheap) — no PostGIS required.
 * 1 degree latitude ≈ 111km, 1 degree longitude ≈ 111km × cos(lat).
 *
 * Only returns: address, run_date, max_floor_area_m2, estimated_weekly_rent_aud
 * No PII, no report_id (not purchased — just showing eligibility signal).
 */

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

const DEFAULT_RADIUS_M = 1000;
const MAX_RADIUS_M = 5000;
const MAX_RESULTS = 5;

export async function GET(req: NextRequest) {
  const params = req.nextUrl.searchParams;
  const latStr = params.get('lat');
  const lngStr = params.get('lng');
  const radiusStr = params.get('radius');

  const lat = latStr ? parseFloat(latStr) : NaN;
  const lng = lngStr ? parseFloat(lngStr) : NaN;

  if (isNaN(lat) || isNaN(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return NextResponse.json({ error: 'lat and lng are required and must be valid coordinates' }, { status: 400 });
  }

  const radiusM = Math.min(
    radiusStr ? Math.abs(parseFloat(radiusStr)) : DEFAULT_RADIUS_M,
    MAX_RADIUS_M
  );

  if (isNaN(radiusM)) {
    return NextResponse.json({ error: 'radius must be a number' }, { status: 400 });
  }

  // Bounding box: 1 degree lat ≈ 111,000m; 1 degree lng ≈ 111,000m × cos(lat)
  const deltaLat = radiusM / 111000;
  const deltaLng = radiusM / (111000 * Math.cos((lat * Math.PI) / 180));

  const supabase = await createClient();

  const { data, error } = await supabase
    .from('granny_flat_reports')
    .select('address, run_date, outputs')
    .eq('confidence', 'high')
    .gte('lat', lat - deltaLat)
    .lte('lat', lat + deltaLat)
    .gte('lng', lng - deltaLng)
    .lte('lng', lng + deltaLng)
    .order('run_date', { ascending: false })
    .limit(20); // fetch more, filter in JS for buildable=true, then cap at MAX_RESULTS

  if (error) {
    console.error('[granny-flat/nearby] Supabase error:', error);
    return NextResponse.json({ error: 'Failed to query nearby reports' }, { status: 500 });
  }

  const eligible = (data ?? [])
    .filter((row) => (row.outputs as Record<string, unknown>)?.granny_flat_buildable === true)
    .slice(0, MAX_RESULTS)
    .map((row) => {
      const o = (row.outputs ?? {}) as Record<string, unknown>;
      return {
        address: row.address,
        run_date: row.run_date,
        max_floor_area_m2: o.max_floor_area_m2 ?? null,
        estimated_weekly_rent_aud: o.estimated_weekly_rent_aud ?? null,
      };
    });

  return NextResponse.json({ results: eligible });
}
