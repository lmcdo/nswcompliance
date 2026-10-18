import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('@/hooks/useCdcComplianceCalculator', () => ({ useCdcComplianceCalculator: () => ({}) }));
jest.mock('@/hooks/useCdcEligibility', () => ({ useCdcEligibility: () => ({ data: null, isLoading: false }) }));
jest.mock('@/components/cdc/CdcDevelopmentForm', () => ({ CdcDevelopmentForm: () => null }));
jest.mock('@/components/cdc/CdcComplianceResults', () => ({ CdcComplianceResults: () => null }));

import { CdcComplianceCalculator } from '@/components/cdc/CdcComplianceCalculator';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';

const sf = {
  status: 'measured' as const, unnamedRoadEdge_m: 0,
  roads: [{ road: 'BERRIGAN ST', frontage_m: 13.34, minFrontHalf_m: 13, maxAll_m: 22, depth_m: 40 }],
};
const lot = { area: 600, frontage: 22.4, depth: 30, confidence: 1, lotType: 'rectangular' as const };

describe('CdcComplianceCalculator street frontage', () => {
  it('measured', () => {
    render(<CdcComplianceCalculator address="a" initialCollapsed={false} lotDimensions={lot} streetFrontage={sf} />);
    expect(screen.getByTestId('cdc-street-frontage').textContent).toContain('13.3 m along Berrigan St');
    expect(screen.getByText('Lot width (shorter side)')).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/Frontage\s*22\.4/i);
  });
  it('null', () => {
    render(<CdcComplianceCalculator address="a" initialCollapsed={false} lotDimensions={lot} streetFrontage={null} />);
    expect(screen.getByTestId('cdc-street-frontage').textContent).toContain('not measured');
  });
});

describe('PropertyDetailsComprehensive street frontage', () => {
  const dims = { area: 600, frontage: 22.4, depth: 30, confidence: 1 };
  it('measured', () => {
    render(<PropertyDetailsComprehensive propertyData={{ lotDimensions: dims, cornerLot: { isCornerLot: false, adjacentRoads: [], roadCount: 1, confidence: 1, streetFrontage: sf } }} />);
    expect(screen.getByTestId('street-frontage-row').textContent).toContain('13.3 m along Berrigan St');
    expect(screen.getByText('Lot width (shorter side)')).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/Frontage:?\s*22\.4/i);
  });
  it('null', () => {
    render(<PropertyDetailsComprehensive propertyData={{ lotDimensions: dims }} />);
    expect(screen.getByTestId('street-frontage-row').textContent).toContain('not measured');
  });
});
