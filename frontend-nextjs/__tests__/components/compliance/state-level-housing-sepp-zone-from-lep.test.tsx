/**
 * The Housing SEPP reported by the Planning Portal is never dropped on a zone list.
 * Before 2026-10-26 a typed RESIDENTIAL list (R1-R5, RU5) dropped it for MU1 and E1, zones that allow housing.
 */
import React from 'react';
import { render, waitFor } from '@testing-library/react';

for (const c of ['StructuredSeppRequirements', 'LandUseZoningCard', 'MinimumLotSizeCard', 'ADGSummaryCard',
  'HousingSEPPEligibilityCard', 'PatternBookEligibilityCard', 'ExemptComplyingProvisions', 'PathwaySummaryCard', 'NotApplicableCard']) {
  jest.doMock(`@/components/compliance/${c}`, () => ({ [c]: () => null }));
}
jest.mock('@/components/tod/NearbyTransportCard', () => ({ NearbyTransportCard: () => null }));
jest.mock('@/components/ui/pdf-image-modal', () => ({ PdfImageModal: () => null }));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { StateLevelControls } = require('@/components/compliance/StateLevelControls');

function run(zone: string, lep: unknown) {
  const seppBodies: string[] = [];
  global.fetch = jest.fn((url: string, init?: { body?: string }) => {
    if (String(url).includes('/api/lep/permissibility')) return Promise.resolve({ ok: true, json: () => Promise.resolve(lep) });
    if (String(url).includes('/api/sepp/structured-requirements')) seppBodies.push(String(init?.body));
    return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
  }) as unknown as typeof fetch;
  render(<StateLevelControls propertyData={{ constraints: { zone, lga: 'Test', applicableSepps: ['SEPP_HOUSING_2021'] } }} developmentType="dual_occupancy" />);
  return seppBodies;
}

afterEach(() => jest.resetAllMocks());

it('keeps the Housing SEPP for MU1 when the LEP table is not checked', async () => {
  const bodies = run('MU1 Mixed Use', { covered: false, entries: [] });
  await waitFor(() => expect(bodies.some((b) => b.includes('housing_2021'))).toBe(true));
});

it('keeps it even when the LEP table prohibits every dwelling type (the Portal reported it)', async () => {
  const bodies = run('R2 Low Density Residential', { covered: true, entries: [
    { development_type: 'dwelling_houses', permissibility: 'prohibited' },
  ] });
  await waitFor(() => expect(bodies.some((b) => b.includes('housing_2021'))).toBe(true));
});
