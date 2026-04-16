import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3003';
const DA_URL = 'https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA';
const CDC_URL = 'https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineCDC';
const RADIUS_M = 200;
const WINDOW_DAYS = 90;

const schema = z.object({
  address: z.string().min(5).max(300),
});

// NSW Spatial Services returns uppercase LGA names (e.g. "INNER WEST").
// NSW ePlanning API needs the exact registered council name.
const COUNCIL_NAME_MAP: Record<string, string> = {
  'sydney':                          'Council of the City of Sydney',
  'city of sydney':                  'Council of the City of Sydney',
  'inner west':                      'Inner West Council',
  'parramatta':                      'City of Parramatta Council',
  'city of parramatta':              'City of Parramatta Council',
  'northern beaches':                'Northern Beaches Council',
  'randwick':                        'Randwick City Council',
  'waverley':                        'Waverley Council',
  'woollahra':                       'Woollahra Municipal Council',
  'mosman':                          'Mosman Municipal Council',
  'north sydney':                    'North Sydney Council',
  'willoughby':                      'Willoughby City Council',
  'lane cove':                       'Lane Cove Municipal Council',
  'hunters hill':                    'Hunters Hill Council',
  'ryde':                            'Ryde City Council',
  'ku-ring-gai':                     'Ku-ring-gai Council',
  'hornsby':                         'Hornsby Shire Council',
  'the hills':                       'The Hills Shire Council',
  'hills shire':                     'The Hills Shire Council',
  'blacktown':                       'Blacktown City Council',
  'penrith':                         'Penrith City Council',
  'blue mountains':                  'Blue Mountains City Council',
  'hawkesbury':                      'Hawkesbury City Council',
  'camden':                          'Camden Council',
  'campbelltown':                    'Campbelltown City Council',
  'wollondilly':                     'Wollondilly Shire Council',
  'liverpool':                       'Liverpool City Council',
  'fairfield':                       'Fairfield City Council',
  'canterbury-bankstown':            'Canterbury-Bankstown Council',
  'canterbury bankstown':            'Canterbury-Bankstown Council',
  'georges river':                   'Georges River Council',
  'sutherland':                      'Sutherland Shire Council',
  'sutherland shire':                'Sutherland Shire Council',
  'bayside':                         'Bayside Council',
  'strathfield':                     'Strathfield Municipal Council',
  'burwood':                         'Burwood Council',
  'cumberland':                      'Cumberland Council',
  'gosford':                         'Central Coast Council',
  'wyong':                           'Central Coast Council',
  'central coast':                   'Central Coast Council',
  'wollongong':                      'Wollongong City Council',
  'newcastle':                       'Newcastle City Council',
  'lake macquarie':                  'Lake Macquarie City Council',
  'maitland':                        'Maitland City Council',
};

function normaliseCouncil(raw: string): string {
  return COUNCIL_NAME_MAP[raw.trim().toLowerCase()] ?? raw.trim();
}

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
  Status?: string;
  Latitude?: string | number;
  Longitude?: string | number;
  Location?: { X?: string; Y?: string }[];
  _distance_m?: number;
}

async function fetchApplications(councilName: string): Promise<Application[]> {
  const since = new Date(Date.now() - WINDOW_DAYS * 86_400_000)
    .toISOString()
    .slice(0, 10);
  const normalised = normaliseCouncil(councilName);
  const filtersHeader = JSON.stringify({
    filters: { CouncilName: [normalised], LodgementDateFrom: since },
  });
  const headers: Record<string, string> = {
    filters: filtersHeader,
    PageSize: '200',
    PageNumber: '1',
    'Cache-Control': 'no-cache',
  };

  const apps: Application[] = [];
  for (const url of [DA_URL, CDC_URL]) {
    try {
      const resp = await fetch(url, { headers, signal: AbortSignal.timeout(15_000) });
      if (resp.ok) {
        const data = await resp.json();
        const list: Application[] = data?.Application ?? data?.ApplicationList ?? [];
        apps.push(...list);
      }
    } catch {
      // non-fatal — one endpoint failing shouldn't block the other
    }
  }
  return apps;
}

function filterNearby(apps: Application[], lat: number, lng: number): Application[] {
  return apps
    .flatMap((app) => {
      try {
        const loc = (app.Location ?? [{}])[0] ?? {};
        const alat = parseFloat(String(app.Latitude ?? loc.Y ?? '0'));
        const alng = parseFloat(String(app.Longitude ?? loc.X ?? '0'));
        if (!alat || !alng) return [];
        const d = haversine(lat, lng, alat, alng);
        if (d > RADIUS_M) return [];
        return [{ ...app, _distance_m: Math.round(d) }];
      } catch {
        return [];
      }
    })
    .sort((a, b) => (a._distance_m ?? 999) - (b._distance_m ?? 999));
}

/**
 * POST /api/satellite/threat-radar/search
 * Body: { address: string }
 *
 * Returns current DA/CDC applications within 200m of the address (last 90 days).
 * Also returns resolved lat/lng/prop_id/council_name so the subscribe step can reuse them.
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
  const propUrl = `${SITE_URL}/api/property/${encodeURIComponent(address)}`;
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

  // Resolve council name
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

  if (!council_name) {
    return NextResponse.json(
      { error: 'Could not determine council for this address. Try a different address format.' },
      { status: 422 },
    );
  }

  const apps = await fetchApplications(council_name);
  const nearby = filterNearby(apps, lat, lng);

  return NextResponse.json({
    address,
    prop_id,
    lat,
    lng,
    council_name,
    applications: nearby,
    window_days: WINDOW_DAYS,
    radius_m: RADIUS_M,
  });
}
