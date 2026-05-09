import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { SharedReportPage } from '@/components/reports/SharedReportPage';
import { getAdminClient } from '@/lib/supabase/admin';

export const dynamic = 'force-dynamic';

export async function generateMetadata(
  { params }: { params: { report_id: string } }
): Promise<Metadata> {
  const supabase = getAdminClient();
  const { data } = await supabase
    .from('pre_da_history_reports')
    .select('address')
    .eq('id', params.report_id)
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Site History Report — ${address}`,
    description: `Satellite change detection and DA history for ${address}. 2017–2024 imagery analysis.`,
    robots: { index: false },
  };
}

export default async function PreDAHistoryReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('pre_da_history_reports')
    .select('id, address, run_date, report_json')
    .eq('id', params.report_id)
    .single();

  if (!row) notFound();

  const report = (row.report_json ?? {}) as Record<string, unknown>;
  const timeline = Array.isArray(report.timeline) ? report.timeline : [];
  const daCount = Array.isArray(report.da_events) ? report.da_events.length : 0;

  return (
    <SharedReportPage
      reportId={row.id}
      product="pre-da-history"
      address={row.address}
      runDate={row.run_date}
      generatePath="/api/reports/pre-da-history/generate"
      highlights={[
        {
          label: 'Timeline events',
          value: `${timeline.length} changes detected`,
          severity: timeline.length > 5 ? 'medium' : 'low',
        },
        {
          label: 'DA/CC applications',
          value: daCount > 0 ? `${daCount} found` : 'None found',
          severity: daCount > 0 ? 'medium' : 'low',
        },
        {
          label: 'Heritage status',
          value: report.is_heritage ? 'Listed' : 'Not listed',
          severity: report.is_heritage ? 'medium' : 'low',
        },
        {
          label: 'Analysis period',
          value: '2017–2024',
        },
      ]}
    />
  );
}
