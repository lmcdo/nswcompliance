import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { createClient } from '@/lib/supabase/server';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

const WINDOW_DAYS = 90;
// Bounding box pre-filter: ±0.005° ≈ 500m at Sydney latitudes — matches the radius limit
const BBOX_DELTA = 0.005;
const RADIUS_M = 500;

const schema = z.object({
  address: z.string().min(5).max(300),
});

function haversine(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6_371_000;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dp = toRad(lat2 - lat1);
  const dl = toRad(lng2 - lng1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dl / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

interface Application {
  PlanningPortalApplicationNumber?: string;
  ApplicationNumber?: string;
  ApplicationType?: string;
  DevelopmentType?: string;
  ApplicationDescription?: string;
  LodgementDate?: string;
  DeterminationDate?: string;
  Status?: string;
  PropertyAddress?: string;
  LotDescription?: string;
  CostOfDevelopment?: number | string;
  NumberOfNewDwellings?: number | string;
  CouncilName?: string;
  Latitude?: string | number;
  Longitude?: string | number;
  _distance_m?: number | null;
}

function parseDevTypes(raw: string | null): string {
  if (!raw) return '';
  try {
    const arr = JSON.parse(raw) as Array<{ DevelopmentType?: string }>;
    return arr.map((d) => d.DevelopmentType ?? '').filter(Boolean).join(', ');
  } catch {
    return '';
  }
}

/**
 * Query development_applications and complying_development_certificates within a
 * bounding box (±BBOX_DELTA°) and last WINDOW_DAYS days, then post-filter to RADIUS_M.
 * Both tables have latitude/longitude float columns populated by the ETL.
 */
async function queryNearbyApplications(lat: number, lng: number): Promise<Application[]> {
  const since = new Date(Date.now() - WINDOW_DAYS * 86_400_000).toISOString().slice(0, 10);
  const supabase = await createClient();

  const minLat = lat - BBOX_DELTA;
  const maxLat = lat + BBOX_DELTA;
  const minLng = lng - BBOX_DELTA;
  const maxLng = lng + BBOX_DELTA;

  const [daResult, cdcResult] = await Promise.all([
    supabase
      .from('development_applications')
      .select(
        'planning_portal_id,council_name,address,description,application_status,determination_date,' +
        'cost_of_development,latitude,longitude,development_type,lodgement_date,proposed_dwellings',
      )
      .gte('lodgement_date', since)
      .gte('latitude', minLat).lte('latitude', maxLat)
      .gte('longitude', minLng).lte('longitude', maxLng),
    supabase
      .from('complying_development_certificates')
      .select(
        'planning_portal_id,council_name,address,description,application_status,determination_date,' +
        'cost_of_development,latitude,longitude,development_type,submission_date,number_of_new_dwellings',
      )
      .gte('submission_date', since)
      .gte('latitude', minLat).lte('latitude', maxLat)
      .gte('longitude', minLng).lte('longitude', maxLng),
  ]);

  const apps: Application[] = [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for (const row of (daResult.data ?? []) as any[]) {
    if (!row.latitude || !row.longitude) continue;
    const dist = haversine(lat, lng, row.latitude as number, row.longitude as number);
    if (dist > RADIUS_M) continue;
    apps.push({
      PlanningPortalApplicationNumber: row.planning_portal_id,
      ApplicationType: 'DA',
      DevelopmentType: parseDevTypes(row.development_type) || undefined,
      ApplicationDescription: row.description,
      LodgementDate: row.lodgement_date,
      DeterminationDate: row.determination_date,
      Status: row.application_status,
      PropertyAddress: row.address,
      CostOfDevelopment: row.cost_of_development,
      NumberOfNewDwellings: row.proposed_dwellings,
      CouncilName: row.council_name,
      Latitude: row.latitude as number,
      Longitude: row.longitude as number,
      _distance_m: Math.round(dist),
    });
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  for (const row of (cdcResult.data ?? []) as any[]) {
    if (!row.latitude || !row.longitude) continue;
    const dist = haversine(lat, lng, row.latitude as number, row.longitude as number);
    if (dist > RADIUS_M) continue;
    apps.push({
      PlanningPortalApplicationNumber: row.planning_portal_id,
      ApplicationType: 'CDC',
      DevelopmentType: parseDevTypes(row.development_type) || undefined,
      ApplicationDescription: row.description,
      LodgementDate: row.submission_date,  // CDCs use submission_date, map to LodgementDate for UI parity
      DeterminationDate: row.determination_date,
      Status: row.application_status,
      PropertyAddress: row.address,
      CostOfDevelopment: row.cost_of_development,
      NumberOfNewDwellings: row.number_of_new_dwellings,
      CouncilName: row.council_name,
      Latitude: row.latitude as number,
      Longitude: row.longitude as number,
      _distance_m: Math.round(dist),
    });
  }

  return apps.sort((a, b) => (a._distance_m ?? Infinity) - (b._distance_m ?? Infinity));
}

/**
 * POST /api/satellite/threat-radar/search
 * Body: { address: string }
 *
 * Returns DA/CDC applications within 500m of the address (last 90 days), sourced from
 * Supabase (populated daily by the NSW Planning ETL). Sorted closest first.
 */
export async function POST(request: NextRequest) {
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, satelliteRateLimiter, 20, 60000);
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

  const { address } = parsed.data;

  // Resolve address
  const siteUrl = new URL(request.url).origin;
  const propUrl = `${siteUrl}/api/property/${encodeURIComponent(address)}`;
  const propResp = await fetch(propUrl, { signal: AbortSignal.timeout(10_000) }).catch(() => null);
  if (!propResp?.ok) {
    return NextResponse.json({ error: `Could not resolve address: ${address}` }, { status: 422 });
  }
  const propData = await propResp.json();
  if (!propData.success || !propData.property) {
    return NextResponse.json({ error: propData.error ?? 'Could not resolve address' }, { status: 422 });
  }

  const prop_id = String(propData.property.prop_id);

  let lat: number | null = propData.property.coordinates?.lat ?? null;
  let lng: number | null = propData.property.coordinates?.lng ?? null;

  if ((!lat || !lng) && propData.lotGeometry?.rings?.[0]?.length) {
    const ring: [number, number][] = propData.lotGeometry.rings[0];
    const xMerc = ring.reduce((s: number, p: [number, number]) => s + p[0], 0) / ring.length;
    const yMerc = ring.reduce((s: number, p: [number, number]) => s + p[1], 0) / ring.length;
    lng = (xMerc / 20037508.34) * 180;
    lat = (Math.atan(Math.exp((yMerc / 20037508.34) * Math.PI)) * 360 / Math.PI) - 90;
  }

  if (!lat || !lng) {
    return NextResponse.json({ error: 'Could not determine coordinates for this address' }, { status: 422 });
  }

  // Resolve council name for display (non-fatal if unavailable)
  let council_name: string | null = propData.property.lga_name ?? null;
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
      // non-fatal
    }
  }

  const applications = await queryNearbyApplications(lat, lng);

  return NextResponse.json({
    address,
    prop_id,
    lat,
    lng,
    council_name,
    applications,
    window_days: WINDOW_DAYS,
    radius_m: RADIUS_M,
  });
}
