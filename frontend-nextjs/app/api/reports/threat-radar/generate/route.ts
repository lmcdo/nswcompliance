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
import { verifyReport } from '@/lib/report-token';
import { generateQRBase64 } from '@/lib/pdf/qr';

export const dynamic = 'force-dynamic';
export const maxDuration = 30;
// No rate limit — route is guarded by HMAC (verifyReport). Threat radar has no DB path.

export async function POST(req: NextRequest) {
  let body: { data?: unknown; is_paid?: boolean; report_token?: string; firm_name?: string };
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

  if (lat === null || lng === null || !verifyReport(lat, lng, String(raw.address), String(raw.run_date ?? ''), body.report_token)) {
    return NextResponse.json({ error: 'Invalid or expired report token' }, { status: 403 });
  }

  const [tile_b64, logo_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng, 'property') : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
  ]);

  const today = new Date().toISOString().split('T')[0];
  const is_paid = body.is_paid === true;

  const applications = Array.isArray(raw.applications)
    ? (raw.applications as ThreatRadarReportData['applications'])
    : [];
  const radius_m = typeof raw.radius_m === 'number' ? raw.radius_m : 500;

  const data: ThreatRadarReportData = {
    address: String(raw.address),
    run_date: today,
    lat: lat ?? 0,
    lng: lng ?? 0,
    council_name: (raw.council_name as string | null) ?? null,
    applications,
    window_days: typeof raw.window_days === 'number' ? raw.window_days : 90,
    radius_m,
    lot_polygon: (raw.lot_polygon as ThreatRadarReportData['lot_polygon']) ?? null,
    is_paid,
    tile_b64,
    logo_b64,
    firm_name: body.firm_name?.trim() || null,
    // Threat radar has no DB-backed report page, so no shareable URL or QR
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
