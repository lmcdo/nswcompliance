import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

const WINDOW_DAYS = 90;
const RADIUS_M = 500;

const DA_URL = 'https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA';
const CDC_URL = 'https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineCDC';

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

// Maps NSW Planning Portal / NSW Spatial Services LGA names (lowercased) →
// exact council name string the NSW ePlanning API expects.
const COUNCIL_NAME_MAP: Record<string, string> = {
  // Sydney
  'sydney':                           'Council of the City of Sydney',
  'city of sydney':                   'Council of the City of Sydney',
  'sydney city':                      'Council of the City of Sydney',
  'sydney city council':              'Council of the City of Sydney',
  'council of the city of sydney':    'Council of the City of Sydney',
  // Inner West
  'inner west':                       'Inner West Council',
  // Parramatta
  'parramatta':                       'City of Parramatta Council',
  'city of parramatta':               'City of Parramatta Council',
  // Northern Beaches
  'northern beaches':                 'Northern Beaches Council',
  // Amalgamated
  'gosford':                          'Central Coast Council',
  'wyong':                            'Central Coast Council',
  'central coast':                    'Central Coast Council',
  // Other Sydney councils
  'randwick':                         'Randwick City Council',
  'waverley':                         'Waverley Council',
  'woollahra':                        'Woollahra Municipal Council',
  'mosman':                           'Mosman Municipal Council',
  'north sydney':                     'North Sydney Council',
  'willoughby':                       'Willoughby City Council',
  'lane cove':                        'Lane Cove Municipal Council',
  'hunters hill':                     'Hunters Hill Council',
  'ryde':                             'Ryde City Council',
  'ku-ring-gai':                      'Ku-ring-gai Council',
  'hornsby':                          'Hornsby Shire Council',
  'the hills':                        'The Hills Shire Council',
  'hills shire':                      'The Hills Shire Council',
  'blacktown':                        'Blacktown City Council',
  'penrith':                          'Penrith City Council',
  'blue mountains':                   'Blue Mountains City Council',
  'hawkesbury':                       'Hawkesbury City Council',
  'camden':                           'Camden Council',
  'campbelltown':                     'Campbelltown City Council',
  'wollondilly':                      'Wollondilly Shire Council',
  'liverpool':                        'Liverpool City Council',
  'fairfield':                        'Fairfield City Council',
  'canterbury-bankstown':             'Canterbury-Bankstown Council',
  'canterbury bankstown':             'Canterbury-Bankstown Council',
  'georges river':                    'Georges River Council',
  'sutherland':                       'Sutherland Shire Council',
  'sutherland shire':                 'Sutherland Shire Council',
  'bayside':                          'Bayside Council',
  'strathfield':                      'Strathfield Municipal Council',
  'burwood':                          'Burwood Council',
  'cumberland':                       'Cumberland Council',
  // Regional
  'wollongong':                       'Wollongong City Council',
  'shellharbour':                     'Shellharbour City Council',
  'kiama':                            'Kiama Municipal Council',
  'shoalhaven':                       'Shoalhaven City Council',
  'newcastle':                        'Newcastle City Council',
  'lake macquarie':                   'Lake Macquarie City Council',
  'cessnock':                         'Cessnock City Council',
  'maitland':                         'Maitland City Council',
  'port stephens':                    'Port Stephens Council',
  'bathurst':                         'Bathurst Regional Council',
  'orange':                           'Orange City Council',
  'dubbo':                            'Dubbo Regional Council',
  'tamworth':                         'Tamworth Regional Council',
  'wagga wagga':                      'Wagga Wagga City Council',
  'wagga':                            'Wagga Wagga City Council',
  'albury':                           'Albury City Council',
};

function normaliseCouncil(name: string): string {
  const key = name.trim().toLowerCase();
  return COUNCIL_NAME_MAP[key] ?? name.trim();
}

interface EplanningRaw {
  PlanningPortalApplicationNumber?: string;
  ApplicationNumber?: string;
  ApplicationDescription?: string;
  DevelopmentType?: string | Array<{ DevelopmentType?: string }>;
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
  Location?: Array<{ X?: string | number; Y?: string | number }>;
}

