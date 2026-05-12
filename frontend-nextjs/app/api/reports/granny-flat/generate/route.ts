/**
 * POST /api/reports/granny-flat/generate
 * Body: { report_id: string } — production path, queries DB
 *   OR: { data: GrannyFlatReportData } — direct path for testing without a DB record
 *
 * Streams back application/pdf.
 *
 * P2-A: Direct stream — no R2 upload. R2 + Stripe wiring is P2-B.
 */

import { NextRequest, NextResponse } from 'next/server';
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import { createClient as createServiceClient } from '@supabase/supabase-js';
import {
  GrannyFlatReportDocument,
  type GrannyFlatReportData,
} from '@/lib/pdf/granny-flat-report';
import { getLogoBase64 } from '@/lib/pdf/logo';
import { generateQRBase64 } from '@/lib/pdf/qr';
import { fetchAerialTileBase64 } from '@/lib/pdf/aerial-tile';

// Use service role — this route is server-only, report_id is an unguessable UUID.
// The anon+cookie client fails with no session (called from webhook or curl).
const getSupabase = () =>
  createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );

export const dynamic = 'force-dynamic';
// PDF generation can take 3–8s — extend Vercel function timeout
export const maxDuration = 30;

export async function POST(req: NextRequest) {
  let body: { report_id?: string; data?: unknown; firm_name?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  let data: GrannyFlatReportData;
  let filename: string;

  if (body?.data && typeof body.data === 'object') {
    // --- Direct data path (testing / preview) ---
    const raw = body.data as Record<string, unknown>;
    if (!raw.address) {
      return NextResponse.json({ error: 'data.address is required' }, { status: 400 });
    }
    const today = new Date().toISOString().split('T')[0];
    const lat = typeof raw.lat === 'number' ? raw.lat : null;
    const lng = typeof raw.lng === 'number' ? raw.lng : null;

    const [tile_b64, logo_b64] = await Promise.all([
      (raw.tile_b64 as string | null) != null
        ? Promise.resolve(raw.tile_b64 as string)
        : (lat && lng) ? fetchAerialTileBase64(lat, lng, 'property') : Promise.resolve(null),
      Promise.resolve(getLogoBase64()),
    ]);

    data = {
      address: String(raw.address),
      run_date: String(raw.run_date ?? today),
      lot_area_m2: raw.lot_area_m2 != null ? Number(raw.lot_area_m2) : null,
      main_dwelling_area_m2: raw.main_dwelling_area_m2 != null ? Number(raw.main_dwelling_area_m2) : null,
      confirmed_structure_count: raw.confirmed_structure_count != null ? Number(raw.confirmed_structure_count) : null,
      granny_flat_buildable: Boolean(raw.granny_flat_buildable),
      max_floor_area_m2: Number(raw.max_floor_area_m2 ?? 0),
      estimated_weekly_rent_aud: raw.estimated_weekly_rent_aud != null ? Number(raw.estimated_weekly_rent_aud) : null,
      rental_yield_annual_pct: raw.rental_yield_annual_pct != null ? Number(raw.rental_yield_annual_pct) : null,
      assumed_build_cost_aud: raw.assumed_build_cost_aud != null ? Number(raw.assumed_build_cost_aud) : null,
      confidence: String(raw.confidence ?? 'low'),
      confidence_reason: String(raw.confidence_reason ?? ''),
      warnings: Array.isArray(raw.warnings) ? (raw.warnings as string[]) : [],
      data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
      tile_b64,
      logo_b64,
      is_paid: !!(process.env.ADMIN_SECRET && req.headers.get('x-admin-key') === process.env.ADMIN_SECRET && (body as Record<string, unknown>).is_paid === true),
    };
    const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
    filename = `granny-flat-report-${slug}.pdf`;
  } else {
    // --- DB path (production) ---
    const report_id = body?.report_id;
    if (!report_id || typeof report_id !== 'string' || !report_id.trim()) {
      return NextResponse.json({ error: 'report_id or data is required' }, { status: 400 });
    }

    const supabase = getSupabase();
    const { data: row, error } = await supabase
      .from('granny_flat_reports')
      .select('address, run_date, inputs, outputs, confidence')
      .eq('id', report_id.trim())
      .single();

    if (error || !row) {
      return NextResponse.json({ error: 'Report not found' }, { status: 404 });
    }

    const inputs = (row.inputs ?? {}) as Record<string, unknown>;
    const outputs = (row.outputs ?? {}) as Record<string, unknown>;

    if (!outputs || outputs.granny_flat_buildable === undefined) {
      return NextResponse.json({ error: 'Report is not yet complete' }, { status: 422 });
    }

    data = {
      address: row.address ?? 'Unknown address',
      run_date: row.run_date ?? new Date().toISOString().split('T')[0],
      lot_area_m2: (inputs.lot_area_m2 as number | null) ?? null,
      main_dwelling_area_m2: (inputs.main_dwelling_area_m2 as number | null) ?? null,
      confirmed_structure_count: (inputs.confirmed_structure_count as number | null) ?? null,
      granny_flat_buildable: outputs.granny_flat_buildable as boolean,
      max_floor_area_m2: (outputs.max_floor_area_m2 as number) ?? 0,
      estimated_weekly_rent_aud: (outputs.estimated_weekly_rent_aud as number | null) ?? null,
      rental_yield_annual_pct: (outputs.rental_yield_annual_pct as number | null) ?? null,
      assumed_build_cost_aud: (outputs.assumed_build_cost_aud as number | null) ?? null,
      confidence: (outputs.confidence as string) ?? row.confidence ?? 'low',
      confidence_reason: (outputs.confidence_reason as string) ?? '',
      warnings: (outputs.warnings as string[]) ?? [],
      data_sources: (outputs.data_sources as string[]) ?? [],
      tile_b64: (outputs.tile_b64 as string | null) ?? null,
      logo_b64: getLogoBase64(),
      is_paid: true, // UUID access = sufficient guard; always render paid sections for DB-fetched reports
    };

    const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://canibuildit.com.au';
    const shareable_url = `${origin}/reports/granny-flat/${report_id}`;
    data.shareable_url = shareable_url;
    data.qr_b64 = await generateQRBase64(shareable_url);
    data.firm_name = body.firm_name?.trim() || null;

    filename = `granny-flat-report-${report_id.slice(0, 8)}.pdf`;
  }

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(GrannyFlatReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[granny-flat/generate] PDF render error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
