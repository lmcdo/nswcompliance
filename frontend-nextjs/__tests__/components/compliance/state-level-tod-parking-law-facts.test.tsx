/**
 * The TOD parking card when the law's transport distances are not available.
 * The distances come from law_facts. If that request fails, "no qualifying public transport" is not known, so the page must say
 * "not checked" and must not print "Not applicable" (found by the cross-review of the area-check branch, 2026-11-08).
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
jest.mock('@/components/compliance/NotApplicableCard', () => ({
  NotApplicableCard: ({ title }: { title: string }) => <div data-testid="not-applicable">{title}</div>,
}));
jest.mock('@/components/tod/NearbyTransportCard', () => ({ NearbyTransportCard: () => null }));
jest.mock('@/components/ui/pdf-image-modal', () => ({ PdfImageModal: () => null }));

const fact = (value: number) => ({ value, unit: 'm', clause: 'c', pdfPage: 125, quote: 'q', lawVersionDate: '2026-10-23' });
let mockFacts: Record<string, unknown> | null = null;
jest.mock('@/hooks/useLawFacts', () => ({
  useLawFacts: () => ({ facts: mockFacts, loading: false, failed: mockFacts == null }),
}));

import { StateLevelControls } from '@/components/compliance/StateLevelControls';

const propertyData = {
  constraints: { zone: 'R2 Low Density Residential', applicableSepps: ['SEPP_HOUSING_2021'], lga: 'Test' },
};

const todNotApplicable = () => screen.queryAllByTestId('not-applicable').filter((e) => /Transit Oriented Development \(TOD\) Parking/.test(e.textContent ?? ''));

describe('TOD parking card and the law facts', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() => Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })) as unknown as typeof fetch;
  });

  it('says not checked, never Not applicable, when the law facts did not load', async () => {
    mockFacts = null;
    render(<StateLevelControls propertyData={propertyData} developmentType="dual_occupancy" />);
    expect(await screen.findByTestId('tod-parking-not-checked')).toBeInTheDocument();
    expect(todNotApplicable()).toHaveLength(0);
  });

  const located = { ...propertyData, location: { lat: -33.89, lng: 151.12 } };
  const transportAnswer = (ok: boolean, suggestions: unknown[] = []) => jest.fn((url: string) => String(url).includes('/api/tod/transport-autocomplete')
    ? Promise.resolve({ ok, status: ok ? 200 : 500, json: () => Promise.resolve({ suggestions }) })
    : Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })) as unknown as typeof fetch;

  it('says Not applicable only when the law facts loaded AND the transport lookup succeeded with nothing in range', async () => {
    mockFacts = { accessible_area_rail_distance: fact(800), accessible_area_bus_distance: fact(400) };
    global.fetch = transportAnswer(true, []);
    render(<StateLevelControls propertyData={located} developmentType="dual_occupancy" />);
    expect(await screen.findAllByTestId('not-applicable')).not.toHaveLength(0);
    expect(screen.queryByTestId('tod-parking-not-checked')).toBeNull();
    expect(todNotApplicable()).toHaveLength(1);
  });

  it('says not checked, never Not applicable, when the nearby-transport request fails', async () => {
    mockFacts = { accessible_area_rail_distance: fact(800), accessible_area_bus_distance: fact(400) };
    global.fetch = transportAnswer(false);
    render(<StateLevelControls propertyData={located} developmentType="dual_occupancy" />);
    expect(await screen.findByTestId('tod-parking-not-checked')).toBeInTheDocument();
    expect(todNotApplicable()).toHaveLength(0);
  });

  it('a bus stop inside the distance is shown as a possibility with the timetable test named as not checked, whatever its label says', async () => {
    mockFacts = { accessible_area_rail_distance: fact(800), accessible_area_bus_distance: fact(400), accessible_area_bus_min_per_hour: fact(1) };
    global.fetch = jest.fn((url: string) => String(url).includes('/api/tod/transport-autocomplete')
      ? Promise.resolve({ ok: true, json: () => Promise.resolve({ suggestions: [{ id: 'b1', name: 'Bus stop', type: 'bus', distance: 150, frequency: 'low' }] }) })
      : Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) })) as unknown as typeof fetch;
    const pd = { ...propertyData, location: { lat: -33.89, lng: 151.12 } };
    render(<StateLevelControls propertyData={pd} developmentType="dual_occupancy" />);
    expect(await screen.findByText(/the timetable was not checked/)).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/at least 1 bus per hour/);
    expect(document.body.textContent).not.toMatch(/frequent bus/i);
  });
});
