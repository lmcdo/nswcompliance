/**
 * A failed Housing SEPP requirements request is "Not checked", never "no requirements".
 * Before 2026-10-26 a non-OK response or a thrown fetch left the list empty and the card said
 * "No Housing SEPP structured requirements for this development type".
 */
import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('@/components/compliance/StructuredSeppRequirements', () => ({ StructuredSeppRequirements: () => null }));
jest.mock('@/components/compliance/LandUseZoningCard', () => ({ LandUseZoningCard: () => null }));
jest.mock('@/components/compliance/MinimumLotSizeCard', () => ({ MinimumLotSizeCard: () => null }));
jest.mock('@/components/compliance/ADGSummaryCard', () => ({ ADGSummaryCard: () => null }));
jest.mock('@/components/compliance/HousingSEPPEligibilityCard', () => ({ HousingSEPPEligibilityCard: () => null }));
jest.mock('@/components/compliance/PatternBookEligibilityCard', () => ({ PatternBookEligibilityCard: () => null }));
jest.mock('@/components/compliance/ExemptComplyingProvisions', () => ({ ExemptComplyingProvisions: () => null }));
jest.mock('@/components/compliance/PathwaySummaryCard', () => ({ PathwaySummaryCard: () => null }));
jest.mock('@/components/compliance/NotApplicableCard', () => ({ NotApplicableCard: () => null }));
jest.mock('@/components/tod/NearbyTransportCard', () => ({ NearbyTransportCard: () => null }));
jest.mock('@/components/ui/pdf-image-modal', () => ({ PdfImageModal: () => null }));

import { StateLevelControls } from '@/components/compliance/StateLevelControls';

const propertyData = {
  constraints: { zone: 'R2 Low Density Residential', applicableSepps: ['SEPP_HOUSING_2021'], lga: 'Test' },
};

function mockFetch(seppResponse: () => Promise<unknown>) {
  global.fetch = jest.fn((url: string) =>
    String(url).includes('/api/sepp/structured-requirements')
      ? seppResponse()
      : Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }),
  ) as unknown as typeof fetch;
}

describe('StateLevelControls Housing SEPP requirements', () => {
  afterEach(() => jest.resetAllMocks());

  it('says Not checked when the request returns an error status', async () => {
    mockFetch(() => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) }));
    render(<StateLevelControls propertyData={propertyData} developmentType="dual_occupancy" />);
    expect(await screen.findByText(/Housing SEPP requirements not checked/i)).toBeInTheDocument();
    expect(screen.queryByText(/No Housing SEPP structured requirements/i)).toBeNull();
  });

  it('says Not checked when the request throws', async () => {
    mockFetch(() => Promise.reject(new Error('network down')));
    render(<StateLevelControls propertyData={propertyData} developmentType="dual_occupancy" />);
    expect(await screen.findByText(/Housing SEPP requirements not checked/i)).toBeInTheDocument();
  });

  it('still says none when the request answered with no requirements', async () => {
    mockFetch(() => Promise.resolve({
      ok: true, json: () => Promise.resolve({ success: true, data: { hasStructuredRequirements: false, requirements: [] } }),
    }));
    render(<StateLevelControls propertyData={propertyData} developmentType="dual_occupancy" />);
    expect(await screen.findByText(/No Housing SEPP structured requirements/i)).toBeInTheDocument();
  });
});
