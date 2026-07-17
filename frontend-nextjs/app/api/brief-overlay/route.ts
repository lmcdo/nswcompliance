/**
 * POST /api/brief-overlay
 *
 * prior-art-checked: "overlay" here is the brief LLM overlay (#742 engine),
 * not spatial/SEPP overlays — app/api/spatial/brief serves PostGIS overlay
 * data and app/api/intelligence-brief triggers the Trigger.dev brief run;
 * neither proxies the new Railway /pipeline/brief-overlay endpoint, which
 * has zero callers until this route.
 *
 * Proxy to Railway's /pipeline/brief-overlay endpoint (the flag-gated brief
 * LLM overlay). Railway checks BRIEF_LLM_OVERLAY_ENABLED server-side and
 * answers { enabled: false, overlay: null } when the feature is dark — this
 * route just forwards.
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const maxDuration = 60; // Stage-1 selection can take ~5-15s

const PYTHON_API = process.env.PYTHON_API_URL;

export async function POST(request: NextRequest) {
  if (!PYTHON_API) {
    return NextResponse.json({ enabled: false, overlay: null });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'invalid JSON body' }, { status: 400 });
  }

  try {
    const upstream = await fetch(`${PYTHON_API}/pipeline/brief-overlay`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(55_000),
    });
    const data = await upstream.json();
    return NextResponse.json(data, { status: upstream.status });
  } catch (err) {
    // Overlay is additive-only: a proxy failure means "no overlay", never an
    // error surfaced to the brief page.
    console.error('[brief-overlay] proxy failure:', err);
    return NextResponse.json({ enabled: false, overlay: null });
  }
}
