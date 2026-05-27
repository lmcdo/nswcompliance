import { NextRequest, NextResponse } from 'next/server';
import { z } from 'zod';
import { createClient } from '@supabase/supabase-js';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { signReport } from '@/lib/report-token';
import { esriRingsToGeoJSON } from '@/lib/geo-utils';

const WINDOW_DAYS = 180;
// Bounding box pre-filter: ±0.006° ≈ 560m lat / 500m lng at Sydney latitudes
// Slightly larger than RADIUS_M to avoid clipping edge cases before haversine post-filter
const BBOX_DELTA = 0.006;
const RADIUS_M = 500;

// DA Supabase — same project as map-viewer-restructured (nsw-planning-etl populates it)
const getDaSupabase = () =>
  createClient(
    process.env.DA_SUPABASE_URL!,
    process.env.DA_SUPABASE_ANON_KEY!,
  );

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
  NumberOfStoreys?: number | string | null;
  DemolitionDwellings?: number | string | null;
  SubdivisionProposedFlag?: string | null;
  EpiVariationProposedFlag?: string | null;
  AccompaniedByVpaFlag?: string | null;
  DevelopmentSubjectToSicFlag?: string | null;
  DevelopmentCategory?: string | null;
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
 * Query ETL Supabase (development_applications + complying_development_certificates)
 * within a bounding box (±BBOX_DELTA°) and last WINDOW_DAYS days, then
 * post-filter to RADIUS_M via haversine. Sorted closest first.
 */
async function queryNearbyApplications(lat: number, lng: number): Promise<Application[]> {
  const since = new Date(Date.now() - WINDOW_DAYS * 86_400_000).toISOString().slice(0, 10);
  const supabase = getDaSupabase();

  const minLat = lat - BBOX_DELTA;
  const maxLat = lat + BBOX_DELTA;
  const minLng = lng - BBOX_DELTA;
  const maxLng = lng + BBOX_DELTA;

  const [daResult, cdcResult] = await Promise.all([
    supabase
      .from('development_applications')
      .select(
        'planning_portal_id,council_name,address,description,application_status,determination_date,' +
        'cost_of_development,latitude,longitude,development_type,lodgement_date,proposed_dwellings,' +
        'number_of_storeys,demolition_dwellings,subdivision_proposed_flag,' +
        'epi_variation_proposed_flag,accompanied_by_vpa_flag,development_subject_to_sic_flag,development_category',
      )
      // ETL fetches by DeterminationDate — match on either date to capture recently-determined apps
      .or(`lodgement_date.gte.${since},determination_date.gte.${since}`)
      .gte('latitude', minLat).lte('latitude', maxLat)
      .gte('longitude', minLng).lte('longitude', maxLng),
    supabase
      .from('complying_development_certificates')
      .select(
        'planning_portal_id,council_name,address,description,application_status,determination_date,' +
        'cost_of_development,latitude,longitude,development_type,submission_date,number_of_new_dwellings,' +
        'number_of_storeys,number_of_demolition_dwellings',
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
      NumberOfStoreys: row.number_of_storeys ?? null,
      DemolitionDwellings: row.demolition_dwellings ?? null,
      SubdivisionProposedFlag: row.subdivision_proposed_flag ?? null,
      EpiVariationProposedFlag: row.epi_variation_proposed_flag ?? null,
      AccompaniedByVpaFlag: row.accompanied_by_vpa_flag ?? null,
      DevelopmentSubjectToSicFlag: row.development_subject_to_sic_flag ?? null,
      DevelopmentCategory: row.development_category ?? null,
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
      LodgementDate: row.submission_date,
      DeterminationDate: row.determination_date,
      Status: row.application_status,
      PropertyAddress: row.address,
      CostOfDevelopment: row.cost_of_development,
      NumberOfNewDwellings: row.number_of_new_dwellings,
      CouncilName: row.council_name,
      Latitude: row.latitude as number,
      Longitude: row.longitude as number,
      _distance_m: Math.round(dist),
      NumberOfStoreys: row.number_of_storeys ?? null,
      DemolitionDwellings: row.number_of_demolition_dwellings ?? null,
      SubdivisionProposedFlag: null,
      EpiVariationProposedFlag: null,
      AccompaniedByVpaFlag: null,
      DevelopmentSubjectToSicFlag: null,
      DevelopmentCategory: null,
    });
  }

  return apps.sort((a, b) => (a._distance_m ?? Infinity) - (b._distance_m ?? Infinity));
}

