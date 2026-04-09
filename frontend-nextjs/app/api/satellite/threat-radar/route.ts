import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3003';

const getSupabase = () =>
  createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

/**
 * POST /api/satellite/threat-radar
 * Body: { address: string, email: string, council_name: string }
 *
 * Resolves address → lat/lng/prop_id, then subscribes to weekly Threat Radar monitoring.
 */
export async function POST(request: NextRequest) {
  let body: { address?: string; email?: string; council_name?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const address = body.address?.trim();
  const email = body.email?.trim();

  if (!address) return NextResponse.json({ error: 'address is required' }, { status: 400 });
  if (!email) return NextResponse.json({ error: 'email is required' }, { status: 400 });

  // Resolve address
  const propUrl = `${SITE_URL}/api/property/${encodeURIComponent(address)}`;
  const propResp = await fetch(propUrl).catch(() => null);
  if (!propResp?.ok) {
    return NextResponse.json({ error: `Could not resolve address: ${address}` }, { status: 422 });
  }

  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json({ error: propData.error ?? 'Could not resolve address' }, { status: 422 });
  }

  const prop_id = String(propData.property.prop_id);

  // council_name: caller may override → else derive from lat/lng via NSW Spatial Services
  let council_name: string | null = body.council_name?.trim() || propData.property.lga_name || null;
  if (!council_name && lat && lng) {
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

  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && propData.lotGeometry?.rings?.[0]?.length) {
    const ring: [number, number][] = propData.lotGeometry.rings[0];
    lng = ring.reduce((s, p) => s + p[0], 0) / ring.length;
    lat = ring.reduce((s, p) => s + p[1], 0) / ring.length;
  }

  if (!lat || !lng) {
    return NextResponse.json({ error: 'Could not determine coordinates for this address' }, { status: 422 });
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

  return NextResponse.json({ subscription_id: String(data.id), address, message: "Subscription active. You'll receive weekly alerts for new development applications near this address." });
}
