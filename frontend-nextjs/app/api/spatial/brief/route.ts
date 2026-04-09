import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const SPATIAL_API_URL = process.env.SPATIAL_API_URL ?? '';
const STREET_CONTEXT_TIMEOUT_MS = 8000;
const LIVE_AMENITY_TIMEOUT_MS = 20000;

/**
 * POST /api/spatial/brief
 * Body: { lat: number; lng: number; precinct_id?: string }
 *
 * Amenity resolution order:
 *   1. precinct_id from caller → cache lookup
 *   2. No precinct_id → spatial lookup via get_precinct_for_point() → cache
 *   3. Cache miss → live city2graph /amenity (up to 20s)
 *
 * Street context always runs in parallel (graph-only, ~2s, no Overpass).
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

  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );

  // Street-context fires immediately and runs fully in parallel.
  const streetContextPromise = fetchStreetContext(lat, lng);

  // Resolve precinct_id from caller or spatial lookup.
  let resolvedPrecinctId: string | null = precinct_id ?? null;
  if (!resolvedPrecinctId) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data } = await (supabase as any).rpc('get_precinct_for_point', { p_lat: lat, p_lng: lng });
      resolvedPrecinctId = (data as string) ?? null;
    } catch {
      // spatial lookup failed — proceed without
    }
  }

  // Try cache.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let amenityRow: { amenity_jsonb: any; computed_at: string | null } | null = null;
  if (resolvedPrecinctId) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { data } = await (supabase as any)
      .from('precinct_amenity_cache')
      .select('amenity_jsonb, computed_at')
      .eq('precinct_id', resolvedPrecinctId)
      .single();
    if (data) amenityRow = data;
  }

  let amenitySource: 'cache' | 'live' | null = amenityRow ? 'cache' : null;

  // Cache miss → live city2graph /amenity.
  if (!amenityRow) {
    const live = await fetchLiveAmenity(lat, lng);
    if (live) {
      amenityRow = { amenity_jsonb: live, computed_at: null };
      amenitySource = 'live';
    }
  }

  const streetContext = await streetContextPromise;

  if (!amenityRow && !streetContext) {
    return NextResponse.json({ error: 'spatial_unavailable' }, { status: 503 });
  }

  return NextResponse.json({
    amenity: amenityRow?.amenity_jsonb ?? null,
    street_context: streetContext,
    amenity_source: amenitySource,
    amenity_computed_at: amenityRow?.computed_at ?? null,
  });
}

async function fetchLiveAmenity(lat: number, lng: number) {
  if (!SPATIAL_API_URL) return null;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), LIVE_AMENITY_TIMEOUT_MS);
  try {
    const resp = await fetch(`${SPATIAL_API_URL}/amenity`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lng, radius_m: 1000 }),
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
