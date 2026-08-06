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
  construction_change_detected: false,
  construction_change_note: 'Sentinel-2 timeout',
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

  it('renders the surface-change note instead of a false clear reading', () => {
    render(<ShadowDisplay data={KINCUMBER_SHADOW} />);
    expect(screen.getByText(/not assessed/)).toBeInTheDocument();
    expect(screen.getByText(/Sentinel-2 timeout/)).toBeInTheDocument();
    expect(screen.queryByText(/No bare-soil increase/)).toBeNull();
  });

  it('states the clear reading only when a real score came back', () => {
    // A score is REQUIRED for the negative. Clearing the note alone is not
    // enough — that is the state 292 stored reports are in, and it used to
    // render as a clear result.
    render(<ShadowDisplay data={{
      ...KINCUMBER_SHADOW, construction_change_note: null, construction_change_score: 0.031,
    }} />);
    expect(screen.getByText(/No bare-soil increase/)).toBeInTheDocument();
  });

  it('does NOT claim a clear reading from the legacy no-data score of exactly 0.0', () => {
    // The 292 pre-June stored reports: score exactly 0.0, no note, because the
    // no-data path returned a hard-coded zero before the note key existed. A
    // real delta is round(recent - baseline, 4) and landing on 0.0000 is a
    // ~1-in-10,000 coincidence; all 292 hold exactly 0.0 and none holds any
    // other value. Reporting "no change" for these asserted a negative about
    // neighbouring land from a check that never ran.
    render(<ShadowDisplay data={{
      ...KINCUMBER_SHADOW, construction_change_note: null, construction_change_score: 0.0,
    }} />);
    expect(screen.getByText(/not assessed/)).toBeInTheDocument();
    expect(screen.queryByText(/No bare-soil increase/)).toBeNull();
  });

  it('never attributes surface change to a named neighbouring lot', () => {
    // The measurement is one mean bare-soil index over a 400m x 400m box that
    // contains the subject's own lot and a few hundred others, and resolves no
    // direction. Prose naming an adjacent lot described something the
    // measurement does not contain.
    for (const score of [0.031, 0.31]) {
      const { container, unmount } = render(<ShadowDisplay data={{
        ...KINCUMBER_SHADOW,
        construction_change_note: null,
        construction_change_score: score,
        construction_change_detected: score > 0.12,
      }} />);
      const text = container.textContent ?? '';
      expect(text).not.toMatch(/adjacent lot/i);
      expect(text).not.toMatch(/next door/i);
      expect(text).not.toMatch(/to the north/i);
      unmount();
    }
  });

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
