/**
 * Owner ruling 2026-11-16: the LEP map rows (zone, height, floor space ratio, lot size) come from map
 * layers and name no clause, so they carry no "Citation not yet checked" mark and no hard-coded
 * "LEP Clause 4.x" text (the same clause number was printed for every council). A clause that IS
 * cited (the zone card's Legislative Clause) keeps the mark. The flood tile never turns an unknown
 * (no flood planning map for the LEP) into "No".
 * prior-art-checked: extends lep-controls-hazard-not-checked.test.tsx (same mocks and tile helper);
 * citation-badge-inventory.test.ts still guards every other surface.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';

jest.mock('@/components/compliance/ConstraintArithmeticCard', () => ({ ConstraintArithmeticCard: () => null }));
jest.mock('@/components/compliance/LocalProvisionsCard', () => ({ LocalProvisionsCard: () => null }));
jest.mock('@/components/compliance/HeritageProvisionsCard', () => ({ HeritageProvisionsCard: () => null }));
jest.mock('@/components/compliance/NotApplicableCard', () => ({ NotApplicableCard: () => null }));
jest.mock('@/components/compliance/ServicingTile', () => ({ ServicingTile: () => null }));

import { LepControls } from '@/components/compliance/LepControls';
import { LandUseZoningCard } from '@/components/compliance/LandUseZoningCard';

const base = {
  maxFsr: 0.5, maxHeight: 8.5, minLotSize: 550, zone: 'R2', zoneDescription: null, lga: 'Penrith',
  heritage: false, floodProne: false, bushfireProne: false, uncheckedHazards: [], notChecked: [],
  basixClimate: null, basixWater: null,
} as any;
const layers = [{ layerName: 'Land Zoning Map', results: [{ 'EPI Name': 'Penrith Local Environmental Plan 2010' }] }] as any;

function tileValue(label: string): string {
  const tile = screen.getByText(label).closest('div')!.parentElement as HTMLElement;
  return within(tile).getAllByText(/./).map((e) => e.textContent).pop() ?? '';
}

describe('LEP map rows', () => {
  it('say which map the figure came from, with no clause number and no unchecked mark', () => {
    render(<LepControls planningLayers={layers} constraints={base} lotArea={500} />);
    expect(screen.getByText(/Penrith Local Environmental Plan 2010 — Height of Buildings Map/)).toBeInTheDocument();
    expect(screen.getByText(/Penrith Local Environmental Plan 2010 — Floor Space Ratio Map/)).toBeInTheDocument();
    expect(screen.getByText(/Penrith Local Environmental Plan 2010 — Lot Size Map/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/LEP Clause \d/);
    expect(document.body.textContent).not.toMatch(/Citation not yet checked/);
  });
});

describe('flood tile', () => {
  it('prints "No flood map found" when the portal holds no flood planning map (unknown is not No)', () => {
    render(<LepControls planningLayers={layers} constraints={{ ...base, floodProne: null, floodMapNote: 'no map for this LEP' }} />);
    expect(tileValue('Flood Mapping')).toBe('No flood map found');
  });
  it('prints "No" only when the council map says the lot is clear', () => {
    render(<LepControls planningLayers={layers} constraints={{ ...base, floodProne: false }} />);
    expect(tileValue('Flood Mapping')).toBe('No');
  });
  it('prints the council flood classification when the lot is on it', () => {
    render(<LepControls planningLayers={layers} constraints={{ ...base, floodProne: null, dcpFloodMap: { inFloodArea: true, classification: 'PMF, 500AEP' } }} />);
    expect(tileValue('Flood Mapping')).toBe('PMF, 500AEP');
  });
});

describe('zone card badge', () => {
  it('names the instrument without the unchecked mark when no clause is cited', () => {
    render(<LandUseZoningCard zone="R2" epiName="Penrith Local Environmental Plan 2010" />);
    expect(document.body.textContent).toMatch(/Penrith Local Environmental Plan 2010/);
    expect(document.body.textContent).not.toMatch(/Citation not yet checked/);
  });
  it('keeps the unchecked mark when a clause is cited', () => {
    render(<LandUseZoningCard zone="R2" epiName="Penrith Local Environmental Plan 2010" legislativeClause="Clause 2.3" />);
    expect(document.body.textContent).toMatch(/Citation not yet checked/);
  });
});
