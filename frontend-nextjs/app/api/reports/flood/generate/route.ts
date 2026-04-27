/**
 * POST /api/reports/flood/generate
 * Body: { data: FloodReportData } — full result from /api/satellite/flood
 *
 * Fetches an aerial tile server-side, then renders the Flood Truth PDF.
 * Returns application/pdf stream.
 */

import { NextRequest, NextResponse } from 'next/server';
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import {
  FloodTruthReportDocument,
  type FloodReportData,
  type BomFloodEvent,
} from '@/lib/pdf/flood-truth-report';
import { getLogoBase64 } from '@/lib/pdf/logo';
import { fetchAerialTileBase64 } from '@/lib/pdf/aerial-tile';
import { checkRateLimit, createRateLimitHeaders, getClientIdentifier, satelliteRateLimiter } from '@/lib/rate-limit';

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

export async function POST(req: NextRequest) {
  const rl = await checkRateLimit(getClientIdentifier(req), satelliteRateLimiter, 10, 60000);
  if (!rl.success) {
    return NextResponse.json({ error: 'Too many requests' }, { status: 429, headers: createRateLimitHeaders(rl) });
  }

  let body: { data?: unknown; is_paid?: boolean };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!body?.data || typeof body.data !== 'object') {
    return NextResponse.json({ error: 'data is required' }, { status: 400 });
  }

  const raw = body.data as Record<string, unknown>;

  // Guard: must have basic fields
  if (!raw.address || !raw.run_date) {
    return NextResponse.json({ error: 'data.address and data.run_date are required' }, { status: 400 });
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;

  // Fetch aerial tile
  const [tile_b64, logo_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng) : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
  ]);

  const is_paid = body.is_paid !== false;

  const data: FloodReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date),
    lat: lat ?? 0,
    lng: lng ?? 0,
    epi_flood_class: (raw.epi_flood_class as string | null) ?? null,
    epi_flood_label: (raw.epi_flood_label as string | null) ?? null,
    sar_flood_detected: raw.sar_flood_detected != null ? Boolean(raw.sar_flood_detected) : null,
    sar_confidence: (raw.sar_confidence as string | null) ?? null,
    sar_analysis_date: (raw.sar_analysis_date as string | null) ?? null,
    ems_flood_detected: raw.ems_flood_detected != null ? Boolean(raw.ems_flood_detected) : null,
    ems_activations: (raw.ems_activations as FloodReportData['ems_activations']) ?? null,
    jrc_water_occurrence_pct: raw.jrc_water_occurrence_pct != null
      ? Number(raw.jrc_water_occurrence_pct) : null,
    jrc_data_year: raw.jrc_data_year != null ? Number(raw.jrc_data_year) : null,
    bom_gauge_name: (raw.bom_gauge_name as string | null) ?? null,
    bom_gauge_distance_km: raw.bom_gauge_distance_km != null
      ? Number(raw.bom_gauge_distance_km) : null,
    bom_last_major_flood_date: (raw.bom_last_major_flood_date as string | null) ?? null,
    bom_last_major_flood_peak_m: raw.bom_last_major_flood_peak_m != null
      ? Number(raw.bom_last_major_flood_peak_m) : null,
    bom_flood_history: Array.isArray(raw.bom_flood_history)
      ? (raw.bom_flood_history as BomFloodEvent[]) : null,
    flood_study_name: (raw.flood_study_name as string | null) ?? null,
    flood_study_date: (raw.flood_study_date as string | null) ?? null,
    s1_gap_warning: (raw.s1_gap_warning as string | null) ?? null,
    data_currency: String(raw.data_currency ?? 'unknown'),
    flood_signal: (raw.flood_signal as FloodReportData['flood_signal']) ?? null,
    confidence: String(raw.confidence ?? 'low'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    warnings: Array.isArray(raw.warnings) ? (raw.warnings as string[]) : [],
    is_paid,
    tile_b64,
    logo_b64,
  };

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(FloodTruthReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[flood/generate] PDF render error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const filename = `flood-report-${slug}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
