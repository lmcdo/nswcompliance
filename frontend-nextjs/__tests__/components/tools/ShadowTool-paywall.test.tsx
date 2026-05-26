/**
 * ShadowTool paywall behaviour.
 *
 * After a result with report_id:
 *   - ShadowLockedPreviewCard renders
 *   - Shows first 2 scenario rows as teasers (readable)
 *   - Shows remaining rows blurred
 *   - Shows blurred objection paragraph when overlap detected
 *   - WaitlistButton shown (no Stripe checkout)
 *
 * After payment success URL params: ShadowPaidDownloadCTA shown.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShadowTool } from '@/components/tools/ShadowTool';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => () => <div data-testid="shadow-map-mock" />,
}));

jest.mock('@/components/reports/AddressAutocomplete', () => ({
  AddressAutocomplete: ({ value, onChange, onSelect, className }: {
    value: string;
    onChange: (v: string) => void;
    onSelect: (v: string) => void;
    className?: string;
  }) => (
    <input
      data-testid="address-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={(e) => onSelect(e.target.value)}
      className={className}
    />
  ),
}));

jest.mock('@/components/reports/ToolCrossSell', () => ({
  ToolCrossSell: () => null,
}));

jest.mock('@/components/providers/PostHogProvider', () => ({
  posthog: { capture: jest.fn() },
}));

jest.mock('@/components/tools/OperationalTransparency', () => ({
  OperationalTransparency: () => null,
}));

jest.mock('@/components/reports/WaitlistButton', () => ({
  WaitlistButton: ({ interestType }: { interestType: string }) => (
    <button data-testid={`waitlist-btn-${interestType}`}>Join waitlist</button>
  ),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SHADOW_RESULT = {
  address: '5 Elm St Haberfield NSW 2045',
  lat: -33.87,
  lng: 151.09,
  run_date: '2026-04-30',
  outputs: {
    height_m: 9.5,
    height_source: 'planning_portal' as const,
    lep_name: 'Inner West LEP 2022',
    lot_polygon: null,
    north_proxy_polygon: null,
    scenarios: [
      { scenario: 'jun21_9am',  label: '21 Jun 9am',  date: '2026-06-21', time_local: '09:00', shadow_length_m: 18.2, shadow_overlap_fraction: 0.45, shadow_direction_deg: 340, overlaps_subject_lot: true,  shadow_on_lot: null, shadow_polygon: null },
      { scenario: 'jun21_12pm', label: '21 Jun 12pm', date: '2026-06-21', time_local: '12:00', shadow_length_m: 12.1, shadow_overlap_fraction: 0.30, shadow_direction_deg: 355, overlaps_subject_lot: true,  shadow_on_lot: null, shadow_polygon: null },
      { scenario: 'jun21_3pm',  label: '21 Jun 3pm',  date: '2026-06-21', time_local: '15:00', shadow_length_m: 17.8, shadow_overlap_fraction: 0.20, shadow_direction_deg: 10,  overlaps_subject_lot: true,  shadow_on_lot: null, shadow_polygon: null },
      { scenario: 'sep21_12pm', label: '21 Sep 12pm', date: '2026-09-21', time_local: '12:00', shadow_length_m: 8.4,  shadow_overlap_fraction: 0.05, shadow_direction_deg: 5,   overlaps_subject_lot: false, shadow_on_lot: null, shadow_polygon: null },
      { scenario: 'dec21_12pm', label: '21 Dec 12pm', date: '2026-12-21', time_local: '12:00', shadow_length_m: 5.2,  shadow_overlap_fraction: 0.00, shadow_direction_deg: 358, overlaps_subject_lot: false, shadow_on_lot: null, shadow_polygon: null },
    ],
    construction_change_score: 0.18,
    construction_change_detected: true,
    adg_compliant: false,
    worst_case_scenario: 'jun21_9am',
  },
  confidence: 'high',
  data_sources: ['NSW Planning Portal', 'Sentinel-2'],
  zone: 'R2',
  warnings: [],
  report_id: 'shadow-report-uuid-1234',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockCheckFetch(result: typeof SHADOW_RESULT) {
  (global.fetch as jest.Mock).mockResolvedValueOnce(
    new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  );
}

async function runShadowCheck(result = SHADOW_RESULT) {
  render(<ShadowTool />);
  mockCheckFetch(result);
  fireEvent.change(screen.getByTestId('address-input'), { target: { value: result.address } });
  fireEvent.click(screen.getByRole('button', { name: /analyse/i }));
  await waitFor(() => screen.getByText('Scenario breakdown'));
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: 'http://localhost/', search: '', pathname: '/reports/shadow' },
  });
  Object.defineProperty(window, 'history', {
    writable: true,
    value: { replaceState: jest.fn() },
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// ShadowLockedPreviewCard
// ---------------------------------------------------------------------------

describe('ShadowTool — ShadowLockedPreviewCard', () => {
  it('renders after result with report_id', async () => {
    await runShadowCheck();
    expect(screen.getByText('Scenario breakdown')).toBeInTheDocument();
    // WaitlistButton replaces Stripe checkout
    expect(screen.getByTestId('waitlist-btn-shadow')).toBeInTheDocument();
  });

  it('shows ADG concern in alarm headline for non-compliant result', async () => {
    await runShadowCheck();
    expect(screen.getByText(/ADG concern/i)).toBeInTheDocument();
  });

  it('shows first 2 scenario rows as readable teasers', async () => {
    await runShadowCheck();
    // First teaser: jun21_9am → 18m shadow (also appears in ShadowCard findings)
    const shadow18 = screen.getAllByText(/18m shadow/);
    expect(shadow18.length).toBeGreaterThanOrEqual(1);
    // Second teaser: jun21_12pm → 12m shadow
    const shadow12 = screen.getAllByText(/12m shadow/);
    expect(shadow12.length).toBeGreaterThanOrEqual(1);
  });

  it('shows objection paragraph section (blurred)', async () => {
    await runShadowCheck();
    // "Objection-ready paragraph" appears in both FreePaidComparison and LockedPreviewCard
    const objectionHeaders = screen.getAllByText(/Objection-ready paragraph/i);
    expect(objectionHeaders.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Shadow modelling conducted/i)).toBeInTheDocument();
  });

  it('shows worst-case overlap section', async () => {
    await runShadowCheck();
    expect(screen.getByText(/Shadow overlap — worst case/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PaidDownloadCTA
// ---------------------------------------------------------------------------

describe('ShadowTool — ShadowPaidDownloadCTA', () => {
  it('shows PaidDownloadCTA when ?payment=success&report_id=X in URL', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        search: '?payment=success&report_id=paid-shadow-uuid',
        pathname: '/reports/shadow',
      },
    });
    render(<ShadowTool />);
    await waitFor(() => {
      expect(screen.getByText('Payment confirmed — your report is ready.')).toBeInTheDocument();
    });
  });

  it('download button calls /api/reports/shadow/generate', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        search: '?payment=success&report_id=paid-shadow-uuid-123',
        pathname: '/reports/shadow',
      },
    });

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(new Uint8Array([37, 80, 68, 70]), {
        status: 200, headers: { 'Content-Type': 'application/pdf' },
      })
    );

    global.URL.createObjectURL = jest.fn().mockReturnValue('blob:mock');
    global.URL.revokeObjectURL = jest.fn();

    render(<ShadowTool />);
    await waitFor(() => screen.getByText('Download PDF report →'));
    fireEvent.click(screen.getByText('Download PDF report →'));

    await waitFor(() => {
      const generateCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
        String(url).includes('/api/reports/shadow/generate')
      );
      expect(generateCall).toBeDefined();
      expect(JSON.parse(generateCall[1].body).report_id).toBe('paid-shadow-uuid-123');
    });
  });
});