export interface Application {
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

function parseDevType(raw: EplanningRaw['DevelopmentType']): string | undefined {
  if (!raw) return undefined;
  if (Array.isArray(raw)) {
    return raw.map((d) => d.DevelopmentType ?? '').filter(Boolean).join(', ') || undefined;
  }
  try {
    const arr = JSON.parse(raw) as Array<{ DevelopmentType?: string }>;
    return arr.map((d) => d.DevelopmentType ?? '').filter(Boolean).join(', ') || undefined;
  } catch {
    return raw || undefined;
  }
}

/**
 * Call NSW ePlanning API directly for DA and CDC applications lodged in the
 * last WINDOW_DAYS, then post-filter to RADIUS_M via haversine distance.
 */
async function queryNearbyApplications(
  lat: number,
  lng: number,
  councilName: string,
): Promise<Application[]> {
  const since = new Date(Date.now() - WINDOW_DAYS * 86_400_000).toISOString().slice(0, 10);
  const council = normaliseCouncil(councilName);

  const filtersHeader = JSON.stringify({
    filters: { CouncilName: [council], LodgementDateFrom: since },
  });
  const reqHeaders = {
    filters: filtersHeader,
    PageSize: '200',
    PageNumber: '1',
    'Cache-Control': 'no-cache',
  };

  const [daResult, cdcResult] = await Promise.allSettled([
    fetch(DA_URL, { headers: reqHeaders, signal: AbortSignal.timeout(20_000) }),
    fetch(CDC_URL, { headers: reqHeaders, signal: AbortSignal.timeout(20_000) }),
  ]);

  const apps: Application[] = [];

  for (const [result, appType] of [
    [daResult, 'DA'],
    [cdcResult, 'CDC'],
  ] as [PromiseSettledResult<Response>, string][]) {
    if (result.status !== 'fulfilled' || !result.value.ok) continue;
    let data: { Application?: EplanningRaw[]; ApplicationList?: EplanningRaw[] };
    try {
      data = await result.value.json();
    } catch {
      continue;
    }
    const list: EplanningRaw[] = data.Application ?? data.ApplicationList ?? [];

    for (const app of list) {
      try {
        const loc = (app.Location ?? [{}])[0] ?? {};
        const alat = parseFloat(String(app.Latitude ?? loc.Y ?? 0));
        const alng = parseFloat(String(app.Longitude ?? loc.X ?? 0));
        if (!alat || !alng) continue;
        const dist = haversine(lat, lng, alat, alng);
        if (dist > RADIUS_M) continue;

        apps.push({
          PlanningPortalApplicationNumber: app.PlanningPortalApplicationNumber ?? app.ApplicationNumber,
          ApplicationType: appType,
          DevelopmentType: parseDevType(app.DevelopmentType),
          ApplicationDescription: app.ApplicationDescription,
          LodgementDate: app.LodgementDate,
          DeterminationDate: app.DeterminationDate,
          Status: app.Status,
          PropertyAddress: app.PropertyAddress,
          LotDescription: app.LotDescription,
          CostOfDevelopment: app.CostOfDevelopment,
          NumberOfNewDwellings: app.NumberOfNewDwellings,
          CouncilName: app.CouncilName ?? councilName,
          Latitude: alat,
          Longitude: alng,
          _distance_m: Math.round(dist),
        });
      } catch {
        // skip malformed record
      }
    }
  }

  return apps.sort((a, b) => (a._distance_m ?? Infinity) - (b._distance_m ?? Infinity));
}

/**
 * POST /api/satellite/threat-radar/search
 * Body: { address: string }
 *
 * Returns DA/CDC applications within 500m of the address (last 90 days),
 * sourced directly from the NSW ePlanning API. Sorted closest first.
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

  // Resolve address → lat/lng + council_name
  const siteUrl = new URL(request.url).origin;
  const propUrl = `${siteUrl}/api/property/${encodeURIComponent(address)}`;
  const internalHeaders: Record<string, string> = {};
  if (process.env.API_KEY) internalHeaders['x-api-key'] = process.env.API_KEY;

  const propResp = await fetch(propUrl, {
    headers: internalHeaders,
    signal: AbortSignal.timeout(10_000),
  }).catch(() => null);

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
    lat = (Math.atan(Math.exp((yMerc / 20037508.34) * Math.PI)) * 360) / Math.PI - 90;
  }

  if (!lat || !lng) {
    return NextResponse.json(
      { error: 'Could not determine coordinates for this address' },
      { status: 422 },
    );
  }

  // Resolve council name — required to query ePlanning API
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
      // non-fatal, will error below
    }
  }

  if (!council_name) {
    return NextResponse.json(
      { error: 'Could not determine council name for this address.' },
      { status: 422 },
    );
  }

  const applications = await queryNearbyApplications(lat, lng, council_name);

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
