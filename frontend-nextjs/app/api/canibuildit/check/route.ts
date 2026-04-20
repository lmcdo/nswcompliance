import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

const NSW_API_BASE = process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning';
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';

const NSW_HEADERS = {
  'Origin': 'https://www.planningportal.nsw.gov.au',
  'Referer': 'https://www.planningportal.nsw.gov.au/',
};

const SEPP_MIN_M2 = 450;
const PERMITTED_ZONES = ['R1', 'R2', 'R3', 'RU5'];

type CheckResult = 'pass' | 'fail' | 'unknown';

function mercatorToWgs84(xMerc: number, yMerc: number): { lat: number; lng: number } {
  const R = 20037508.342789244;
  const lng = xMerc * 180.0 / R;
  const lat = (Math.atan(Math.exp(yMerc * Math.PI / R)) * 2 - Math.PI / 2) * (180 / Math.PI);
  return { lat, lng };
}

export async function POST(req: NextRequest) {
  const { address } = await req.json();
  if (!address?.trim()) {
    return NextResponse.json({ error: 'Address required' }, { status: 400 });
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

  if (lotRes.ok) {
    try {
      const lotData = await lotRes.json();
      const rings = lotData?.geometry?.rings;
      if (rings?.[0]?.length >= 3) {
        const ring: [number, number][] = rings[0];
        // Shoelace area in EPSG:3857
        let area = 0;
        for (let i = 0; i < ring.length - 1; i++) {
          area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
        }
        lotArea = Math.abs(area) / 2;

        // Centroid
        const xMerc = ring.reduce((s, p) => s + p[0], 0) / ring.length;
        const yMerc = ring.reduce((s, p) => s + p[1], 0) / ring.length;
        ({ lat: centroidLat, lng: centroidLng } = mercatorToWgs84(xMerc, yMerc));
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
  const zoneRaw: string | null = zoningLayer?.results?.[0]?.Zone ?? null;
  const zone: string | null = zoneRaw ? zoneRaw.split(' ')[0].toUpperCase() : null;

  // Extract heritage (Heritage Map layer — any results = item or HCA, both ineligible under SEPP Cl 37(1)(d))
  const heritageLayer = planningControls.find((c: any) =>
    c.layerName?.toLowerCase().includes('heritage')
  );
  const hasHeritage = (heritageLayer?.results?.length ?? 0) > 0;

  // 5. Spatial overlays — independent try/catch
  // flood: Hazard MapServer, 12 LGAs only — no rows always = unknown (partial coverage)
  // biodiversity/acid_sulfate: Protection MapServer, state-wide — no rows = pass only if query ran
  let overlayTypes = new Set<string>();
  let spatialQueryRan = false;
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

  // 6. Evaluate all checks
  const checks: {
    lot_area: CheckResult;
    zone: CheckResult;
    heritage: CheckResult;
    flood: CheckResult;
    biodiversity: CheckResult;
    acid_sulfate: CheckResult;
  } = {
    lot_area: lotArea === null ? 'unknown' : lotArea >= SEPP_MIN_M2 ? 'pass' : 'fail',
    zone: zone === null ? 'unknown' : PERMITTED_ZONES.includes(zone) ? 'pass' : 'fail',
    heritage: planningControls.length === 0 ? 'unknown' : hasHeritage ? 'fail' : 'pass',
    // flood: always unknown on no hit — partial data coverage (12 LGAs)
    flood: overlayTypes.has('flood') ? 'fail' : 'unknown',
    // biodiversity/acid_sulfate: state-wide — no rows = pass, but only if query actually ran
    biodiversity: overlayTypes.has('biodiversity') ? 'fail' : spatialQueryRan ? 'pass' : 'unknown',
    acid_sulfate: overlayTypes.has('acid_sulfate') ? 'fail' : spatialQueryRan ? 'pass' : 'unknown',
  };

  // First hard fail in priority order sets the ineligible reason
  const CHECK_ORDER: (keyof typeof checks)[] = ['lot_area', 'zone', 'heritage', 'flood', 'biodiversity', 'acid_sulfate'];
  const CHECK_LABELS: Record<keyof typeof checks, string> = {
    lot_area: `Lot area ${lotArea ? Math.round(lotArea) + ' m²' : 'unknown'} — minimum 450 m² required under SEPP Housing 2021`,
    zone: `Zone ${zone ?? 'unknown'} is not permitted for secondary dwellings under SEPP Housing 2021 (permitted: R1, R2, R3, RU5)`,
    heritage: 'Property is a heritage item or within a heritage conservation area — secondary dwellings are excluded under SEPP Housing 2021 cl 37(1)(d)',
    flood: 'Property is within a flood control lot — secondary dwellings are excluded under SEPP Housing 2021',
    biodiversity: 'Property is within a biodiversity values area — secondary dwellings are excluded under SEPP Housing 2021',
    acid_sulfate: 'Property is within an acid sulfate soils area — secondary dwellings are excluded under SEPP Housing 2021',
  };

  const firstFail = CHECK_ORDER.find(k => checks[k] === 'fail');
  // Eligible if no check is a hard fail — unknowns do not block
  const sepp_eligible = firstFail === undefined;
  const sepp_ineligible_reason = firstFail ? CHECK_LABELS[firstFail] : null;

  // 7. Trigger Railway detect if eligible (non-blocking)
  let detectId: string | null = null;
  if (sepp_eligible) {
    try {
      const detectRes = await fetch(`${PYTHON_API_URL}/pipeline/granny-flat/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, prop_id: propId, lat: centroidLat ?? 0, lng: centroidLng ?? 0 }),
        signal: AbortSignal.timeout(5000),
      });
      if (detectRes.ok) {
        const d = await detectRes.json();
        detectId = d.detect_id ?? null;
        if (d.lot_area_m2) lotArea = d.lot_area_m2;
      }
    } catch {
      // Non-blocking — eligibility result still valid
    }
  }

  return NextResponse.json({
    detect_id: detectId,
    address: property.address ?? address,
    lot_area_m2: lotArea ? Math.round(lotArea * 10) / 10 : null,
    zone,
    sepp_eligible,
    sepp_ineligible_reason,
    checks,
    confirmation_required: false,
  });
}
