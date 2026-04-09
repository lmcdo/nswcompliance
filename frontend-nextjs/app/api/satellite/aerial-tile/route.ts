import { NextRequest, NextResponse } from 'next/server';
import {
  aerialTileRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!;

// NSW bounding box with small margin
const NSW_LAT = { min: -38.0, max: -28.0 };
const NSW_LNG = { min: 140.5, max: 154.0 };

export async function GET(request: NextRequest) {
  // Rate limit — aerial-tile is a PUBLIC_ROUTE so global middleware limiter is skipped.
  const clientIP = getClientIdentifier(request);
  const rl = await checkRateLimit(clientIP, aerialTileRateLimiter, 30, 60000);
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Rate limit exceeded. Please try again later.' },
      { status: 429, headers: createRateLimitHeaders(rl) },
    );
  }

  const { searchParams } = request.nextUrl;
  const rawLat = searchParams.get('lat');
  const rawLng = searchParams.get('lng');

  if (!rawLat || !rawLng) {
    return NextResponse.json({ error: 'lat and lng required' }, { status: 400 });
  }

  // Parse and validate — prevents parameter injection into the upstream URL
  const lat = parseFloat(rawLat);
  const lng = parseFloat(rawLng);

  if (
    !isFinite(lat) || !isFinite(lng) ||
    lat < NSW_LAT.min || lat > NSW_LAT.max ||
    lng < NSW_LNG.min || lng > NSW_LNG.max
  ) {
    return NextResponse.json(
      { error: 'Coordinates must be valid numbers within NSW bounds' },
      { status: 400 },
    );
  }

  const url = `https://maps.googleapis.com/maps/api/staticmap?center=${lat},${lng}&zoom=19&size=600x300&maptype=satellite&key=${KEY}`;

  const res = await fetch(url);
  if (!res.ok) {
    // Do not echo back the upstream URL or query params
    return NextResponse.json({ error: 'Failed to fetch aerial tile' }, { status: 502 });
  }

  const buffer = await res.arrayBuffer();
  return new NextResponse(buffer, {
    headers: {
      'Content-Type': res.headers.get('Content-Type') ?? 'image/png',
      'Cache-Control': 'public, max-age=86400',
    },
  });
}
