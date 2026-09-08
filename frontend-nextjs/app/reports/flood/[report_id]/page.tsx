import { notFound } from 'next/navigation';
import type { Metadata } from 'next';
import { SharedReportPage } from '@/components/reports/SharedReportPage';
import { getAdminClient } from '@/lib/supabase/admin';
import {
  FLOOD_ZONE_NOT_ASSESSED_LABEL,
  floodZoneUnavailableMessage,
  readFloodZoneVerdict,
} from '@/lib/not-assessed';

export const dynamic = 'force-dynamic';

export async function generateMetadata(
  { params }: { params: { report_id: string } }
): Promise<Metadata> {
  const supabase = getAdminClient();
  const { data } = await supabase
    .from('property_reports')
    .select('address')
    .eq('id', params.report_id)
    .eq('product', 'flood')
    .single();

  const address = data?.address ?? 'Property';
  return {
    title: `Flood Screening Report — ${address}`,
    description: `Flood risk assessment for ${address}. Cross-referenced from government overlays, satellite imagery, river gauges, and council flood models.`,
    robots: { index: false }, // Don't index individual reports
  };
}

export default async function FloodReportPage(
  { params }: { params: { report_id: string } }
) {
  const supabase = getAdminClient();
  const { data: row } = await supabase
    .from('property_reports')
    .select('id, address, lat, lng, run_date, outputs, confidence, data_sources')
    .eq('id', params.report_id)
    .eq('product', 'flood')
    .single();

  if (!row) notFound();

  const outputs = (row.outputs ?? {}) as Record<string, unknown>;

  return (
    <SharedReportPage
      reportId={row.id}
      product="flood"
      address={row.address}
      runDate={row.run_date}
      confidence={row.confidence}
      generatePath="/api/reports/flood/generate"
      highlights={[
        // THREE states, read through a validator rather than a cast. A
        // truthiness ternary stood here and rendered every unanswered case as
        // 'No' at severity 'low' — the reassuring end of the scale, for a
        // question nobody had answered.
        ...(() => {
          const verdict = readFloodZoneVerdict(outputs.in_100yr_flood_zone);
          return [{
            label: '100-year flood zone',
            value: verdict == null
              ? FLOOD_ZONE_NOT_ASSESSED_LABEL
              : verdict ? 'Yes — in flood zone' : 'No',
            severity: (verdict == null ? 'medium' : verdict ? 'high' : 'low') as
              'high' | 'medium' | 'low',
            detail: verdict == null
              ? floodZoneUnavailableMessage(
                  Array.isArray(outputs.in_100yr_flood_zone_unconsulted)
                    ? (outputs.in_100yr_flood_zone_unconsulted as string[])
                    : null,
                )
              : undefined,
          }];
        })(),
        {
          label: 'EPI flood classification',
          value: (outputs.epi_flood_label as string) ?? 'Not classified',
          severity: outputs.epi_flood_class ? 'medium' : 'low',
        },
        {
          label: 'Ground elevation',
          value: outputs.ground_elevation_m_ahd != null
            ? `${Number(outputs.ground_elevation_m_ahd).toFixed(1)}m AHD`
            : 'Not available',
        },
        {
          label: 'SAR flood detected',
          value: outputs.sar_flood_detected ? 'Yes' : outputs.sar_flood_detected === false ? 'No' : 'No data',
          severity: outputs.sar_flood_detected ? 'high' : 'low',
        },
        {
          label: 'Data sources',
          value: `${(row.data_sources ?? []).length} independent sources`,
        },
      ]}
    />
  );
}
