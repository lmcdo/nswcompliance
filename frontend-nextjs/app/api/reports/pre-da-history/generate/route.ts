/**
 * POST /api/reports/pre-da-history/generate
 * Body: { report_id: string }
 *
 * Reads report_json from pre_da_history_reports, renders the PDF,
 * and returns it as application/pdf.
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
  let body: { report_id?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const report_id = body?.report_id?.trim();
  if (!report_id) {
    return NextResponse.json({ error: 'report_id is required' }, { status: 400 });
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

  const data: PreDAHistoryReportData = {
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
  };

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

  const filename = `pre-da-history-${report_id.slice(0, 8)}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
