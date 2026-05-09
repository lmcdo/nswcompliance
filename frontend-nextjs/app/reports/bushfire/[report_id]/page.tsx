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
    .eq('product', 'bushfire')
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Bushfire Pre-Screen — ${address}`,
    description: `Bushfire prone land assessment for ${address}. BFPL category, BAL band, RFS referral requirements.`,
    robots: { index: false },
  };
}

export default async function BushfireReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('property_reports')
    .select('id, address, lat, lng, run_date, outputs, confidence, data_sources')
    .eq('id', params.report_id)
    .eq('product', 'bushfire')
    .single();

  if (!row) notFound();

  const outputs = (row.outputs ?? {}) as Record<string, unknown>;

  return (
    <SharedReportPage
      reportId={row.id}
      product="bushfire"
      address={row.address}
      runDate={row.run_date}
      confidence={row.confidence}
      generatePath="/api/reports/bushfire/generate"
      highlights={[
        {
          label: 'Bush Fire Prone Land',
          value: outputs.bfpl_category ? String(outputs.bfpl_category) : 'Not on BFPL',
          severity: outputs.bfpl_category ? 'high' : 'low',
        },
        {
          label: 'Estimated BAL band',
          value: (outputs.bal_estimate as string) ?? 'N/A',
          severity: outputs.bal_estimate && outputs.bal_estimate !== 'BAL-LOW' ? 'medium' : 'low',
        },
        {
          label: 'RFS referral required',
          value: outputs.rfs_referral_required ? 'Yes' : 'No',
          severity: outputs.rfs_referral_required ? 'high' : 'low',
        },
        {
          label: '10/50 clearing entitlement',
          value: outputs.clearing_entitlement_1050 ? 'Yes' : 'No',
        },
        {
          label: 'Data sources',
          value: `${(row.data_sources ?? []).length} independent sources`,
        },
      ]}
    />
  );
}
