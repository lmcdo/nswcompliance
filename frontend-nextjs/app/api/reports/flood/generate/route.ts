/**
 * POST /api/reports/flood/generate
 *
 * Two call paths:
 *   A) Stripe webhook: { report_id } — fetches from property_reports, generates paid PDF
 *   B) Legacy direct:  { data, report_token } — verifies HMAC, generates free PDF
 *
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
import { verifyReport } from '@/lib/report-token';
import { generateQRBase64 } from '@/lib/pdf/qr';
import { createClient } from '@supabase/supabase-js';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

export async function POST(req: NextRequest) {
  // No rate limit — route is guarded by DB UUID (Path A) and HMAC (Path B).
  // Webhook calls all originate from the same Vercel internal IP; a 10/min bucket
  // would block PDF delivery above 10 concurrent paid reports.

  let body: { data?: unknown; is_paid?: boolean; report_token?: string; report_id?: string; firm_name?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  let raw: Record<string, unknown>;
  let is_paid: boolean;

  // Path A: webhook call with report_id — fetch from DB, always paid
  if (body.report_id) {
    const { data: row, error } = await getSupabase()
      .from('property_reports')
      .select('address, lat, lng, run_date, outputs, confidence, data_sources')
      .eq('id', body.report_id.trim())
      .single();

    if (error || !row) {
      return NextResponse.json({ error: 'Report not found' }, { status: 404 });
    }

    raw = {
      address: row.address,
      lat: row.lat,
      lng: row.lng,
      run_date: row.run_date,
      confidence: row.confidence,
      data_sources: row.data_sources,
      ...(row.outputs as Record<string, unknown>),
    };
    is_paid = true;

  // Path B: direct call with data + HMAC token — free version
  } else {
    if (!body?.data || typeof body.data !== 'object') {
      return NextResponse.json({ error: 'report_id or data is required' }, { status: 400 });
    }
    raw = body.data as Record<string, unknown>;

    if (!raw.address || !raw.run_date) {
      return NextResponse.json({ error: 'data.address and data.run_date are required' }, { status: 400 });
    }

    const lat = typeof raw.lat === 'number' ? raw.lat : null;
    const lng = typeof raw.lng === 'number' ? raw.lng : null;

    if (lat === null || lng === null || !verifyReport(lat, lng, String(raw.address), String(raw.run_date), body.report_token)) {
      return NextResponse.json({ error: 'Invalid or expired report token' }, { status: 403 });
    }
    const isAdmin = process.env.ADMIN_SECRET && req.headers.get('x-admin-key') === process.env.ADMIN_SECRET;
    is_paid = !!(isAdmin && body.is_paid === true);
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://verify.plotdetect.com.au';
  const shareable_url = body.report_id ? `${origin}/reports/flood/${body.report_id}` : null;

  const [tile_b64, logo_b64, qr_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng, 'property') : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
    shareable_url ? generateQRBase64(shareable_url) : Promise.resolve(null),
  ]);

  const data: FloodReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date),
    lat: lat ?? 0,
    lng: lng ?? 0,
    lga_name: (raw.lga_name as string | null) ?? null,
    epi_flood_class: (raw.epi_flood_class as string | null) ?? null,
    epi_flood_label: (raw.epi_flood_label as string | null) ?? null,
    sar_flood_detected: raw.sar_flood_detected != null ? Boolean(raw.sar_flood_detected) : null,
    sar_confidence: (raw.sar_confidence as string | null) ?? null,
    sar_analysis_date: (raw.sar_analysis_date as string | null) ?? null,
    ems_flood_detected: raw.ems_flood_detected != null ? Boolean(raw.ems_flood_detected) : null,
    ems_activations: (raw.ems_activations as FloodReportData['ems_activations']) ?? null,
    jrc_water_occurrence_pct: raw.jrc_water_occurrence_pct != null ? Number(raw.jrc_water_occurrence_pct) : null,
    jrc_data_year: raw.jrc_data_year != null ? Number(raw.jrc_data_year) : null,
    dea_wofs_frequency_pct: raw.dea_wofs_frequency_pct != null ? Number(raw.dea_wofs_frequency_pct) : null,
    bom_gauge_name: (raw.bom_gauge_name as string | null) ?? null,
    bom_gauge_distance_km: raw.bom_gauge_distance_km != null ? Number(raw.bom_gauge_distance_km) : null,
    bom_last_major_flood_date: (raw.bom_last_major_flood_date as string | null) ?? null,
    bom_last_major_flood_peak_m: raw.bom_last_major_flood_peak_m != null ? Number(raw.bom_last_major_flood_peak_m) : null,
    bom_flood_history: Array.isArray(raw.bom_flood_history) ? (raw.bom_flood_history as BomFloodEvent[]) : null,
    flood_study_name: (raw.flood_study_name as string | null) ?? null,
    flood_study_date: (raw.flood_study_date as string | null) ?? null,
    hawkesbury_flood_level_2aep: raw.hawkesbury_flood_level_2aep != null ? Number(raw.hawkesbury_flood_level_2aep) : null,
    hawkesbury_flood_level_5aep: raw.hawkesbury_flood_level_5aep != null ? Number(raw.hawkesbury_flood_level_5aep) : null,
    hawkesbury_flood_level_10aep: raw.hawkesbury_flood_level_10aep != null ? Number(raw.hawkesbury_flood_level_10aep) : null,
    hawkesbury_flood_level_20aep: raw.hawkesbury_flood_level_20aep != null ? Number(raw.hawkesbury_flood_level_20aep) : null,
    hawkesbury_flood_level_50aep: raw.hawkesbury_flood_level_50aep != null ? Number(raw.hawkesbury_flood_level_50aep) : null,
    hawkesbury_flood_level_100aep: raw.hawkesbury_flood_level_100aep != null ? Number(raw.hawkesbury_flood_level_100aep) : null,
    hawkesbury_flood_level_200aep: raw.hawkesbury_flood_level_200aep != null ? Number(raw.hawkesbury_flood_level_200aep) : null,
    hawkesbury_flood_level_500aep: raw.hawkesbury_flood_level_500aep != null ? Number(raw.hawkesbury_flood_level_500aep) : null,
    hawkesbury_flood_level_pmf: raw.hawkesbury_flood_level_pmf != null ? Number(raw.hawkesbury_flood_level_pmf) : null,
    hawkesbury_flood_study: (raw.hawkesbury_flood_study as string | null) ?? null,
    ground_elevation_m_ahd: raw.ground_elevation_m_ahd != null ? Number(raw.ground_elevation_m_ahd) : null,
    // THREE states. `Boolean(x ?? false)` used to stand here, which collapsed
    // "not assessed" into "not in a flood zone" at the API boundary — the PDF
    // could never see the third state no matter what the pipeline produced.
    // Only an explicit true/false is an answer; anything else is null.
    in_100yr_flood_zone:
      raw.in_100yr_flood_zone === true
        ? true
        : raw.in_100yr_flood_zone === false
          ? false
          : null,
    in_100yr_flood_zone_unconsulted: Array.isArray(raw.in_100yr_flood_zone_unconsulted)
      ? (raw.in_100yr_flood_zone_unconsulted as string[])
      : [],
    flood_studies: Array.isArray(raw.flood_studies) ? raw.flood_studies : [],
    s1_gap_warning: (raw.s1_gap_warning as string | null) ?? null,
    data_currency: String(raw.data_currency ?? 'unknown'),
    flood_signal: (raw.flood_signal as FloodReportData['flood_signal']) ?? null,
    confidence: String(raw.confidence ?? 'low'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    warnings: Array.isArray(raw.warnings) ? (raw.warnings as string[]) : [],
    is_paid,
    lot_polygon: (raw.lot_polygon as FloodReportData['lot_polygon']) ?? null,
    tile_b64,
    logo_b64,
    qr_b64,
    firm_name: body.firm_name?.trim() || null,
    shareable_url,
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
