import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

/**
 * GET /api/reports/status?jobId=<uuid>
 *
 * Polls property_reports for a completed satellite pipeline job.
 * Frontend polls every 2 seconds after triggering a Trigger.dev task.
 *
 * Returns:
 *   { status: 'pending' }          — row not yet written
 *   { status: 'complete', data: {} } — full report row
 */
export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get('jobId');

  if (!jobId) {
    return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
  }

  const { data, error } = await getSupabase()
    .from('property_reports')
    .select('*')
    .eq('id', jobId)
    .single();

  if (error || !data) {
    return NextResponse.json({ status: 'pending' });
  }

  return NextResponse.json({ status: 'complete', data });
}
