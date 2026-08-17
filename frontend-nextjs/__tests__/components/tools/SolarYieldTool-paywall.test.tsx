/**
 * SolarYieldTool paywall behaviour.
 *
 * After a result with coverage_available=true:
 *   - SolarLockedPreviewCard renders with blurred financial values
 *   - WaitlistButton shown (no Stripe checkout)
 *
 * After payment success URL params:
 *   - PaidDownloadCTA renders instead of SolarLockedPreviewCard
 *   - Download button calls generate route
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SolarYieldTool } from '@/components/tools/SolarYieldTool';

// jsdom 26 (jest-environment-jsdom 30) makes window.location non-configurable,
// so Object.defineProperty(window, 'location', ...) throws. Navigate with the
// real History API instead, which genuinely updates location.pathname/.search.
// The reference is captured HERE, at module load, because beforeEach replaces
// window.history with a mock - a later lookup would find the mock and the URL
// would silently never change.
const realReplaceState = window.history.replaceState.bind(window.history);
const setTestUrl = (url: string) => realReplaceState({}, '', url);

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('next/dynamic', () => ({
  __esModule: true,
  default: () => () => <div data-testid="aerial-tile-mock" />,
}));

jest.mock('@/components/reports/AddressAutocomplete', () => ({
  AddressAutocomplete: ({ value, onChange, onSelect, placeholder, className }: {
    value: string;
    onChange: (v: string) => void;
    onSelect: (v: string) => void;
    placeholder?: string;
    className?: string;
  }) => (
    <input
      data-testid="address-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onBlur={(e) => onSelect(e.target.value)}
      placeholder={placeholder}
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

const SOLAR_OUTPUTS = {
  max_panels: 20,
  max_panel_area_m2: 32,
  annual_kwh_estimate: 8200,
  sunshine_hours_per_year: 1680,
  best_pitch_deg: 22,
  best_azimuth_deg: 5,
  roof_area_m2: 80,
  is_heritage: false,
  is_commercial_scale: false,
  imagery_date: '2024-09',
  coverage_available: true,
};

const SOLAR_RESULT = {
  product: 'solar-yield',
  address: '5 Commercial Rd Haberfield NSW 2045',
  lat: -33.87,
  lng: 151.09,
  lot_polygon: null,
  run_date: '2026-04-30',
  outputs: SOLAR_OUTPUTS,
  confidence: 'high',
  data_sources: ['Google Solar API', 'BOM irradiance'],
  report_id: 'sol-report-uuid-1234',
};

const NO_COVERAGE_RESULT = {
  ...SOLAR_RESULT,
  outputs: { ...SOLAR_OUTPUTS, coverage_available: false },
  report_id: undefined,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockRunFetch(data: unknown, ok = true) {
  (global.fetch as jest.Mock).mockResolvedValueOnce(
    new Response(JSON.stringify(ok ? { data } : { error: 'Failed' }), {
      status: ok ? 200 : 500,
      headers: { 'Content-Type': 'application/json' },
    })
  );
}

async function runReport(data = SOLAR_RESULT) {
  render(<SolarYieldTool />);
  mockRunFetch(data);
  fireEvent.change(screen.getByTestId('address-input'), { target: { value: data.address } });
  fireEvent.click(screen.getByRole('button', { name: /run report/i }));
  // Wait for result to render
  await waitFor(() => {
    const hasResult = screen.queryByText(/Your solar financials/i) || screen.queryByText(/not assessable/i) || screen.queryByText(/Building data not available/i);
    if (!hasResult) throw new Error('Result not yet rendered');
  });
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  setTestUrl('/reports/solar-yield');
  Object.defineProperty(window, 'history', {
    writable: true,
    value: { replaceState: jest.fn() },
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// LockedPreviewCard
// ---------------------------------------------------------------------------

describe('SolarYieldTool — LockedPreviewCard after result', () => {
  it('shows SolarLockedPreviewCard when coverage_available and report_id present', async () => {
    await runReport();
    // "Your solar financials" is the unique heading in the LockedPreviewCard
    expect(screen.getByText('Your solar financials')).toBeInTheDocument();
    // WaitlistButton replaces Stripe checkout
    expect(screen.getByTestId('waitlist-btn-solar-yield')).toBeInTheDocument();
  });

  it('shows all blurred preview rows', async () => {
    await runReport();
    // Some labels appear in both FreePaidComparison and LockedPreviewCard, use getAllByText
    expect(screen.getAllByText(/Payback period/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Installed cost estimate/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Feed-in/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Full PDF report/).length).toBeGreaterThanOrEqual(1);
  });

  it('blurred values contain real computed $ amounts, on DELIVERED energy', async () => {
    await runReport();
    // THIS TEST USED TO ENCODE THE BUG. It computed savings straight off the
    // fixture's 8,200 kWh, which is Google's DC figure — energy at the panel,
    // before the inverter — and asserted $1,132/yr and ~7.1 years payback.
    // Money has to come off what reaches the meter:
    //   delivered = 8200 × (1 − 0.1408) × 0.96          = 6,763.6 kWh
    //   savings   = 6763.6×0.30×0.32 + 6763.6×0.70×0.06 = $933.4  → $933
    //   payback   = (20 × 400 × 1.00) / 933.4           = 8.6 years
    // The old figures are kept above deliberately: the gap between 7.1 and 8.6
    // years is the defect this change fixes, and a future edit that "restores"
    // the old numbers is reintroducing it.
    expect(screen.getByText(/\$9\d\d\s*\/\s*yr/)).toBeInTheDocument();
    expect(screen.getByText(/8\.\d years/)).toBeInTheDocument();
    // And the DC figure must NOT be what the money was built from.
    expect(screen.queryByText(/\$1,1\d\d\s*\/\s*yr/)).not.toBeInTheDocument();
  });

  it('does NOT show LockedPreviewCard when coverage_available is false', async () => {
    await runReport(NO_COVERAGE_RESULT);
    expect(screen.queryByText('Your solar financials')).not.toBeInTheDocument();
  });

  it('shows "Your solar financials" heading', async () => {
    await runReport();
    expect(screen.getByText('Your solar financials')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PaidDownloadCTA
// ---------------------------------------------------------------------------

describe('SolarYieldTool — PaidDownloadCTA after payment success', () => {
  it('shows PaidDownloadCTA when ?payment=success&report_id=X in URL', async () => {
    setTestUrl('/reports/solar-yield?payment=success&report_id=paid-report-uuid');
    render(<SolarYieldTool />);
    await waitFor(() => {
      expect(screen.getByText('Payment confirmed — your report is ready.')).toBeInTheDocument();
    });
  });

  it('does NOT show SolarLockedPreviewCard when PaidDownloadCTA is shown', async () => {
    setTestUrl('/reports/solar-yield?payment=success&report_id=paid-report-uuid');
    render(<SolarYieldTool />);
    await waitFor(() => {
      expect(screen.queryByText('Annual electricity savings')).not.toBeInTheDocument();
    });
  });

  it('download button POSTs to generate route with report_id', async () => {
    setTestUrl('/reports/solar-yield?payment=success&report_id=paid-uuid-123');

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(new Uint8Array([37, 80, 68, 70]), { // %PDF
        status: 200,
        headers: { 'Content-Type': 'application/pdf' },
      })
    );

    // jsdom doesn't implement URL.createObjectURL
    global.URL.createObjectURL = jest.fn().mockReturnValue('blob:mock');
    global.URL.revokeObjectURL = jest.fn();

    render(<SolarYieldTool />);
    await waitFor(() => screen.getByText('Download PDF report →'));
    fireEvent.click(screen.getByText('Download PDF report →'));

    await waitFor(() => {
      const generateCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
        String(url).includes('/api/reports/solar-yield/generate')
      );
      expect(generateCall).toBeDefined();
      const body = JSON.parse(generateCall[1].body);
      expect(body.report_id).toBe('paid-uuid-123');
    });
  });
});
