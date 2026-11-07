import { NextRequest, NextResponse } from 'next/server';

// prior-art-checked: thin proxy copied from app/api/housing-sepp/gates/route.ts (same error pass-through). The rules live in
// services/lmr_area_decision.py and the measurements in services/lmr_area_inputs.py; none here. The gates route is kept until no page reads it.

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * GET /api/housing-sepp/area-check?lat=&lng=
 *
 * The full state-law area answer for the lot at this point: low and mid-rise walking limit, Chapter 5 (TOD) map rule and the
 * s164 exclusions, each with clause, page and law version date. A check that could not be completed comes back saying so
 * ("Not determined"); it is never turned into a yes or a no here.
 */
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const toNumber = (raw: unknown): number =>
    typeof raw === 'string' && raw.trim() !== '' ? Number(raw) : NaN;
  const lat = toNumber(searchParams.get('lat'));
  const lng = toNumber(searchParams.get('lng'));
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return NextResponse.json({ error: 'lat and lng must be numbers' }, { status: 400 });
  }

  let pythonResp: Response;
  try {
    pythonResp = await fetch(
      `${PYTHON_API}/pipeline/housing-sepp/area-check?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`,
      // no-store: the answer carries the law version date; Next's fetch cache served a week-old answer after the rules text changed.
      { cache: 'no-store', signal: AbortSignal.timeout(50_000) },
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Area check failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: text || `Area check service error (${pythonResp.status})` },
      { status: 502 },
    );
  }

  return NextResponse.json(await pythonResp.json());
}
