import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

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
      signal: AbortSignal.timeout(90000),
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Spatial API error' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error('[spatial/tod] fetch failed:', err);
    return NextResponse.json({ error: 'Spatial API unavailable' }, { status: 503 });
  }
}
