/** CONSUMER CHECK: render each surface and assert the section is GONE and no hole remains. */
jest.mock('@react-pdf/renderer', () => ({
  Document: () => null, Page: () => null, View: () => null, Text: () => null, Image: () => null,
  StyleSheet: { create: (s: Record<string, unknown>) => s },
}));
jest.mock('@/lib/pdf/shared-components', () => ({
  PlotDetectFooter: () => null, AboutPage: () => null, ReferralLinks: () => null,
  DataCurrencyTable: () => null, QRBlock: () => null, PreparedBy: () => null,
}));
jest.mock('@/lib/pdf/map-overlay', () => ({ AerialWithOverlay: () => null }));

import { render, screen } from '@testing-library/react';
import { buildFindings, type ShadowReportData } from '@/lib/pdf/shadow-report';
import { ShadowDisplay } from '@/components/reports/ShadowDetailDisplay';
import { shadowConfig } from '@/components/reports/landing/data/shadow';

const SCENARIOS = ['jun21_9am','jun21_12pm','jun21_3pm','sep21_12pm','dec21_12pm'].map(k => ({
  scenario: k, label: k, date: '2026-06-21', time_local: '12:00',
  shadow_length_m: 14, shadow_overlap_fraction: 0.1, shadow_direction_deg: 180,
  overlaps_subject_lot: false, status: 'computed',
}));

it('PDF: no finding mentions the removed check, and findings are non-empty', () => {
  const f = buildFindings({
    address: 'x', run_date: '2026-08-07', lat: -33.8, lng: 151.2, zone: 'R2',
    height_m: 9, height_source: 'planning_portal', lep_name: 'LEP',
    scenarios: SCENARIOS, adg_compliant: true, worst_case_scenario: 'jun21_9am',
  } as unknown as ShadowReportData);
  expect(f.length).toBeGreaterThan(0);
  const all = JSON.stringify(f);
  for (const t of ['bare-soil','Sentinel','surface-change','Surface-change','adjacent','ground-surface','Ground-surface'])
    expect(all).not.toContain(t);
});

it('Brief/report page: card renders, no surface-change line, no trailing empty block', () => {
  const { container } = render(<ShadowDisplay data={{
    height_m: 9, adg_compliant: true, confidence: 'low',
    scenarios: [{ date_label: '21 Jun', time_label: '12:00', shadow_length_m: 14,
                  overlap_pct: 10, overlaps_subject_lot: false, status: 'computed' }],
  }} />);
  expect(screen.getByTestId('shadow-scenario-table')).toBeInTheDocument();
  expect(container.textContent).not.toMatch(/bare-soil|Sentinel|Surface-change|adjacent/i);
  const root = container.firstElementChild!;
  const last = root.lastElementChild!;
  expect(last.textContent!.trim().length).toBeGreaterThan(0); // no empty trailing div
});

it('landing page: sells nothing it cannot do, and the grid has no empty cell', () => {
  const blob = JSON.stringify(shadowConfig);
  for (const t of ['Surface-change','bare-soil','Sentinel','Ground-Surface'])
    expect(blob).not.toContain(t);
  expect(shadowConfig.features).toHaveLength(3);           // -> lg:grid-cols-3
  expect(shadowConfig.comparison.map(c => c.name)).not.toContain('Surface-change screening detail');
});
