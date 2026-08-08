/**
 * Satellite pass-through parity (PR-B) — the brief must render what its own
 * engines computed instead of discarding it at the contract layer.
 *
 * Covers: the flood screening-signal line, the Copernicus EMS wording
 * ("mapped extent" register — never "the property flooded"), and the full
 * shadow scenario table with the default-height / low-confidence caveat.
 * Shadow fixture values are from the recorded Kincumber run (2026-07-16).
 */

import fs from 'fs';
import path from 'path';
import { render, screen } from '@testing-library/react';
import { floodSignalLine, emsLine } from '@/app/reports/intelligence-brief/satellite-copy';
import { ShadowDisplay, type ShadowData } from '@/components/reports/ShadowDetailDisplay';

const PAGE_SRC = fs.readFileSync(
  path.join(__dirname, '..', '..', 'app', 'reports', 'intelligence-brief', 'page.tsx'),
  'utf8',
);

describe('flood card copy — screening signal line', () => {
  it('renders the signal as a screening output with provenance, not a bare verdict', () => {
    expect(floodSignalLine('moderate')).toBe(
      'Flood screening signal: moderate — computed from the sources below.',
    );
  });

  it('the page renders the signal line for satellite.flood', () => {
    expect(PAGE_SRC).toContain("key === 'flood_signal'");
    expect(PAGE_SRC).toContain('floodSignalLine(val)');
  });
});

describe('flood card copy — Copernicus EMS line (mapped-extent register)', () => {
  const activations = [{
    activation_id: 'EMSR567',
    event_name: 'NSW/QLD Floods Feb–Mar 2022 — La Niña (Copernicus EMSR567)',
    event_date: '2022-02-26',
    flood_type: 'observed',
  }];

  it('detected: states a mapped extent intersecting the location during the named event', () => {
    const line = emsLine(true, activations);
    expect(line).toBe(
      'Copernicus emergency mapping recorded flood extent intersecting this location during ' +
      'NSW/QLD Floods Feb–Mar 2022 — La Niña (Copernicus EMSR567) (2022-02-26).',
    );
    expect(line).toContain('mapping recorded flood extent intersecting this location');
  });

  it('never claims the property flooded', () => {
    expect(emsLine(true, activations)).not.toMatch(/property flooded/i);
    expect(emsLine(false)).not.toMatch(/property flooded/i);
    expect(emsLine(true, [])).not.toMatch(/property flooded/i);
  });

  it('not detected: states no mapped extent recorded at this location', () => {
    expect(emsLine(false)).toBe(
      'No Copernicus emergency-mapping flood extent recorded at this location.',
    );
  });

  it('detected without activation detail still states the mapped-extent fact', () => {
    expect(emsLine(true, [])).toBe(
      'Copernicus emergency mapping recorded flood extent intersecting this location.',
    );
  });

  it('falls back to the activation id when the event has no name', () => {
    expect(emsLine(true, [{ activation_id: 'EMSR567' }])).toContain('during EMSR567');
  });
});

// Recorded Kincumber shadow run (default 9 m height, run confidence low,
// Sentinel-2 change check timed out, 5 scenarios) — overlap_pct is the
// builder's fraction->percent conversion of the recorded fractions.
const KINCUMBER_SHADOW: ShadowData = {
  height_m: 9.0,
  height_source: 'default',
  adg_compliant: true,
  worst_case_scenario: 'jun21_3pm',
  confidence: 'low',
  scenarios: [
    { date_label: 'ADG worst case 9am Jun 21', time_label: '09:00', shadow_length_m: 19.0, overlap_pct: 9.5, overlaps_subject_lot: false },
    { date_label: 'ADG worst case noon Jun 21', time_label: '12:00', shadow_length_m: 13.8, overlap_pct: 6.3, overlaps_subject_lot: false },
    { date_label: 'ADG worst case 3pm Jun 21', time_label: '15:00', shadow_length_m: 19.7, overlap_pct: 11.2, overlaps_subject_lot: false },
    { date_label: 'Spring equinox noon', time_label: '12:00', shadow_length_m: 6.1, overlap_pct: 1.3, overlaps_subject_lot: false },
    { date_label: 'Summer solstice noon', time_label: '12:00', shadow_length_m: 1.6, overlap_pct: 0.1, overlaps_subject_lot: false },
  ],
};

