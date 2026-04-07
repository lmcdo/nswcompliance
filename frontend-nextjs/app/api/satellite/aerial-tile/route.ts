import { NextRequest, NextResponse } from 'next/server';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const lat = searchParams.get('lat');
  const lng = searchParams.get('lng');

  if (!lat || !lng) {
    return NextResponse.json({ error: 'lat and lng required' }, { status: 400 });
  }

  const url = `https://maps.googleapis.com/maps/api/staticmap?center=${lat},${lng}&zoom=19&size=600x300&maptype=satellite&key=${KEY}`;

  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text();
    return NextResponse.json({ error: text, status: res.status, url: url.replace(KEY, 'REDACTED') }, { status: 500 });
  }

  const buffer = await res.arrayBuffer();
  return new NextResponse(buffer, {
    headers: {
      'Content-Type': res.headers.get('Content-Type') ?? 'image/png',
      'Cache-Control': 'public, max-age=86400',
    },
  });
}
