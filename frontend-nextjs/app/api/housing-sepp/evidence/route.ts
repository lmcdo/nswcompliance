import { NextRequest, NextResponse } from 'next/server';

// prior-art-checked: thin proxy copied from app/api/housing-sepp/area-check/route.ts (same error pass-through, no-store). All content is built in services/evidence_statement.py; none here (grep app/ components/ hooks/ for evidence, 2026-11-20: no planner evidence page).

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * GET /api/housing-sepp/evidence?lat=&lng=
 *
 * The data behind the printable site evidence page for the lot at this point: the s164 exclusions, the walking range, the council controls and the council files held.
 * A source that did not answer comes back saying so; it is never turned into a yes or a no here.
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
      `${PYTHON_API}/pipeline/housing-sepp/evidence?lat=${encodeURIComponent(String(lat))}&lng=${encodeURIComponent(String(lng))}`,
      // no-store: the answer carries the law version date; Next's fetch cache served a week-old answer after the rules text changed.
      { cache: 'no-store', signal: AbortSignal.timeout(50_000) },
    );
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Evidence statement failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: text || `Evidence service error (${pythonResp.status})` },
      { status: 502 },
    );
  }

  return NextResponse.json(await pythonResp.json());
}
