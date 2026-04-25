/**
 * POST /api/reports/shadow/generate
 * Body: { data: ShadowReportData } — full result from /api/satellite/shadow
 *
 * Fetches an aerial tile server-side, then renders the Shadow Detector PDF.
 * Returns application/pdf stream.
 */

import { NextRequest, NextResponse } from 'next/server';
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import {
  ShadowReportDocument,
  type ShadowReportData,
} from '@/lib/pdf/shadow-report';
import { getLogoBase64 } from '@/lib/pdf/logo';

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY!;
const NSW_LAT = { min: -38.0, max: -28.0 };
const NSW_LNG = { min: 140.5, max: 154.0 };

async function fetchAerialTile(lat: number, lng: number): Promise<string | null> {
  if (
    !isFinite(lat) || !isFinite(lng) ||
    lat < NSW_LAT.min || lat > NSW_LAT.max ||
    lng < NSW_LNG.min || lng > NSW_LNG.max ||
    !MAPS_KEY
  ) return null;

  try {
    const url = `https://maps.googleapis.com/maps/api/staticmap?center=${lat},${lng}&zoom=19&size=600x300&maptype=satellite&key=${MAPS_KEY}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(10_000) });
    if (!res.ok) return null;
    const buf = await res.arrayBuffer();
    return Buffer.from(buf).toString('base64');
  } catch {
    return null;
  }
}

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
    (lat && lng) ? fetchAerialTile(lat, lng) : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
  ]);

  const today = new Date().toISOString().split('T')[0];

  // Strip GeoJSON geometry fields — PDF doesn't need them
  const rawOutputs = (raw.outputs as Record<string, unknown> | null) ?? raw;

  const data: ShadowReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date ?? today),
    lat: lat ?? 0,
    lng: lng ?? 0,
    zone: (raw.zone as string | null) ?? null,
    height_m: Number(rawOutputs.height_m ?? raw.height_m ?? 9),
    height_source: (rawOutputs.height_source as string | null) ?? null,
    lep_name: (rawOutputs.lep_name as string | null) ?? null,
    scenarios: ((rawOutputs.scenarios as ShadowReportData['scenarios']) ?? []).map((sc) => ({
      scenario: sc.scenario,
      label: sc.label,
      date: sc.date,
      time_local: sc.time_local,
      shadow_length_m: sc.shadow_length_m,
      shadow_overlap_fraction: sc.shadow_overlap_fraction,
      shadow_direction_deg: sc.shadow_direction_deg,
      overlaps_subject_lot: sc.overlaps_subject_lot,
    })),
    construction_change_score:
      rawOutputs.construction_change_score != null
        ? Number(rawOutputs.construction_change_score)
        : null,
    construction_change_detected: Boolean(rawOutputs.construction_change_detected),
    adg_compliant: Boolean(rawOutputs.adg_compliant),
    worst_case_scenario: String(rawOutputs.worst_case_scenario ?? 'jun21_12pm'),
    confidence: String(raw.confidence ?? 'medium'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    warnings: Array.isArray(raw.warnings) ? (raw.warnings as string[]) : [],
    tile_b64,
    logo_b64,
  };

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(ShadowReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[shadow/generate] PDF render error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const filename = `shadow-report-${slug}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
