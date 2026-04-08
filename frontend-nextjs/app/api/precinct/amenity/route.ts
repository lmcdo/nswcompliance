import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

/**
 * GET /api/precinct/amenity?precinctId=<id>
 *
 * Returns pre-computed amenity walkability for a DCP precinct.
 * Populated by enrichment/precompute_amenity.py at LGA onboarding time.
 *
 * 200 — cached result found
 * 404 — no cache entry for this precinct (caller should fall back to live city2graph /amenity)
 * 400 — missing precinctId param
 */
export async function GET(request: NextRequest) {
  const precinctId = request.nextUrl.searchParams.get('precinctId');

  if (!precinctId) {
    return NextResponse.json({ error: 'precinctId is required' }, { status: 400 });
  }

  const supabase = getSupabase();
  const { data, error } = await supabase
    .from('precinct_amenity_cache')
    .select('amenity_jsonb, centroid_lat, centroid_lng, computed_at')
    .eq('precinct_id', precinctId)
    .single();

  if (error || !data) {
    return NextResponse.json({ error: 'not_cached' }, { status: 404 });
  }

  return NextResponse.json({
    precinct_id: precinctId,
    amenity: data.amenity_jsonb,
    centroid_lat: data.centroid_lat,
    centroid_lng: data.centroid_lng,
    computed_at: data.computed_at,
    source: 'cache',
  });
}
