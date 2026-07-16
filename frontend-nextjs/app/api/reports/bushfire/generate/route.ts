/**
 * POST /api/reports/bushfire/generate
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
  BushfireReportDocument,
  type BushfireReportData,
} from '@/lib/pdf/bushfire-report';
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
  let body: { data?: unknown; report_token?: string; report_id?: string; firm_name?: string };
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
    is_paid = false;
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;
  const today = new Date().toISOString().split('T')[0];

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';
  const shareable_url = body.report_id ? `${origin}/reports/bushfire/${body.report_id}` : null;

  const [tile_b64, logo_b64, qr_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng, 'property') : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
    shareable_url ? generateQRBase64(shareable_url) : Promise.resolve(null),
  ]);

  const rawOutputs = (raw.outputs as Record<string, unknown> | null) ?? raw;
  const compliance = (rawOutputs.compliance as Record<string, unknown> | null) ?? {};

  const data: BushfireReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date ?? today),
    lat: lat ?? 0,
    lng: lng ?? 0,
    is_bushfire_prone: rawOutputs.is_bushfire_prone != null ? Boolean(rawOutputs.is_bushfire_prone) : null,
    designation_source: (rawOutputs.designation_source as string | null) ?? null,
    designation_category: (rawOutputs.designation_category as string | null) ?? null,
    designation_guideline: (rawOutputs.designation_guideline as string | null) ?? null,
    estimated_bal_band: (rawOutputs.estimated_bal_band as string | null) ?? null,
    bal_assessment_likely_required: rawOutputs.bal_assessment_likely_required != null ? Boolean(rawOutputs.bal_assessment_likely_required) : null,
    bal_formal_assessment_cost_range: (rawOutputs.bal_formal_assessment_cost_range as string | null) ?? null,
    bal_assessor_directory_url: (rawOutputs.bal_assessor_directory_url as string | null) ?? null,
    fire_signal: String(rawOutputs.fire_signal ?? 'unavailable'),
    compliance: {
      state_legislation: (compliance.state_legislation as string | null) ?? null,
      rfs_referral_required: compliance.rfs_referral_required != null ? Boolean(compliance.rfs_referral_required) : null,
      rfs_referral_note: (compliance.rfs_referral_note as string | null) ?? null,
      rfs_referral_triggers: Array.isArray(compliance.rfs_referral_triggers) ? (compliance.rfs_referral_triggers as string[]) : null,
      cdc_pathway_available: compliance.cdc_pathway_available != null ? Boolean(compliance.cdc_pathway_available) : null,
      clearing_10_50_entitled: compliance.clearing_10_50_entitled != null ? Boolean(compliance.clearing_10_50_entitled) : null,
      clearing_10_50_exceptions: (compliance.clearing_10_50_exceptions as string | null) ?? null,
      cross_overlays: Array.isArray(compliance.cross_overlays)
        ? (compliance.cross_overlays as BushfireReportData['compliance']['cross_overlays'])
        : null,
      estimated_consultant_costs: (compliance.estimated_consultant_costs as string | null) ?? null,
      zone: (compliance.zone as string | null) ?? null,
      compliance_depth: String(compliance.compliance_depth ?? 'basic'),
      legislation_url: (compliance.legislation_url as string | null) ?? null,
    },
    data_currency: String(rawOutputs.data_currency ?? 'unknown'),
    confidence: String(raw.confidence ?? 'medium'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    is_paid,
    lot_polygon: (raw.lot_polygon as BushfireReportData['lot_polygon']) ?? (rawOutputs.lot_polygon as BushfireReportData['lot_polygon']) ?? null,
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
      React.createElement(BushfireReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[bushfire/generate] PDF render error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const filename = `bushfire-report-${slug}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
