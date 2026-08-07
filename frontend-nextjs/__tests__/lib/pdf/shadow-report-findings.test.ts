/**
 * buildFindings — unavailable scenarios must never be silently absorbed into
 * an all-clear aggregate (Sol pre-push round, 2026-08-07).
 *
 * overlapCount counts only computed overlaps, so with one scenario
 * unavailable the pre-fix wording claimed "no significant shadow impact ...
 * across any test scenario" — five results from four. These tests FAIL on the
 * pre-fix code.
 */

// @react-pdf/renderer ships ESM Jest cannot parse; every consumer test mocks
// it. buildFindings itself is pure — only the module's render exports touch
// the renderer. shadow-surface-change stays real: buildFindings branches on it.
jest.mock('@react-pdf/renderer', () => ({
  Document: () => null,
  Page: () => null,
  View: () => null,
  Text: () => null,
  Image: () => null,
  StyleSheet: { create: (styles: Record<string, unknown>) => styles },
}));
jest.mock('@/lib/pdf/shared-components', () => ({
  PlotDetectFooter: () => null,
  AboutPage: () => null,
  ReferralLinks: () => null,
  DataCurrencyTable: () => null,
  QRBlock: () => null,
  PreparedBy: () => null,
}));
jest.mock('@/lib/pdf/imagery-currency', () => ({ s2ImageryCurrency: jest.fn() }));
jest.mock('@/lib/pdf/map-overlay', () => ({ AerialWithOverlay: () => null }));

import { buildFindings, type ShadowReportData, type ShadowScenario } from '@/lib/pdf/shadow-report';

function scenario(key: string, overrides: Partial<ShadowScenario> = {}): ShadowScenario {
  return {
    scenario: key,
    label: key,
    date: '2026-06-21',
    time_local: '12:00',
    shadow_length_m: 14,
    shadow_overlap_fraction: 0,
    shadow_direction_deg: 180,
    overlaps_subject_lot: false,
    status: 'computed',
    ...overrides,
  };
}

const KEYS = ['jun21_9am', 'jun21_12pm', 'jun21_3pm', 'sep21_12pm', 'dec21_12pm'];

function reportData(scenarios: ShadowScenario[]): ShadowReportData {
  return {
    address: '1 Test St, Kincumber NSW',
    run_date: '2026-08-07',
    lat: -33.47,
    lng: 151.39,
    zone: 'R2',
    height_m: 9,
    height_source: 'planning_portal',
    lep_name: 'Central Coast LEP 2022',
    scenarios,
    construction_change_score: null,
    construction_change_detected: false,
    construction_change_note: 'Sentinel-2 timeout',
    adg_compliant: true,
    worst_case_scenario: 'jun21_9am',
  } as ShadowReportData;
}

describe('buildFindings — unavailable scenarios are disclosed, not absorbed', () => {
  it('with one unavailable scenario, the ADG finding is scoped to the computed count and goes amber', () => {
    const scenarios = KEYS.map((k, i) =>
      i === 0
        ? scenario(k, {
            status: 'unavailable',
            error_note: 'shadow reach could not be validated against the physical ceiling',
            shadow_length_m: null,
            shadow_overlap_fraction: null,
            overlaps_subject_lot: null,
          })
        : scenario(k)
    );
    const findings = buildFindings(reportData(scenarios));
    const adg = findings.find(f => f.label === 'ADG Part 3F solar access test');
    expect(adg).toBeDefined();
    expect(adg!.value).toContain('4 computed scenarios');
    expect(adg!.detail).toContain('could not be assessed');
    // The categorical five-scenario claim must be gone:
    expect(adg!.detail).not.toContain('across any test scenario');
    expect(adg!.severity).toBe('amber');
  });

  it('with all 5 computed and clear, the original all-scenario claim stands and stays green', () => {
    const findings = buildFindings(reportData(KEYS.map(k => scenario(k))));
    const adg = findings.find(f => f.label === 'ADG Part 3F solar access test');
    expect(adg).toBeDefined();
    expect(adg!.detail).toContain('across any test scenario');
    expect(adg!.severity).toBe('green');
  });

  it('legacy stored rows without a status field count as computed', () => {
    // Pre-fix cached rows predate the status key; treating absence as
    // unavailable would wrongly downgrade every stored report.
    const scenarios = KEYS.map(k => {
      const s = scenario(k);
      delete (s as Partial<ShadowScenario>).status;
      return s;
    });
    const findings = buildFindings(reportData(scenarios));
    const adg = findings.find(f => f.label === 'ADG Part 3F solar access test');
    expect(adg!.severity).toBe('green');
    expect(adg!.detail).toContain('across any test scenario');
  });

  it('the shadow-overlap count denominator excludes unavailable scenarios', () => {
    const scenarios = KEYS.map((k, i) =>
      i === 4
        ? scenario(k, {
            status: 'unavailable',
            error_note: 'no shadow output',
            shadow_length_m: null,
            shadow_overlap_fraction: null,
            overlaps_subject_lot: null,
          })
        : scenario(k, i === 1 ? { overlaps_subject_lot: true, shadow_overlap_fraction: 0.3 } : {})
    );
    const findings = buildFindings(reportData(scenarios));
    const adg = findings.find(f => f.label === 'ADG Part 3F solar access test');
    expect(adg!.value).toContain('1 of 4 computed scenarios');
    expect(adg!.value).not.toContain('of 5');
  });
});
