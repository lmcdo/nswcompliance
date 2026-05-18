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
    .eq('product', 'shadow')
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Shadow Analysis — ${address}`,
    description: `Shadow impact assessment for ${address}. ADG compliance, seasonal diagrams, solar access analysis.`,
    robots: { index: false },
  };
}

export default async function ShadowReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('property_reports')
    .select('id, address, lat, lng, run_date, outputs, confidence, data_sources')
    .eq('id', params.report_id)
    .eq('product', 'shadow')
    .single();

  if (!row) notFound();

  const outputs = (row.outputs ?? {}) as Record<string, unknown>;

  return (
    <SharedReportPage
      reportId={row.id}
      product="shadow"
      address={row.address}
      runDate={row.run_date}
      confidence={row.confidence}
      generatePath="/api/reports/shadow/generate"
      highlights={[
        {
          label: 'ADG solar access test',
          value: outputs.adg_compliant ? 'Meets test' : outputs.adg_compliant === false ? 'Concern' : 'N/A',
          severity: outputs.adg_compliant === false ? 'high' : 'low',
        },
        {
          label: 'Maximum shadow coverage',
          value: outputs.max_shadow_pct != null ? `${Number(outputs.max_shadow_pct).toFixed(0)}%` : 'N/A',
          severity: Number(outputs.max_shadow_pct ?? 0) > 50 ? 'high' : Number(outputs.max_shadow_pct ?? 0) > 25 ? 'medium' : 'low',
        },
        {
          label: 'Max building height (adjacent)',
          value: outputs.max_height_m != null ? `${Number(outputs.max_height_m).toFixed(1)}m` : 'N/A',
        },
        {
          label: 'Scenarios tested',
          value: outputs.scenarios_count != null ? `${outputs.scenarios_count} ADG scenarios` : '5 ADG scenarios',
        },
      ]}
    />
  );
}