describe('ShadowDisplay — full scenario table + confidence caveats', () => {
  it('renders all 5 scenario rows, not only the worst case', () => {
    render(<ShadowDisplay data={KINCUMBER_SHADOW} />);
    const table = screen.getByTestId('shadow-scenario-table');
    const rows = table.querySelectorAll('tbody tr');
    expect(rows).toHaveLength(5);
    expect(screen.getByText('Spring equinox noon')).toBeInTheDocument();
    expect(screen.getByText('Summer solstice noon')).toBeInTheDocument();
    expect(screen.getByText('19.7 m')).toBeInTheDocument();
    expect(screen.getByText('11.2%')).toBeInTheDocument();
  });

  it('keeps the worst-case summary line above the table', () => {
    render(<ShadowDisplay data={KINCUMBER_SHADOW} />);
    expect(screen.getByText(/Worst case \(/)).toBeInTheDocument();
  });

  it('carries the default-height caveat on the ADG line and surfaces run confidence', () => {
    render(<ShadowDisplay data={KINCUMBER_SHADOW} />);
    expect(
      screen.getByText(/computed at the standard two-storey height — confidence low/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Run confidence:/)).toBeInTheDocument();
  });

  // REMOVED 2026-08-07 (§4h): four tests pinned the Sentinel-2 surface-change
  // three-state wording — "renders the surface-change note instead of a false
  // clear reading", "states the clear reading only when a real score came
  // back", "does NOT claim a clear reading from the legacy no-data score of
  // exactly 0.0", and "never attributes surface change to a named neighbouring
  // lot". They were correct against the old doctrine and are deleted with the
  // feature, not weakened: the check returned a reading in 0 of 538 attempts
  // and cannot resolve a single lot at 20 m SWIR, so the whole section is gone
  // rather than reworded. Nothing renders the state they asserted.
  it('omits the caveat when the height came from a mapped LEP control', () => {
    render(<ShadowDisplay data={{ ...KINCUMBER_SHADOW, height_source: 'spatial_overlays', confidence: 'medium' }} />);
    expect(screen.queryByText(/standard two-storey height — confidence low/)).toBeNull();
  });
});

describe('page source — new satellite rows are wired', () => {
  it('flood composite rows exist for EMS, SES, gauge name, 100-yr and the S1 gap caveat', () => {
    expect(PAGE_SRC).toContain("key === 'ems_flood_detected'");
    expect(PAGE_SRC).toContain("key === 'ses_in_flood_planning_area'");
    expect(PAGE_SRC).toContain("key === 'bom_gauge_distance_km'");
    expect(PAGE_SRC).toContain("key === 'in_100yr_flood_zone'");
    expect(PAGE_SRC).toContain("key === 's1_gap_warning'");
  });

  it('bushfire rows exist for BAL cost (typical range) with the assessor directory link, 10/50 and consultant costs', () => {
    expect(PAGE_SRC).toContain("key === 'bal_formal_assessment_cost_range'");
    expect(PAGE_SRC).toContain('typical range for a formal BAL assessment, not a quote');
    expect(PAGE_SRC).toContain('Find a BAL assessor (NSW RFS directory)');
    expect(PAGE_SRC).toContain("key === 'clearing_10_50_exceptions'");
    expect(PAGE_SRC).toContain("key === 'estimated_consultant_costs'");
  });

  it('solar card renders best pitch/azimuth and the commercial-scale note', () => {
    expect(PAGE_SRC).toContain('best_pitch_deg');
    expect(PAGE_SRC).toContain('best_azimuth_deg');
    expect(PAGE_SRC).toContain('is_commercial_scale');
    expect(PAGE_SRC).toContain('Best roof segment');
  });
});

describe('ShadowDisplay — a scenario with no result must not read as a clear one', () => {
  const UNAVAILABLE_SCENARIO = {
    date_label: '21 Jun',
    time_label: '12:00',
    shadow_length_m: null,
    overlap_pct: null,
    overlaps_subject_lot: null,
    status: 'unavailable',
    error_note: 'the shadow could not be intersected with this lot\'s boundary — no overlap was measured',
  };

  it('says what was tried, why there is no answer, and that it is neither a pass nor a fail', () => {
    render(<ShadowDisplay data={{ ...KINCUMBER_SHADOW, scenarios: [UNAVAILABLE_SCENARIO] }} />);
    expect(screen.getByText(/Not assessed/)).toBeInTheDocument();
    // (1) why there is no answer — named in plain words, not internals
    expect(screen.getByText(/recorded lot boundary is incomplete/)).toBeInTheDocument();
    // (2) explicitly not a verdict in either direction
    expect(screen.getByText(/not a result/)).toBeInTheDocument();
    expect(screen.getByText(/neither a pass nor a fail/)).toBeInTheDocument();
    // (3) what the reader can do about it
    expect(screen.getByText(/ask the council/)).toBeInTheDocument();
  });

  it('does NOT render the operator-facing internals to the reader', () => {
    render(<ShadowDisplay data={{ ...KINCUMBER_SHADOW, scenarios: [UNAVAILABLE_SCENARIO] }} />);
    expect(screen.queryByText(/could not be intersected/)).toBeNull();
    expect(screen.queryByText(/no overlap was measured/)).toBeNull();
  });

  it('does not fall back to an em dash or a zero for the missing measurements', () => {
    const { container } = render(
      <ShadowDisplay data={{ ...KINCUMBER_SHADOW, scenarios: [UNAVAILABLE_SCENARIO] }} />
    );
    const row = container.querySelector('tbody tr');
    expect(row).not.toBeNull();
    // An empty cell reads as "fine" to someone skimming — that is the defect.
    expect(row!.textContent).not.toMatch(/0 m|0%|—\s*—/);
    expect(row!.className).toContain('amber');
  });

  it('a computed scenario is unaffected — the amber state must not leak', () => {
    const { container } = render(<ShadowDisplay data={{
      ...KINCUMBER_SHADOW,
      scenarios: [{ date_label: '21 Jun', time_label: '12:00', shadow_length_m: 14,
                    overlap_pct: 30, overlaps_subject_lot: true, status: 'computed' }],
    }} />);
    const row = container.querySelector('tbody tr');
    expect(row!.textContent).toContain('14 m');
    expect(row!.className).not.toContain('amber');
    expect(screen.queryByText(/Not assessed/)).toBeNull();
  });

  it('legacy rows with no status field still render as computed results', () => {
    const { container } = render(<ShadowDisplay data={{
      ...KINCUMBER_SHADOW,
      scenarios: [{ date_label: '21 Jun', time_label: '12:00', shadow_length_m: 14,
                    overlap_pct: 30, overlaps_subject_lot: true }],
    }} />);
    expect(container.querySelector('tbody tr')!.textContent).toContain('14 m');
    expect(screen.queryByText(/Not assessed/)).toBeNull();
  });
});