/**
 * LGA-wide aggregate stats (last 12 months) — approval rate, avg determination
 * time, top development types.  Non-fatal: returns null on any error.
 */
async function queryLgaStats(councilName: string) {
  try {
    const supabase = getDaSupabase();
    const since = new Date(Date.now() - 365 * 86_400_000).toISOString().slice(0, 10);

    const { data, error } = await supabase
      .from('development_applications')
      .select('application_status,determination_date,lodgement_date,cost_of_development,development_type')
      .eq('council_name', councilName)
      .gte('lodgement_date', since)
      .limit(5000);

    if (error || !data) return null;

    let total = 0;
    let approved = 0;
    let totalCost = 0;
    let detTimeSum = 0;
    let detTimeCount = 0;
    const devTypes: Record<string, number> = {};

    for (const row of data) {
      total++;
      const status = (row.application_status ?? '').toLowerCase();
      if (status.includes('approved') || (status.includes('determined') && !status.includes('undetermined'))) approved++;

      const cost = Number(row.cost_of_development) || 0;
      totalCost += cost;

      if (row.lodgement_date && row.determination_date) {
        const lodged = new Date(row.lodgement_date).getTime();
        const determined = new Date(row.determination_date).getTime();
        if (determined >= lodged) {
          detTimeSum += (determined - lodged) / 86_400_000;
          detTimeCount++;
        }
      }

      // Parse dev type JSON array
      const dtRaw = row.development_type;
      if (dtRaw) {
        try {
          const arr = JSON.parse(dtRaw) as Array<{ DevelopmentType?: string }>;
          for (const d of arr) {
            const t = d.DevelopmentType;
            if (t) devTypes[t] = (devTypes[t] || 0) + 1;
          }
        } catch { /* not JSON */ }
      }
    }

    const topDevTypes = Object.entries(devTypes)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([type, count]) => ({ type, count }));

    return {
      total_applications: total,
      approval_rate: total > 0 ? Math.round((approved / total) * 100) : null,
      avg_determination_days: detTimeCount > 0 ? Math.round(detTimeSum / detTimeCount) : null,
      total_construction_value: totalCost,
      top_development_types: topDevTypes,
      period_months: 12,
    };
  } catch (err) { // qa-ignore silent-failure — intentional: LGA stats are supplementary, null hides the panel
    console.error('[threat-radar] LGA stats query failed:', err);
    return null;
  }
}

/**
 * POST /api/satellite/threat-radar/search
 * Body: { address: string }
 *
 * Returns DA/CDC applications within 500m of the address (last 180 days),
 * sourced from the ETL Supabase (populated daily by nsw-planning-etl GH Actions).
 * Sorted closest first.
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

  // Resolve address → lat/lng
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

  const lot_polygon = propData.lotGeometry?.rings?.length
    ? esriRingsToGeoJSON(propData.lotGeometry.rings)
    : null;

  if (!lat || !lng) {
    return NextResponse.json(
      { error: 'Could not determine coordinates for this address' },
      { status: 422 },
    );
  }

  // Resolve council name for display (non-fatal)
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

  // Run nearby apps first, then use the DB's own council_name for LGA stats
  // (Planning Portal returns "Inner West" but DA table stores "Inner West Council")
  let applications: Application[] = [];
  let lgaStats: Awaited<ReturnType<typeof queryLgaStats>> = null;
  try {
    applications = await queryNearbyApplications(lat, lng);
    // Extract council_name from the DAs themselves — guaranteed to match the DB column
    const dbCouncilName = applications.find(a => a.CouncilName)?.CouncilName ?? council_name;
    if (dbCouncilName) {
      council_name = dbCouncilName;
      lgaStats = await queryLgaStats(dbCouncilName);
    }
  } catch (err) { // qa-ignore silent-failure — intentional: return empty results rather than 500, UI shows "No applications found"
    console.error('[threat-radar] DA query failed:', err);
  }
  const run_date = new Date().toISOString().slice(0, 10);
  const report_token = signReport(lat, lng, address, run_date);

  return NextResponse.json({
    address,
    prop_id,
    lat,
    lng,
    run_date,
    council_name,
    applications,
    window_days: WINDOW_DAYS,
    radius_m: RADIUS_M,
    report_token,
    lga_stats: lgaStats,
    lot_polygon,
  });
}
