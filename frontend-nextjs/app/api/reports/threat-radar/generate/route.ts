/**
 * POST /api/reports/threat-radar/generate
 * Body: { data: ThreatRadarReportData } — full result from /api/satellite/threat-radar/search
 *
 * Fetches an aerial tile server-side, then renders the Threat Radar PDF.
 * Returns application/pdf stream.
 */

import { NextRequest, NextResponse } from 'next/server';
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import {
  ThreatRadarReportDocument,
  type ThreatRadarReportData,
} from '@/lib/pdf/threat-radar-report';
import { getLogoBase64 } from '@/lib/pdf/logo';
import { fetchAerialTileBase64 } from '@/lib/pdf/aerial-tile';

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

export async function POST(req: NextRequest) {
  let body: { data?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!body?.data || typeof body.data !== 'object') {
    return NextResponse.json({ error: 'data is required' }, { status: 400 });
  }

  const raw = body.data as Record<string, unknown>;

  if (!raw.address) {
    return NextResponse.json({ error: 'data.address is required' }, { status: 400 });
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;

  const [tile_b64, logo_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng) : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
  ]);

  const today = new Date().toISOString().split('T')[0];

  const data: ThreatRadarReportData = {
    address: String(raw.address),
    run_date: today,
    lat: lat ?? 0,
    lng: lng ?? 0,
    council_name: (raw.council_name as string | null) ?? null,
    applications: Array.isArray(raw.applications)
      ? (raw.applications as ThreatRadarReportData['applications'])
      : [],
    window_days: typeof raw.window_days === 'number' ? raw.window_days : 90,
    radius_m: typeof raw.radius_m === 'number' ? raw.radius_m : 500,
    tile_b64,
    logo_b64,
  };

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(ThreatRadarReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[threat-radar/generate] PDF render error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const filename = `threat-radar-report-${slug}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
