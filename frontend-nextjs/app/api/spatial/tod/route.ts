import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const maxDuration = 60;

export async function POST(request: NextRequest) {
  const spatialApiUrl = process.env.SPATIAL_API_URL;
  if (!spatialApiUrl) {
    return NextResponse.json({ error: 'SPATIAL_API_URL not configured' }, { status: 503 });
  }

  try {
    const body = await request.json();
    const response = await fetch(`${spatialApiUrl}/tod`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(55000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Spatial API error' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('[spatial/tod] fetch failed:', msg);
    return NextResponse.json({ error: 'Spatial API unavailable', detail: msg }, { status: 503 });
  }
}

export async function GET() {
  const spatialApiUrl = process.env.SPATIAL_API_URL;
  if (!spatialApiUrl) {
    return NextResponse.json({ configured: false, error: 'SPATIAL_API_URL not set' });
  }
  try {
    const r = await fetch(`${spatialApiUrl}/graph-status`, { signal: AbortSignal.timeout(5000) });
    const data = await r.json();
    return NextResponse.json({ configured: true, spatial_url: spatialApiUrl, graph_status: data });
  } catch (err) {
    return NextResponse.json({ configured: true, spatial_url: spatialApiUrl, error: String(err) });
  }
}
