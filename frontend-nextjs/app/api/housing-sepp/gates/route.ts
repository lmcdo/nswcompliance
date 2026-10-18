import { NextRequest, NextResponse } from 'next/server';

// prior-art-checked: thin proxy modelled on app/api/upzoning/route.ts (same timeout and error
// pass-through pattern). The gate logic lives in services/housing_sepp_gates_api.py; none here.

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * GET /api/housing-sepp/gates?lat=&lng=
 *
 * Proxies to /pipeline/housing-sepp/gates: whether the point is in a Low and Mid-Rise housing area,
 * as true / false / null (null = the planning map query did not answer).
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const latRaw = searchParams.get('lat');
  const lngRaw = searchParams.get('lng');
  const lat = latRaw === null || latRaw.trim() === '' ? NaN : Number(latRaw);
  const lng = lngRaw === null || lngRaw.trim() === '' ? NaN : Number(lngRaw);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return NextResponse.json({ error: 'lat and lng must be numbers' }, { status: 400 });
  }

  let pythonResp: Response;
  try {
    pythonResp = await fetch(
      `${PYTHON_API}/pipeline/housing-sepp/gates?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`,
      { signal: AbortSignal.timeout(25_000) },
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Housing SEPP gate check failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: text || `Housing SEPP gate service error (${pythonResp.status})` },
      { status: 502 },
    );
  }

  return NextResponse.json(await pythonResp.json());
}
