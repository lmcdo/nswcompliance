/**
 * (3) LepControls hazard tiles: a map that did not answer prints "Not checked", never "No".
 * Before 2026-10-21 bushfireProne defaulted to false and a failed lookup printed "No".
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';

jest.mock('@/components/compliance/LandUseZoningCard', () => ({ LandUseZoningCard: () => null }));
jest.mock('@/components/compliance/ConstraintArithmeticCard', () => ({ ConstraintArithmeticCard: () => null }));
jest.mock('@/components/compliance/LocalProvisionsCard', () => ({ LocalProvisionsCard: () => null }));
jest.mock('@/components/compliance/HeritageProvisionsCard', () => ({ HeritageProvisionsCard: () => null }));
jest.mock('@/components/compliance/NotApplicableCard', () => ({ NotApplicableCard: () => null }));
jest.mock('@/components/compliance/ServicingTile', () => ({ ServicingTile: () => null }));

import { LepControls } from '@/components/compliance/LepControls';

const base = {
  maxFsr: null, maxHeight: null, minLotSize: null, zone: 'R2', zoneDescription: null, lga: 'Test',
  heritage: false, floodProne: false, basixClimate: null, basixWater: null,
} as any;

function tileValue(label: string): string {
  const name = screen.getByText(label);
  const tile = name.closest('div')!.parentElement as HTMLElement;
  return within(tile).getAllByText(/./).map((e) => e.textContent).pop() ?? '';
}

describe('LepControls hazard tiles', () => {
  it('prints "Not checked" for unknown bush fire, mine subsidence and contaminated land', () => {
    render(<LepControls planningLayers={[]} constraints={{
      ...base, bushfireProne: null, uncheckedHazards: ['bushfire', 'mine_subsidence', 'contaminated_land'],
    }} />);
    expect(tileValue('Bushfire Prone')).toBe('Not checked');
    expect(tileValue('Mine Subsidence')).toBe('Not checked');
    expect(tileValue('Contaminated Land')).toBe('Not checked');
  });

  it('prints "No" only when the maps answered', () => {
    render(<LepControls planningLayers={[]} constraints={{ ...base, bushfireProne: false, uncheckedHazards: [] }} />);
    expect(tileValue('Bushfire Prone')).toBe('No');
    expect(tileValue('Mine Subsidence')).toBe('No');
    expect(tileValue('Contaminated Land')).toBe('No');
  });
});
