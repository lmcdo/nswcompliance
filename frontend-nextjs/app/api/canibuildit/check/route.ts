import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';
import {
  canibuilditCheckLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { getCachedAddressCheck, setCachedAddressCheck } from '@/lib/cache';
import { toLgaSlug } from '@/lib/lga-slug';
import { fetchDcpControls } from '@/lib/dcp-controls-client';
import { NSW_STANDARD_ZONES } from '@/lib/regulatory-constants';

const NSW_API_BASE = process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning';
const NSW_EPLANNING_BASE = 'https://api.apps1.nsw.gov.au/eplanning/data/v0';

// Maps Planning Portal LGA_NAME values → exact council name the NSW ePlanning API expects.
// Ported from services/threat_radar.py _COUNCIL_NAME_MAP.
const COUNCIL_NAME_MAP: Record<string, string> = {
  'council of the city of sydney': 'Council of the City of Sydney',
  'city of sydney': 'Council of the City of Sydney',
  'sydney city council': 'Council of the City of Sydney',
  'sydney': 'Council of the City of Sydney',
  'inner west council': 'Inner West Council',
  'inner west': 'Inner West Council',
  'city of parramatta council': 'City of Parramatta Council',
  'parramatta': 'City of Parramatta Council',
  'northern beaches council': 'Northern Beaches Council',
  'northern beaches': 'Northern Beaches Council',
  'randwick city council': 'Randwick City Council',
  'randwick': 'Randwick City Council',
  'waverley council': 'Waverley Council',
  'waverley': 'Waverley Council',
  'woollahra municipal council': 'Woollahra Municipal Council',
  'woollahra': 'Woollahra Municipal Council',
  'mosman municipal council': 'Mosman Municipal Council',
  'mosman': 'Mosman Municipal Council',
  'north sydney council': 'North Sydney Council',
  'north sydney': 'North Sydney Council',
  'willoughby city council': 'Willoughby City Council',
  'willoughby': 'Willoughby City Council',
  'lane cove municipal council': 'Lane Cove Municipal Council',
  'lane cove': 'Lane Cove Municipal Council',
  'hunters hill council': 'Hunters Hill Council',
  'hunters hill': 'Hunters Hill Council',
  'ryde city council': 'Ryde City Council',
  'ryde': 'Ryde City Council',
  'ku-ring-gai council': 'Ku-ring-gai Council',
  'ku-ring-gai': 'Ku-ring-gai Council',
  'hornsby shire council': 'Hornsby Shire Council',
  'hornsby': 'Hornsby Shire Council',
  'the hills shire council': 'The Hills Shire Council',
  'the hills': 'The Hills Shire Council',
  'blacktown city council': 'Blacktown City Council',
  'blacktown': 'Blacktown City Council',
  'penrith city council': 'Penrith City Council',
  'penrith': 'Penrith City Council',
  'blue mountains city council': 'Blue Mountains City Council',
  'blue mountains': 'Blue Mountains City Council',
  'hawkesbury city council': 'Hawkesbury City Council',
  'hawkesbury': 'Hawkesbury City Council',
  'camden council': 'Camden Council',
  'camden': 'Camden Council',
  'campbelltown city council': 'Campbelltown City Council',
  'campbelltown': 'Campbelltown City Council',
  'wollondilly shire council': 'Wollondilly Shire Council',
  'wollondilly': 'Wollondilly Shire Council',
  'liverpool city council': 'Liverpool City Council',
  'liverpool': 'Liverpool City Council',
  'fairfield city council': 'Fairfield City Council',
  'fairfield': 'Fairfield City Council',
  'canterbury-bankstown council': 'Canterbury-Bankstown Council',
  'canterbury-bankstown city council': 'Canterbury-Bankstown Council',
  'canterbury bankstown': 'Canterbury-Bankstown Council',
  'georges river council': 'Georges River Council',
  'georges river': 'Georges River Council',
  'sutherland shire council': 'Sutherland Shire Council',
  'sutherland': 'Sutherland Shire Council',
  'bayside council': 'Bayside Council',
  'bayside': 'Bayside Council',
  'strathfield municipal council': 'Strathfield Municipal Council',
  'strathfield': 'Strathfield Municipal Council',
  'burwood council': 'Burwood Council',
  'burwood': 'Burwood Council',
  'cumberland council': 'Cumberland Council',
  'cumberland': 'Cumberland Council',
  'central coast council': 'Central Coast Council',
  'central coast': 'Central Coast Council',
  'gosford': 'Central Coast Council',
  'wollongong city council': 'Wollongong City Council',
  'wollongong': 'Wollongong City Council',
  'newcastle city council': 'Newcastle City Council',
  'newcastle': 'Newcastle City Council',
  'lake macquarie city council': 'Lake Macquarie City Council',
  'lake macquarie': 'Lake Macquarie City Council',
};

function normaliseCouncilName(raw: string): string {
  return COUNCIL_NAME_MAP[raw.trim().toLowerCase()] ?? raw.trim();
}
const NSW_HEADERS = {
  'Origin': 'https://www.planningportal.nsw.gov.au',
  'Referer': 'https://www.planningportal.nsw.gov.au/',
};

const SEPP_MIN_M2 = 450;
// SEPP (Housing) 2021 cl 49 "residential zone" definition: R1, R2, R3, R4, R5 (Large Lot Residential).
// R5 and RU5 are the same zone under different LEP generations — include both.
// DQ-30: this exact value is also NSW_STANDARD_ZONES.RESIDENTIAL — consolidated
// (.claude/DATA_QUALITY_TRACKER.md), was independently declared in 4 files.
const PERMITTED_ZONES = NSW_STANDARD_ZONES.RESIDENTIAL as readonly string[];

type CheckResult = 'pass' | 'fail' | 'unknown';

function mercatorToWgs84(xMerc: number, yMerc: number): { lat: number; lng: number } {
  const R = 20037508.342789244;
  const lng = xMerc * 180.0 / R;
  const lat = (Math.atan(Math.exp(yMerc * Math.PI / R)) * 2 - Math.PI / 2) * (180 / Math.PI);
  return { lat, lng };
}

export async function POST(req: NextRequest) {
  // Rate limit: 20 checks/min per IP — stops scrapers, fine for real users
  const clientIP = getClientIdentifier(req);
  const rl = await checkRateLimit(clientIP, canibuilditCheckLimiter, 20, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests. Please wait a moment before checking another address.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  const { address } = await req.json();
  if (!address?.trim()) {
    return NextResponse.json({ error: 'Address required' }, { status: 400 });
  }

  // Address cache: return stored result if checked within last 24 hours.
  // Prevents re-hitting the NSW Planning Portal for the same address.
  const cached = await getCachedAddressCheck(address);
  if (cached) {
    return NextResponse.json({ ...cached, _cached: true });
  }

  // 1. Resolve address → propId
  const addrRes = await fetch(
    `${NSW_API_BASE}/viewersf/V1/ePlanningApi/address?a=${encodeURIComponent(address)}&noOfRecords=1`,
    { headers: NSW_HEADERS }
  );
  if (!addrRes.ok) {
    return NextResponse.json(
      { error: 'Could not resolve address — try the full street address including suburb and postcode' },
      { status: 422 }
    );
  }
  const addrData = await addrRes.json();
  const property = addrData?.[0];
  if (!property?.propId) {
    return NextResponse.json({ error: 'Address not found in NSW Planning Portal' }, { status: 404 });
  }

  const propId = String(property.propId);

  // 2. Parallel: lot geometry + layerintersect
  const [lotRes, layerRes] = await Promise.all([
    fetch(
      `${NSW_API_BASE}/viewersf/V1/ePlanningApi/lot?propId=${propId}`,
      { headers: NSW_HEADERS }
    ),
    fetch(
      `${NSW_API_BASE}/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${propId}&layers=epi`,
      { headers: NSW_HEADERS, signal: AbortSignal.timeout(10000) }
    ),
  ]);

  // 3. Compute lot area + centroid from geometry
  let lotArea: number | null = null;
  let centroidLat: number | null = null;
  let centroidLng: number | null = null;
  let lotPolygon: { type: 'Polygon'; coordinates: number[][][] } | null = null;
  let lotWidthM: number | null = null;
  let lotDepthM: number | null = null;

  if (lotRes.ok) {
    try {
      const lotRaw = await lotRes.json();
      // NSW lot API returns an array of lot objects
      const lotData = Array.isArray(lotRaw) ? lotRaw[0] : lotRaw;
      const rings = lotData?.geometry?.rings;
      if (rings?.[0]?.length >= 3) {
        const ring: [number, number][] = rings[0];
        // Shoelace area in EPSG:3857
        let area = 0;
        for (let i = 0; i < ring.length - 1; i++) {
          area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
        }
        // Centroid first — needed for Mercator correction
        const xMerc = ring.reduce((s, p) => s + p[0], 0) / ring.length;
        const yMerc = ring.reduce((s, p) => s + p[1], 0) / ring.length;
        ({ lat: centroidLat, lng: centroidLng } = mercatorToWgs84(xMerc, yMerc));

        // Apply Mercator cos²(lat) correction — EPSG:3857 overestimates by ~45% at Sydney latitudes
        const latRad = centroidLat * Math.PI / 180;
        const cosLat = Math.cos(latRad);
        lotArea = Math.abs(area) / 2 * cosLat * cosLat;

        // Lot bounding-box dimensions — same Mercator cos(lat) correction on both axes
        const xCoords = ring.map((p) => p[0]);
        const yCoords = ring.map((p) => p[1]);
        const ewM = (Math.max(...xCoords) - Math.min(...xCoords)) * cosLat;
        const nsM = (Math.max(...yCoords) - Math.min(...yCoords)) * cosLat;
        lotWidthM = Math.round(Math.min(ewM, nsM));   // shorter side — typically frontage
        lotDepthM = Math.round(Math.max(ewM, nsM));   // longer side — typically depth

        // Convert ring to WGS84 GeoJSON for lot boundary overlay
        lotPolygon = {
          type: 'Polygon',
          coordinates: [ring.map(([x, y]) => {
            const { lat, lng } = mercatorToWgs84(x, y);
            return [lng, lat];
          })],
        };
      }
    } catch {
      // lot area stays null
    }
  }

  // 4. Parse layerintersect — independent try/catch
  let planningControls: any[] = [];
  try {
    if (layerRes.ok) {
      const data = await layerRes.json();
      planningControls = Array.isArray(data) ? data : [];
    }
  } catch {
    // planningControls stays []
  }

  // Extract zone
  const zoningLayer = planningControls.find((c: any) =>
    c.layerName?.includes('Land Zoning')
  );
  const zoneResult = zoningLayer?.results?.[0] ?? null;
  const zoneRaw: string | null = zoneResult?.Zone ?? null;
  const zone: string | null = zoneRaw ? zoneRaw.split(' ')[0].toUpperCase() : null;
  // LGA and LEP instrument from zoning result
  const lgaName: string | null = zoneResult?.LGA_NAME ?? zoneResult?.Council ?? null;
  const epiName: string | null = zoneResult?.EPI_NAME ?? zoneResult?.LEP_NAME ?? null;

  // Extract heritage (Heritage Map layer — any results = item or HCA, both ineligible under SEPP Cl 37(1)(d))
  const heritageLayer = planningControls.find((c: any) =>
    c.layerName?.toLowerCase().includes('heritage')
  );
  const hasHeritage = (heritageLayer?.results?.length ?? 0) > 0;

  // Extract height of buildings, FSR, minimum lot size from LEP layers
  const hobLayer = planningControls.find((c: any) => /height.*building/i.test(c.layerName ?? ''));
  const hobVal = hobLayer?.results?.[0]?.MAX_B_H ?? hobLayer?.results?.[0]?.B_H ?? hobLayer?.results?.[0]?.HEIGHT ?? null;
  const heightOfBuildings: string | null = hobVal != null ? `${hobVal}m` : null;

  const fsrLayer = planningControls.find((c: any) => /floor.*space.*ratio/i.test(c.layerName ?? ''));
  const fsrVal = fsrLayer?.results?.[0]?.FSR ?? fsrLayer?.results?.[0]?.MAX_FSR ?? null;
  const fsr: string | null = fsrVal != null ? String(fsrVal) : null;

  const minLotLayer = planningControls.find((c: any) =>
    /minimum.*lot.*size|lot.*size.*map/i.test(c.layerName ?? '')
  );
  const minLotVal = minLotLayer?.results?.[0]?.MIN_LOT_SIZE
    ?? minLotLayer?.results?.[0]?.LOT_SIZE
    ?? minLotLayer?.results?.[0]?.MINLOTSIZE
    ?? null;
  const minLotSizeM2: number | null = minLotVal != null ? (parseFloat(String(minLotVal)) || null) : null;

  // 5. Spatial overlays — independent try/catch
  // flood: Hazard MapServer, 12 LGAs only — no rows = unknown UNLESS lga has flood data (then pass)
  // biodiversity/acid_sulfate: Protection MapServer, state-wide — no rows = pass only if query ran
  let overlayTypes = new Set<string>();
  let spatialQueryRan = false;
  let lgaHasFloodData = false;
  if (centroidLng !== null && centroidLat !== null) {
    try {
      const sr = await query(
        `SELECT layer_type FROM spatial_overlays
         WHERE ST_Contains(geom, ST_SetSRID(ST_Point($1, $2), 4326))
         AND layer_type IN ('flood', 'biodiversity', 'acid_sulfate')`,
        [centroidLng, centroidLat]
      );
      overlayTypes = new Set(sr.rows.map((r: any) => r.layer_type));
      spatialQueryRan = true;
    } catch {
      // spatialQueryRan stays false — all spatial checks fall to 'unknown'
    }
  }
  // Check if this LGA has flood coverage — allows returning 'pass' (not 'unknown') for clear properties
  if (lgaName) {
    try {
      const fcr = await query(
        `SELECT 1 FROM spatial_overlays WHERE lga_name = $1 AND layer_type = 'flood' LIMIT 1`,
        [lgaName.toUpperCase()]
      );
      lgaHasFloodData = fcr.rows.length > 0;
    } catch {
      // lgaHasFloodData stays false — flood falls back to 'unknown' (safe)
    }
  }

  // 5b. ePlanning Phase 1: Dual occupancy prohibition (layer 452)
  let dualOccProhibited = false;
  let dualOccQueryRan = false;
  if (centroidLng !== null && centroidLat !== null) {
    try {
      const dualOccRes = await fetch(
        `https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning/Planning_Portal_Local_Provisions/MapServer/452/query?` +
        `geometry=${centroidLng},${centroidLat}&geometryType=esriGeometryPoint&` +
        `spatialRel=esriSpatialRelIntersects&outFields=LAY_CLASS&returnGeometry=false&f=json&inSR=4283`,
        { signal: AbortSignal.timeout(8000) }
      );
      if (dualOccRes.ok) {
        const dualOccData = await dualOccRes.json();
        if (!dualOccData.error && Array.isArray(dualOccData.features)) {
          dualOccProhibited = dualOccData.features.length > 0;
          dualOccQueryRan = true;
        }
      }
    } catch {
      // dualOccQueryRan stays false — check shows 'unknown' not false 'pass'
    }
  }

  // 6. Evaluate all checks
  const checks: {
    lot_area: CheckResult;
    zone: CheckResult;
    heritage: CheckResult;
    flood: CheckResult;
    biodiversity: CheckResult;
    acid_sulfate: CheckResult;
    dual_occ_prohibition: CheckResult;
  } = {
    lot_area: lotArea === null ? 'unknown' : lotArea >= SEPP_MIN_M2 ? 'pass' : 'fail', // qa-ignore: type-boundary — lotArea is number|null from geocode API
    zone: zone === null ? 'unknown' : PERMITTED_ZONES.includes(zone) ? 'pass' : 'fail', // qa-ignore: type-boundary — zone is string|null from geocode API
    heritage: planningControls.length === 0 ? 'unknown' : hasHeritage ? 'fail' : 'pass',
    // flood: fail if in flood zone; pass if LGA has coverage but point is clear; unknown if no LGA data
    flood: overlayTypes.has('flood') ? 'fail' : lgaHasFloodData ? 'pass' : 'unknown',
    // biodiversity/acid_sulfate: state-wide — no rows = pass, but only if query actually ran
    biodiversity: overlayTypes.has('biodiversity') ? 'fail' : spatialQueryRan ? 'pass' : 'unknown',
    acid_sulfate: overlayTypes.has('acid_sulfate') ? 'fail' : spatialQueryRan ? 'pass' : 'unknown',
    // dual occ prohibition: pass only if query ran and returned no features; unknown if query failed or no centroid
    dual_occ_prohibition: !dualOccQueryRan ? 'unknown' : dualOccProhibited ? 'fail' : 'pass',
  };

  // First hard fail in priority order sets the ineligible reason
  const CHECK_ORDER: (keyof typeof checks)[] = ['lot_area', 'zone', 'heritage', 'flood', 'biodiversity', 'acid_sulfate', 'dual_occ_prohibition'];
  const CHECK_LABELS: Record<keyof typeof checks, string> = {
    lot_area: `Lot area ${lotArea ? Math.round(lotArea) + ' m²' : 'unknown'} — minimum 450 m² required under SEPP Housing 2021`,
    zone: `Zone ${zone ?? 'unknown'} is not permitted for secondary dwellings under SEPP Housing 2021 (permitted: R1, R2, R3, R4, R5/RU5)`,
    heritage: 'Property is a heritage item or within a heritage conservation area — secondary dwellings are excluded under SEPP Housing 2021 cl 37(1)(d)',
    flood: 'Property is within a flood control lot — secondary dwellings are excluded under SEPP Housing 2021',
    biodiversity: 'Property is within a biodiversity values area — secondary dwellings are excluded under SEPP Housing 2021',
    acid_sulfate: 'Property is within an acid sulfate soils area — secondary dwellings are excluded under SEPP Housing 2021',
    dual_occ_prohibition: 'Property is in a dual occupancy development prohibition area under the local LEP — secondary dwellings may not be permitted',
  };

  const firstFail = CHECK_ORDER.find(k => checks[k] === 'fail');
  // Eligible if no check is a hard fail — unknowns do not block
  const sepp_eligible = firstFail === undefined;
  const sepp_ineligible_reason = firstFail ? CHECK_LABELS[firstFail] : null;

  // DCP coverage flag — only Inner West Council has DCP data as of current dataset
  // Update this when new councils are onboarded (see NEXT_PUBLIC_ENABLED_LGAS)
  const dcp_available = lgaName != null && /inner\s*west/i.test(lgaName);

  // DCP setback controls — query dcp_setback_controls for this LGA
  // Normalise LGA name to the source_council convention (lowercase, underscored)
  let dcpSetbacks: Array<{
    control_type: string;
    value_min: number | null;
    value_max: number | null;
    unit: string | null;
    condition: string | null;
    applicability: string;
    source_text: string | null;
    section_ref: string | null;
  }> = [];
  let dcpSetbacksUnavailable = false;
  if (lgaName) {
    try {
      // Item 5 consolidation: rows come from the ONE guarded implementation
      // via /pipeline/dcp-controls — this route previously ran its own SQL
      // with NO needs_review guard (4 flagged secondary-dwelling rows were
      // served, measured 2026-08-03) and its own third copy of the slug map
      // (now lib/lga-slug.ts, the single mapper).
      const normLga = toLgaSlug(lgaName);
      if (normLga) {
        const dcp = await fetchDcpControls(normLga);
        dcpSetbacks = (dcp.available && dcp.rows ? dcp.rows : [])
          .filter((r) => r.dev_type === 'secondary_dwelling')
          .map((r) => ({
            control_type: r.semantic_type,
            value_min: r.value_min,
            value_max: r.value_max,
            unit: r.unit,
            condition: r.notes || null,
            // Passed through unchanged — fabricating a plausible value here
            // would erase real qualifications (Sol, 2026-08-04).
            applicability: r.applicability ?? 'unspecified',
            source_text: r.source_text,
            section_ref: r.clause || null,
          }));
      }
    } catch {
      // Typed absence: an unreachable source is NOT the same response as a
      // completed zero-row lookup — the flag makes the difference visible
      // to consumers (Sol, 2026-08-04) while keeping the check non-blocking.
      dcpSetbacksUnavailable = true;
    }
  }

  // 7. Nearby secondary dwelling DAs + CDCs from NSW ePlanning API
  // Note: detect is NOT pre-fired here. The frontend's runDetect triggers via Trigger.dev
  // after eligibility cards are shown. Pre-firing added 5s latency and was unused (frontend
  // creates its own DB row + Trigger.dev job via /api/satellite/granny-flat POST).
  let nearbySecondaryDwellingCount: number | null = null;

  await Promise.allSettled([
    // Nearby secondary dwelling DAs + CDCs
    (async () => {
      if (!lgaName || centroidLat === null || centroidLng === null) return; // qa-ignore: type-boundary — coords are number|null from geocode
      const since = new Date();
      since.setFullYear(since.getFullYear() - 2);
      const filtersHeader = JSON.stringify({
        filters: { CouncilName: [normaliseCouncilName(lgaName)], LodgementDateFrom: since.toISOString().split('T')[0] },
      });
      const ePlanHdr = {
        ...NSW_HEADERS,
        'filters': filtersHeader,
        'PageSize': '200',
        'PageNumber': '1',
      };

      const daResults = await Promise.allSettled([
        fetch(`${NSW_EPLANNING_BASE}/OnlineDA`, { headers: ePlanHdr, signal: AbortSignal.timeout(2000) }),
        fetch(`${NSW_EPLANNING_BASE}/OnlineCDC`, { headers: ePlanHdr, signal: AbortSignal.timeout(2000) }),
      ]);

      const apps: any[] = [];
      for (const r of daResults) {
        if (r.status === 'fulfilled' && r.value.ok) {
          const d = await r.value.json();
          apps.push(...(d?.Application ?? d?.ApplicationList ?? []));
        }
      }

      const clat = centroidLat;
      const clng = centroidLng;
      let count = 0;
      for (const app of apps) {
        // Coordinates are in Location[0].X (lng) / Location[0].Y (lat) as strings
        const loc = (app?.Location ?? [])[0];
        const alat = parseFloat(loc?.Y ?? '0');
        const alng = parseFloat(loc?.X ?? '0');
        if (!alat || !alng) continue;
        // Haversine distance
        const R = 6371000;
        const φ1 = clat * Math.PI / 180;
        const φ2 = alat * Math.PI / 180;
        const Δφ = (alat - clat) * Math.PI / 180;
        const Δλ = (alng - clng) * Math.PI / 180;
        const a = Math.sin(Δφ / 2) ** 2 + Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
        const dist = R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        if (dist > 500) continue;
        // DevelopmentType is an array of objects: [{DevelopmentType: "Secondary dwelling"}, ...]
        const devTypes: string[] = ((app?.DevelopmentType ?? []) as Array<{ DevelopmentType?: string }>)
          .map((dt) => (dt?.DevelopmentType ?? '').toLowerCase());
        if (devTypes.some((t) => t.includes('secondary dwelling') || t.includes('granny flat'))) {
          count++;
        }
      }
      if (count > 0) nearbySecondaryDwellingCount = count;
    })(),
  ]);

  const result = {
    detect_id: null,
    address: property.address ?? address,
    lat: centroidLat,
    lng: centroidLng,
    lot_polygon: lotPolygon,
    lga_name: lgaName,
    epi_name: epiName,
    lot_area_m2: lotArea ? Math.round(lotArea * 10) / 10 : null,
    lot_width_m: lotWidthM,
    lot_depth_m: lotDepthM,
    zone,
    height_of_buildings: heightOfBuildings,
    fsr,
    min_lot_size_m2: minLotSizeM2,
    nearby_secondary_dwelling_count: nearbySecondaryDwellingCount,
    dcp_available,
    sepp_eligible,
    sepp_ineligible_reason,
    checks,
    dcp_setbacks: dcpSetbacks,
    // true when the guarded source could not be reached — distinguishes
    // "no controls found" from "the lookup did not complete".
    dcp_setbacks_unavailable: dcpSetbacksUnavailable,
    confirmation_required: false,
  };

  // Cache result for 24 hours — non-blocking, failure is silent
  void setCachedAddressCheck(address, result as Record<string, unknown>);

  return NextResponse.json(result);
}
