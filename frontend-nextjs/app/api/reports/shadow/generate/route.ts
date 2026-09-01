/**
 * POST /api/reports/shadow/generate
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
  ShadowReportDocument,
  type ShadowReportData,
} from '@/lib/pdf/shadow-report';
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

    const outputs = (row.outputs as Record<string, unknown>) ?? {};
    raw = {
      address: row.address,
      lat: row.lat,
      lng: row.lng,
      run_date: row.run_date,
      confidence: row.confidence,
      data_sources: row.data_sources,
      outputs,
      zone: outputs.zone ?? null,
      warnings: outputs.warnings ?? [],
    };
    is_paid = true;

  // Path B: direct call with data + HMAC token — free version
  } else {
    if (!body?.data || typeof body.data !== 'object') {
      return NextResponse.json({ error: 'report_id or data is required' }, { status: 400 });
    }
    raw = body.data as Record<string, unknown>;

    if (!raw.address) {
      return NextResponse.json({ error: 'data.address is required' }, { status: 400 });
    }

    const lat = typeof raw.lat === 'number' ? raw.lat : null;
    const lng = typeof raw.lng === 'number' ? raw.lng : null;

    if (lat === null || lng === null || !verifyReport(lat, lng, String(raw.address), String(raw.run_date ?? ''), body.report_token)) {
      return NextResponse.json({ error: 'Invalid or expired report token' }, { status: 403 });
    }
    const isAdmin = process.env.ADMIN_SECRET && req.headers.get('x-admin-key') === process.env.ADMIN_SECRET;
    is_paid = !!(isAdmin && body.is_paid === true);
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;
  const today = new Date().toISOString().split('T')[0];

  const rawOutputs = (raw.outputs as Record<string, unknown> | null) ?? raw;
  const lotPoly = (rawOutputs.lot_polygon as { type: 'Polygon'; coordinates: number[][][] } | null) ?? null;

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://verify.plotdetect.com.au';
  const shareable_url = body.report_id ? `${origin}/reports/shadow/${body.report_id}` : null;

  const [tile_b64, logo_b64, qr_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng, 'property', lotPoly) : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
    shareable_url ? generateQRBase64(shareable_url) : Promise.resolve(null),
  ]);

  const data: ShadowReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date ?? today),
    lat: lat ?? 0,
    lng: lng ?? 0,
    zone: (raw.zone as string | null) ?? (rawOutputs.zone as string | null) ?? null,
    lga_name: (rawOutputs.lga_name as string | null) ?? (raw.lga_name as string | null) ?? null,
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
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shadow_on_lot: (sc as any).shadow_on_lot ?? null,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      shadow_polygon: (sc as any).shadow_polygon ?? null,
    })),
    // null = NOT ASSESSED (noon scenario missing/errored) — Boolean() coerced
    // it to false, which rendered a "Concern" verdict from a failed model run
    // (output-grounding fix 1, 2026-08-03).
    adg_compliant: rawOutputs.adg_compliant == null ? null : Boolean(rawOutputs.adg_compliant),
    worst_case_scenario: String(rawOutputs.worst_case_scenario ?? 'jun21_12pm'),
    confidence: String(raw.confidence ?? 'medium'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    warnings: Array.isArray(raw.warnings) ? (raw.warnings as string[]) : [],
    lot_polygon: (rawOutputs.lot_polygon as ShadowReportData['lot_polygon']) ?? null,
    north_proxy_polygon: (rawOutputs.north_proxy_polygon as ShadowReportData['north_proxy_polygon']) ?? null,
    is_paid,
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
