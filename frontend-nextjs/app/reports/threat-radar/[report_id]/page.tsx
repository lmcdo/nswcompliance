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
    .from('property_reports')
    .select('address')
    .eq('id', params.report_id)
    .eq('product', 'threat-radar')
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Development Monitoring — ${address}`,
    description: `Nearby DA and CDC activity for ${address}. Development pressure, application types, and construction timelines.`,
    robots: { index: false },
  };
}

export default async function ThreatRadarReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('property_reports')
    .select('id, address, lat, lng, run_date, outputs, confidence, data_sources')
    .eq('id', params.report_id)
    .eq('product', 'threat-radar')
    .single();

  if (!row) notFound();

  const outputs = (row.outputs ?? {}) as Record<string, unknown>;
  const apps = Array.isArray(outputs.applications) ? outputs.applications : [];

  return (
    <SharedReportPage
      reportId={row.id}
      product="threat-radar"
      address={row.address}
      runDate={row.run_date}
      confidence={row.confidence}
      generatePath="/api/reports/threat-radar/generate"
      highlights={[
        {
          label: 'Nearby applications',
          value: `${apps.length} found`,
          severity: apps.length > 10 ? 'high' : apps.length > 3 ? 'medium' : 'low',
        },
        {
          label: 'Search radius',
          value: outputs.radius_m ? `${outputs.radius_m}m` : '200m',
        },
        {
          label: 'Council',
          value: (outputs.council_name as string) ?? 'N/A',
        },
        {
          label: 'Data sources',
          value: `${(row.data_sources ?? []).length} sources`,
        },
      ]}
    />
  );
}
