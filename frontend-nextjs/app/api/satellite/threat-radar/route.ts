import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import { z } from 'zod';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

const getSupabase = () =>
  createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

const schema = z.object({
  address: z.string().min(5).max(300),
  email: z.string().email(),
  council_name: z.string().max(100).optional(),
});

/**
 * POST /api/satellite/threat-radar
 * Body: { address: string, email: string, council_name?: string }
 *
 * Resolves address → lat/lng/prop_id, then subscribes to weekly Threat Radar monitoring.
 */
export async function POST(request: NextRequest) {
  // Per-product rate limit — writes to DB + emails
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, satelliteRateLimiter, 10, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  let rawBody: unknown;
  try {
    rawBody = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const parsed = schema.safeParse(rawBody);
  if (!parsed.success) {
    return NextResponse.json(
      { error: 'Invalid input', details: parsed.error.flatten().fieldErrors },
      { status: 422 },
    );
  }

  const { address, email, council_name: councilNameOverride } = parsed.data;

  // Resolve address
  const propUrl = `${new URL(request.url).origin}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;
  const propResp = await fetch(propUrl, { headers: internalHeaders, signal: AbortSignal.timeout(10_000) }).catch(() => null);
  if (!propResp?.ok) {
    return NextResponse.json({ error: `Could not resolve address: ${address}` }, { status: 422 });
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json({ error: propData.error ?? 'Could not resolve address' }, { status: 422 });
  }

  const prop_id = String(propData.property.prop_id);

  // Resolve lat/lng before using them in the council_name spatial fallback below
  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && propData.lotGeometry?.rings?.[0]?.length) {
    // NSW Planning Portal returns lot geometry in EPSG:3857 (Web Mercator) — convert to WGS84
    const ring: [number, number][] = propData.lotGeometry.rings[0];
    const xMerc = ring.reduce((s: number, p: [number, number]) => s + p[0], 0) / ring.length;
    const yMerc = ring.reduce((s: number, p: [number, number]) => s + p[1], 0) / ring.length;
    lng = (xMerc / 20037508.34) * 180;
    lat = (Math.atan(Math.exp((yMerc / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
  }

  if (!lat || !lng) {
    return NextResponse.json({ error: 'Could not determine coordinates for this address' }, { status: 422 });
  }

  // council_name: caller may override → else derive from lga_name or NSW Spatial Services
  let council_name: string | null = councilNameOverride || propData.property.lga_name || null;
  if (!council_name) {
    try {
      const spatialUrl =
        `https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Administrative_Boundaries/MapServer/1/query` +
        `?geometry=${lng},${lat}&geometryType=esriGeometryPoint&inSR=4326` +
        `&spatialRel=esriSpatialRelIntersects&outFields=lganame&f=json`;
      const spatialResp = await fetch(spatialUrl, { signal: AbortSignal.timeout(8_000) }).catch(() => null);
      if (spatialResp?.ok) {
        const spatialData = await spatialResp.json();
        council_name = spatialData?.features?.[0]?.attributes?.lganame ?? null;
      }
    } catch {
      // non-fatal — will fail at subscribe step if still null
    }
  }
  if (!council_name) {
    return NextResponse.json(
      { error: 'Could not determine council name for this address. Please provide council_name.' },
      { status: 422 },
    );
  }

  // Subscribe — write directly to Supabase (no Python backend required)
  const supabase = getSupabase();
  const { data, error } = await supabase
    .from('threat_radar_subscriptions')
    .insert({
      address,
      prop_id,
      lat,
      lng,
      email,
      active: true,
      inputs: { council_name, seen_application_numbers: [] },
    })
    .select('id')
    .single();

  if (error) {
    return NextResponse.json({ error: `Subscribe failed: ${error.message}` }, { status: 502 });
  }

  return NextResponse.json({
    subscription_id: String(data.id),
    address,
    message: "Subscription active. You'll receive weekly alerts for new development applications near this address.",
  });
}
