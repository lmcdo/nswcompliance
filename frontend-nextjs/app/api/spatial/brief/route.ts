import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

const SPATIAL_API_URL = process.env.SPATIAL_API_URL ?? '';
const STREET_CONTEXT_TIMEOUT_MS = 8000;

/**
 * POST /api/spatial/brief
 * Body: { lat: number; lng: number; precinct_id?: string }
 *
 * Returns amenity walkability + street context for a property location.
 * - Amenity: served from precinct_amenity_cache if precinct_id is provided; skipped if no cache hit.
 * - Street context: live from city2graph /street-context (graph-only, fast ~2s, no Overpass).
 *
 * 200 — at least one data source returned
 * 503 — both sources failed
 */
export async function POST(request: NextRequest) {
  let body: { lat?: number; lng?: number; precinct_id?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { lat, lng, precinct_id } = body;
  if (typeof lat !== 'number' || typeof lng !== 'number') {
    return NextResponse.json({ error: 'lat and lng are required numbers' }, { status: 400 });
  }

  // Run amenity cache lookup and street-context call in parallel.
  const [amenityResult, streetResult] = await Promise.allSettled([
    fetchAmenityFromCache(precinct_id),
    fetchStreetContext(lat, lng),
  ]);

  const amenity = amenityResult.status === 'fulfilled' ? amenityResult.value : null;
  const streetContext = streetResult.status === 'fulfilled' ? streetResult.value : null;

  if (!amenity && !streetContext) {
    return NextResponse.json({ error: 'spatial_unavailable' }, { status: 503 });
  }

  return NextResponse.json({
    amenity: amenity?.amenity_jsonb ?? null,
    street_context: streetContext,
    amenity_source: amenity ? 'cache' : null,
    amenity_computed_at: amenity?.computed_at ?? null,
  });
}

async function fetchAmenityFromCache(precinctId: string | undefined) {
  if (!precinctId) return null;
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from('precinct_amenity_cache')
    .select('amenity_jsonb, computed_at')
    .eq('precinct_id', precinctId)
    .single();
  if (error || !data) return null;
  return data;
}

async function fetchStreetContext(lat: number, lng: number) {
  if (!SPATIAL_API_URL) return null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), STREET_CONTEXT_TIMEOUT_MS);
  try {
    const resp = await fetch(`${SPATIAL_API_URL}/street-context`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng }),
      signal: controller.signal,
    });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
