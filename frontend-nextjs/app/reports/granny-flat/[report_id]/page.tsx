import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { SharedReportPage } from '@/components/reports/SharedReportPage';
import { getAdminClient } from '@/lib/supabase/admin';
import { resolveGrannyReviewState } from '@/lib/granny-flat-review-state';

export const dynamic = 'force-dynamic';

export async function generateMetadata(
  { params }: { params: { report_id: string } }
): Promise<Metadata> {
  const supabase = getAdminClient();
  const { data } = await supabase
    .from('property_reports')
    .select('address')
    .eq('id', params.report_id)
    .eq('product', 'granny-flat')
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Granny Flat Eligibility — ${address}`,
    description: `CDC pathway eligibility, setbacks, floor area, and rental yield analysis for ${address}.`,
    robots: { index: false },
  };
}

export default async function GrannyFlatReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('property_reports')
    .select('id, address, lat, lng, run_date, outputs, confidence, inputs')
    .eq('id', params.report_id)
    .eq('product', 'granny-flat')
    .single();

  if (!row) notFound();

  const outputs = (row.outputs ?? {}) as Record<string, unknown>;
  const inputs = (row.inputs ?? {}) as Record<string, unknown>;
  // Say what was checked, not how confident we are. The grade this replaces
  // called an unchecked lot "medium".
  const review = resolveGrannyReviewState(outputs, inputs);

  return (
    <SharedReportPage
      reportId={row.id}
      product="granny-flat"
      address={row.address}
      runDate={row.run_date}
      stateLabel={review.label}
      stateDetail={review.detail}
      generatePath="/api/reports/granny-flat/generate"
      highlights={[
        {
          label: 'SEPP eligibility',
          value: outputs.sepp_eligible ? 'Eligible' : 'Not eligible',
          severity: outputs.sepp_eligible ? 'low' : 'high',
        },
        {
          label: 'Approval pathway',
          value: (outputs.pathway as string) ?? 'N/A',
        },
        {
          label: 'Lot area',
          value: outputs.lot_area_m2 != null ? `${Number(outputs.lot_area_m2).toLocaleString()} m²` : 'N/A',
        },
        {
          label: 'Maximum GFA',
          value: outputs.max_gfa_m2 != null ? `${Number(outputs.max_gfa_m2).toFixed(0)} m²` : 'N/A',
        },
        {
          label: 'Heritage listed',
          value: outputs.is_heritage ? 'Yes' : 'No',
          severity: outputs.is_heritage ? 'medium' : 'low',
        },
      ]}
    />
  );
}
