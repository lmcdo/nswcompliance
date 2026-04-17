import { NextRequest, NextResponse } from 'next/server';

const NSW_API_BASE = process.env.NSW_PLANNING_API_BASE_URL || 'https://api.apps1.nsw.gov.au/planning';
const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:8000';

const NSW_HEADERS = {
  'Origin': 'https://www.planningportal.nsw.gov.au',
  'Referer': 'https://www.planningportal.nsw.gov.au/',
};

export async function POST(req: NextRequest) {
  const { address } = await req.json();
  if (!address?.trim()) {
    return NextResponse.json({ error: 'Address required' }, { status: 400 });
  }

  // 1. Resolve address → propId + coordinates
  const addrRes = await fetch(
    `${NSW_API_BASE}/viewersf/V1/ePlanningApi/address?a=${encodeURIComponent(address)}&noOfRecords=1`,
    { headers: NSW_HEADERS }
  );
  if (!addrRes.ok) {
    return NextResponse.json({ error: 'Could not resolve address — try the full street address including suburb and postcode' }, { status: 422 });
  }
  const addrData = await addrRes.json();
  const property = addrData?.[0];
  if (!property?.propId) {
    return NextResponse.json({ error: 'Address not found in NSW Planning Portal' }, { status: 404 });
  }

  const propId = String(property.propId);

  // 2. Get lot geometry for area calculation
  const lotRes = await fetch(
    `${NSW_API_BASE}/viewersf/V1/ePlanningApi/lot?propId=${propId}`,
    { headers: NSW_HEADERS }
  );
  let lotArea: number | null = null;
  if (lotRes.ok) {
    const lotData = await lotRes.json();
    const geom = lotData?.geometry;
    if (geom?.rings) {
      // Compute area from EPSG:3857 rings (metres)
      const ring = geom.rings[0];
      if (ring?.length >= 3) {
        let area = 0;
        for (let i = 0; i < ring.length - 1; i++) {
          area += ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
        }
        lotArea = Math.abs(area) / 2;
      }
    }
  }

  // 3. SEPP Housing 2021 minimum lot area check
  const SEPP_MIN_M2 = 450;
  const eligible = lotArea !== null ? lotArea >= SEPP_MIN_M2 : null;
  const ineligibleReason = !eligible && lotArea !== null
    ? `Lot area ${Math.round(lotArea)} m² is below the SEPP Housing 2021 minimum of ${SEPP_MIN_M2} m²`
    : null;

  // 4. If eligible, call Railway for full detect (structures, confidence)
  //    This runs in the background for the free tier — we return eligibility immediately.
  //    The full report (confirm step) requires payment.
  let detectId: string | null = null;
  if (eligible) {
    try {
      const detectRes = await fetch(`${PYTHON_API_URL}/pipeline/granny-flat/detect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, prop_id: propId, lat: 0, lng: 0 }),
        signal: AbortSignal.timeout(5000), // don't block on this
      });
      if (detectRes.ok) {
        const d = await detectRes.json();
        detectId = d.detect_id ?? null;
        if (d.lot_area_m2) lotArea = d.lot_area_m2; // prefer Railway's value
      }
    } catch {
      // Non-blocking — eligibility result still valid
    }
  }

  return NextResponse.json({
    detect_id: detectId,
    address: property.address ?? address,
    lot_area_m2: lotArea ? Math.round(lotArea * 10) / 10 : null,
    sepp_eligible: eligible ?? false,
    sepp_ineligible_reason: ineligibleReason,
    confirmation_required: false,
  });
}
