/**
 * POST /api/reports/granny-flat/generate
 * Body: { report_id: string }
 *
 * Queries granny_flat_reports by ID, renders the PDF via @react-pdf/renderer,
 * and streams it back as application/pdf.
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
  let report_id: string | undefined;
  try {
    const body = await req.json();
    report_id = body?.report_id;
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!report_id || typeof report_id !== 'string' || !report_id.trim()) {
    return NextResponse.json({ error: 'report_id is required' }, { status: 400 });
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

  // Guard: report must be complete (not pending or error state)
  if (!outputs || outputs.granny_flat_buildable === undefined) {
    return NextResponse.json(
      { error: 'Report is not yet complete' },
      { status: 422 }
    );
  }

  const data: GrannyFlatReportData = {
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
  };

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

  const filename = `granny-flat-report-${report_id.slice(0, 8)}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
