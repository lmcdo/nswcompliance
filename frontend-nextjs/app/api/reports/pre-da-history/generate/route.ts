/**
 * POST /api/reports/pre-da-history/generate
 * Body: { report_id: string } — production path, queries DB
 *   OR: { data: PreDAHistoryReportData } — direct path for testing without a DB record
 *
 * Streams back application/pdf.
 */

import { NextRequest, NextResponse } from 'next/server';
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import { createClient as createServiceClient } from '@supabase/supabase-js';
import {
  PreDAHistoryReportDocument,
  type PreDAHistoryReportData,
} from '@/lib/pdf/pre-da-history-report';
import { getLogoBase64 } from '@/lib/pdf/logo';

const getSupabase = () =>
  createServiceClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
  );

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

export async function POST(req: NextRequest) {
  let body: { report_id?: string; data?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  let data: PreDAHistoryReportData;
  let filename: string;

  if (body?.data && typeof body.data === 'object') {
    // --- Direct data path (testing / preview) ---
    const raw = body.data as Record<string, unknown>;
    if (!raw.address) {
      return NextResponse.json({ error: 'data.address is required' }, { status: 400 });
    }

    data = {
      address: String(raw.address),
      run_date: String(raw.run_date ?? new Date().toISOString().split('T')[0]),
      lat: typeof raw.lat === 'number' ? raw.lat : 0,
      lon: typeof raw.lon === 'number' ? raw.lon : 0,
      council: typeof raw.council === 'string' ? raw.council : null,
      heritage_flag: Boolean(raw.heritage_flag),
      heritage_note: typeof raw.heritage_note === 'string' ? raw.heritage_note : null,
      timeline: Array.isArray(raw.timeline) ? (raw.timeline as PreDAHistoryReportData['timeline']) : [],
      wayback_ssim: (raw.wayback_ssim as Record<string, number>) ?? {},
      data_quality_note: String(raw.data_quality_note ?? ''),
      logo_b64: getLogoBase64(),
      is_paid: false, // Direct data path — defence-in-depth, no paid content
    };
    const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
    filename = `pre-da-history-${slug}.pdf`;
  } else {
    // --- DB path (production) ---
    const report_id = body?.report_id?.trim();
    if (!report_id) {
      return NextResponse.json({ error: 'report_id or data is required' }, { status: 400 });
    }

    const supabase = getSupabase();
    const { data: row, error } = await supabase
      .from('pre_da_history_reports')
      .select('report_json, address, run_date')
      .eq('id', report_id)
      .single();

    if (error || !row) {
      return NextResponse.json({ error: 'Report not found' }, { status: 404 });
    }

    const reportJson = row.report_json as Record<string, unknown>;
    if (!reportJson?.timeline) {
      return NextResponse.json({ error: 'Report is not complete' }, { status: 422 });
    }

    data = {
      address: (reportJson.address as string) ?? row.address,
      run_date: (reportJson.run_date as string) ?? row.run_date,
      lat: reportJson.lat as number,
      lon: reportJson.lon as number,
      council: (reportJson.council as string | null) ?? null,
      heritage_flag: Boolean(reportJson.heritage_flag),
      heritage_note: (reportJson.heritage_note as string | null) ?? null,
      timeline: reportJson.timeline as PreDAHistoryReportData['timeline'],
      wayback_ssim: (reportJson.wayback_ssim as Record<string, number>) ?? {},
      data_quality_note: (reportJson.data_quality_note as string) ?? '',
      logo_b64: getLogoBase64(),
      is_paid: true, // DB path = post-Stripe payment, always render paid sections
    };
    filename = `pre-da-history-${report_id.slice(0, 8)}.pdf`;
  }

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(PreDAHistoryReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[pre-da-history/generate] PDF render error:', err);
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
