import { NextRequest, NextResponse } from 'next/server';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

// prior-art-checked: thin proxy modelled on app/api/satellite/conveyancing/route.ts
// (same rate-limiter, timeout and error-pass-through pattern); the flagged matches
// (PostResultEmailStrip, flood_truth) share only HTTP-verb tokens. All eligibility
// logic lives in services/upzoning_check.py -> housing_sepp_eligibility — none here.

export const dynamic = 'force-dynamic';
// Upzoning pipeline queries the Planning Portal + four live ArcGIS gates — allow up to 60s
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * POST /api/upzoning
 * Body: { address: string }
 *
 * Proxies to the Python /pipeline/upzoning endpoint: per-address Housing-SEPP
 * form eligibility under the 2025 LMR/TOD reforms (live 776/752/759/452 gates,
 * heritage suppression, fail-closed — see services/upzoning_check.py).
 */
export async function POST(request: NextRequest) {
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, satelliteRateLimiter, 10, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  let body: { address?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const address = body.address?.trim();
  if (!address || address.length < 5) {
    return NextResponse.json({ error: 'address is required' }, { status: 400 });
  }

  let pythonResp: Response;
  try {
    pythonResp = await fetch(`${PYTHON_API}/pipeline/upzoning`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address }),
      signal: AbortSignal.timeout(55_000),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Upzoning check failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    // Pass through 4xx address errors so the page can show a useful message;
    // everything else is a 502 (visible failure, never an empty "success").
    const text = await pythonResp.text().catch(() => '');
    const status = pythonResp.status === 422 || pythonResp.status === 400 ? pythonResp.status : 502;
    return NextResponse.json(
      { error: text || `Upzoning pipeline error (${pythonResp.status})` },
      { status },
    );
  }

  return NextResponse.json(await pythonResp.json());
}
