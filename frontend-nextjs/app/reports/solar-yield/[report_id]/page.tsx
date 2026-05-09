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
    .eq('product', 'solar')
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Solar Yield Report — ${address}`,
    description: `Rooftop solar potential assessment for ${address}. System sizing, annual kWh, payback period.`,
    robots: { index: false },
  };
}

export default async function SolarYieldReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('property_reports')
    .select('id, address, lat, lng, run_date, outputs, confidence, data_sources')
    .eq('id', params.report_id)
    .eq('product', 'solar')
    .single();

  if (!row) notFound();

  const outputs = (row.outputs ?? {}) as Record<string, unknown>;

  return (
    <SharedReportPage
      reportId={row.id}
      product="solar-yield"
      address={row.address}
      runDate={row.run_date}
      confidence={row.confidence}
      generatePath="/api/reports/solar-yield/generate"
      highlights={[
        {
          label: 'Suitability grade',
          value: (outputs.grade as string) ?? 'N/A',
          severity: outputs.grade === 'A' || outputs.grade === 'B' ? 'low' : outputs.grade === 'C' ? 'medium' : 'high',
        },
        {
          label: 'Annual generation',
          value: outputs.annual_kwh != null ? `${Number(outputs.annual_kwh).toLocaleString()} kWh` : 'N/A',
        },
        {
          label: 'Best orientation',
          value: (outputs.best_orientation as string) ?? 'N/A',
        },
        {
          label: 'Heritage listed',
          value: outputs.is_heritage ? 'Yes — DA may be required' : 'No',
          severity: outputs.is_heritage ? 'medium' : 'low',
        },
      ]}
    />
  );
}
