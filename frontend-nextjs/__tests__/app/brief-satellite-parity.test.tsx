/**
 * Satellite pass-through parity (PR-B) — the brief must render what its own
 * engines computed instead of discarding it at the contract layer.
 *
 * Covers: the flood screening-signal line and the Copernicus EMS wording
 * ("mapped extent" register — never "the property flooded").
 */

import fs from 'fs';
import path from 'path';
import { render, screen } from '@testing-library/react';
import { floodSignalLine, emsLine } from '@/app/reports/intelligence-brief/satellite-copy';

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

describe('page source — shadow section removed (2026-10-22)', () => {
  it('the brief page no longer renders the shadow section or promises shadow analysis', () => {
    expect(PAGE_SRC).not.toContain('ShadowDisplay');
    expect(PAGE_SRC).not.toContain('ShadowDetailDisplay');
    expect(PAGE_SRC).not.toMatch(/shadow analysis/i);
    expect(PAGE_SRC).not.toMatch(/\bADG\b/);
  });
});
