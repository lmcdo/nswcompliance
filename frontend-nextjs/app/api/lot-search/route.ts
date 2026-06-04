/**
 * POST /api/lot-search
 * POST /api/lot-search?summary=true
 *
 * Proxy to Railway's /lot-search and /lot-search/summary endpoints.
 */

import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

const PYTHON_API = process.env.PYTHON_API_URL;

export async function POST(request: NextRequest) {
  if (!PYTHON_API) {
    return NextResponse.json(
      { error: 'PYTHON_API_URL not configured' },
      { status: 503 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const isSummary = request.nextUrl.searchParams.get('summary') === 'true';
  const endpoint = isSummary ? '/lot-search/summary' : '/lot-search';

  try {
    const resp = await fetch(`${PYTHON_API}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    if (!resp.ok) {
      const text = await resp.text();
      return NextResponse.json(
        { error: `Railway returned ${resp.status}`, detail: text },
        { status: resp.status },
      );
    }

    const data = await resp.json();
    return NextResponse.json(data);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: 'Failed to reach lot-search API', detail: message },
      { status: 502 },
    );
  }
}
