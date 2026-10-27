/**
 * The ADG card's zone warning comes from the LEP land use table, not a typed zone list.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('@/components/ui/pdf-image-modal', () => ({ PdfImageModal: () => null }));
import { ADGSummaryCard } from '@/components/compliance/ADGSummaryCard';

const summary = {
  success: true,
  data: { documentInfo: { title: "ADG", version: "2015", authority: "NSW" }, keyMetrics: [], totalCriteria: 0, appliesTo: [] },
};

function mockFetch(lep: unknown) {
  global.fetch = jest.fn((url: string) => Promise.resolve(
    String(url).includes('/api/lep/permissibility')
      ? { ok: true, json: () => Promise.resolve(lep) }
      : { ok: true, json: () => Promise.resolve(summary) },
  )) as unknown as typeof fetch;
}

afterEach(() => jest.resetAllMocks());

it('warns when the LEP table lists residential flat buildings as prohibited (R4 not on any typed list)', async () => {
  mockFetch({ covered: true, entries: [{ development_type: 'residential_flat_buildings', permissibility: 'prohibited' }] });
  render(<ADGSummaryCard developmentType="residential_flat_building" zoneCode="R4" lga="Test" />);
  expect(await screen.findByText(/lists residential flat buildings as prohibited/i)).toBeInTheDocument();
});

it('does not warn when the LEP table permits them (R2 is on the typed list)', async () => {
  mockFetch({ covered: true, entries: [{ development_type: 'residential_flat_buildings', permissibility: 'permitted' }] });
  render(<ADGSummaryCard developmentType="residential_flat_building" zoneCode="R2" lga="Test" />);
  expect(await screen.findByText(/ADG/)).toBeInTheDocument();
  expect(screen.queryByText(/prohibit/i)).toBeNull();
});

it('says not checked when the zone is not covered', async () => {
  mockFetch({ covered: false, entries: [] });
  render(<ADGSummaryCard developmentType="residential_flat_building" zoneCode="R2" lga="Test" />);
  expect(await screen.findByText(/not checked against the LEP land use table/i)).toBeInTheDocument();
});
