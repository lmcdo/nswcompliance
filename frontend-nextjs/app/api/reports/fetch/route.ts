/**
 * GET /api/reports/fetch?id=<report_id>
 *
 * Returns report data as JSON for shareable report pages.
 * Uses service role key (bypasses RLS) since paid reports should be
 * accessible to anyone with the link (security through UUID obscurity).
 *
 * Handles both property_reports (satellite products) and
 * pre_da_history_reports (site history).
 */

import { NextRequest, NextResponse } from 'next/server';
import { getAdminClient } from '@/lib/supabase/admin';

export const dynamic = 'force-dynamic';

export async function GET(req: NextRequest) {
  const reportId = req.nextUrl.searchParams.get('id')?.trim();

  if (!reportId) {
    return NextResponse.json({ error: 'id parameter required' }, { status: 400 });
  }

  // UUID format guard — prevents injection attempts
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(reportId)) {
    return NextResponse.json({ error: 'Invalid report ID format' }, { status: 400 });
  }

  const supabase = getAdminClient();

  // Try property_reports first (satellite products)
  const { data: propRow } = await supabase
    .from('property_reports')
    .select('id, product, address, lat, lng, run_date, outputs, confidence, data_sources, inputs')
    .eq('id', reportId)
    .single();

  if (propRow) {
    return NextResponse.json({
      source: 'property_reports',
      product: propRow.product,
      report: {
        id: propRow.id,
        address: propRow.address,
        lat: propRow.lat,
        lng: propRow.lng,
        run_date: propRow.run_date,
        confidence: propRow.confidence,
        data_sources: propRow.data_sources,
        inputs: propRow.inputs,
        ...(propRow.outputs as Record<string, unknown>),
      },
    });
  }

  // Try pre_da_history_reports
  const { data: preDARow } = await supabase
    .from('pre_da_history_reports')
    .select('id, address, run_date, report_json')
    .eq('id', reportId)
    .single();

  if (preDARow) {
    return NextResponse.json({
      source: 'pre_da_history_reports',
      product: 'pre-da-history',
      report: {
        id: preDARow.id,
        address: preDARow.address,
        run_date: preDARow.run_date,
        ...(preDARow.report_json as Record<string, unknown>),
      },
    });
  }

  return NextResponse.json({ error: 'Report not found' }, { status: 404 });
}
