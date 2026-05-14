import { NextRequest, NextResponse } from 'next/server';
import {
  satelliteRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';
import { signReport } from '@/lib/report-token';

export const dynamic = 'force-dynamic';
// Conveyancing pipeline queries multiple APIs — allow up to 60s
export const maxDuration = 60;

const PYTHON_API = process.env.PYTHON_API_URL || 'http://localhost:8000';

/**
 * POST /api/satellite/conveyancing
 * Body: { address: string }
 *
 * Resolves address → fetches LEP controls, spatial overlays, valuation,
 * feasibility analysis from the Python conveyancing pipeline.
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

  const report_id = crypto.randomUUID();

  let pythonResp: Response;
  try {
    pythonResp = await fetch(`${PYTHON_API}/pipeline/conveyancing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ address, report_id }),
      signal: AbortSignal.timeout(55_000),
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json({ error: `Conveyancing pipeline failed: ${msg}` }, { status: 502 });
  }

  if (!pythonResp.ok) {
    const text = await pythonResp.text().catch(() => '');
    return NextResponse.json(
      { error: `Conveyancing pipeline error (${pythonResp.status}): ${text}` },
      { status: 502 },
    );
  }

  const result = await pythonResp.json();
  const report_token = signReport(
    result.lat, result.lng, address, result.run_date ?? '',
  );
  return NextResponse.json({ ...result, report_id, report_token });
}
