/**
 * SolarYieldTool paywall behaviour.
 *
 * After a result with coverage_available=true:
 *   - SolarLockedPreviewCard renders with blurred financial values
 *   - No email input visible
 *   - Clicking Unlock fires checkout with {report_id, address} (no email)
 *
 * After payment success URL params:
 *   - PaidDownloadCTA renders instead of SolarLockedPreviewCard
 *   - Download button calls generate route
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SolarYieldTool } from '@/components/tools/SolarYieldTool';

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
  // Wait for grade badge to appear (coverage_available path) or "not assessable" (no coverage)
  await waitFor(() => {
    const hasGrade = screen.queryByText(/Annual electricity savings/i) || screen.queryByText(/not assessable/i) || screen.queryByText(/Building data not available/i);
    if (!hasGrade) throw new Error('Result not yet rendered');
  });
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: 'http://localhost/', search: '', pathname: '/reports/solar-yield' },
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
// LockedPreviewCard
// ---------------------------------------------------------------------------

describe('SolarYieldTool — LockedPreviewCard after result', () => {
  it('shows SolarLockedPreviewCard when coverage_available and report_id present', async () => {
    await runReport();
    expect(screen.getByText('Annual electricity savings')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /unlock full analysis.*\$19/i })).toBeInTheDocument();
  });

  it('shows all blurred preview rows', async () => {
    await runReport();
    expect(screen.getByText('Annual electricity savings')).toBeInTheDocument();
    expect(screen.getByText('Payback period')).toBeInTheDocument();
    expect(screen.getByText('Installed cost estimate')).toBeInTheDocument();
    expect(screen.getByText('Feed-in contribution')).toBeInTheDocument();
    expect(screen.getByText('Full PDF report')).toBeInTheDocument();
  });

  it('blurred values contain real computed $ amounts', async () => {
    await runReport();
    // annual_savings = (8200*0.30*0.32) + (8200*0.70*0.06) = 786.24 + 344.4 = 1,130.64 → $1,131
    const savingsEl = screen.getByText(/\$1,1\d\d\s*\/\s*yr/);
    expect(savingsEl).toBeInTheDocument();
    // payback = (20*400*1.00) / 1130.64 ≈ 7.1 years
    expect(screen.getByText(/7\.\d years/)).toBeInTheDocument();
  });

  it('does NOT show email input in LockedPreviewCard', async () => {
    await runReport();
    // The coverage interest form has an email field, but LockedPreviewCard must not
    const emailInputs = screen.queryAllByPlaceholderText(/email/i);
    // Filter out coverage interest form (which is in no-coverage branch — not shown here)
    expect(emailInputs).toHaveLength(0);
  });

  it('does NOT show LockedPreviewCard when coverage_available is false', async () => {
    await runReport(NO_COVERAGE_RESULT);
    expect(screen.queryByText('Annual electricity savings')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /unlock/i })).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// handleUnlock
// ---------------------------------------------------------------------------

describe('SolarYieldTool — handleUnlock', () => {
  it('fires checkout POST with {report_id, address} and redirects', async () => {
    await runReport();

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ checkout_url: 'https://checkout.stripe.com/pay/cs_test_sol' }), {
        status: 200, headers: { 'Content-Type': 'application/json' },
      })
    );

    fireEvent.click(screen.getByRole('button', { name: /unlock full analysis/i }));

    await waitFor(() => {
      expect(window.location.href).toBe('https://checkout.stripe.com/pay/cs_test_sol');
    });

    const checkoutCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
      String(url).includes('/api/stripe/checkout/solar-yield')
    );
    expect(checkoutCall).toBeDefined();
    const body = JSON.parse(checkoutCall[1].body);
    expect(body.report_id).toBe('sol-report-uuid-1234');
    expect(body.address).toBe('5 Commercial Rd Haberfield NSW 2045');
    expect(body).not.toHaveProperty('email');
  });

  it('shows error when checkout call fails', async () => {
    await runReport();

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'Service unavailable' }), {
        status: 503, headers: { 'Content-Type': 'application/json' },
      })
    );

    fireEvent.click(screen.getByRole('button', { name: /unlock full analysis/i }));

    await waitFor(() => {
      expect(screen.getByText('Service unavailable')).toBeInTheDocument();
    });
  });

  it('button shows "Starting checkout..." and is disabled while in flight', async () => {
    await runReport();
    (global.fetch as jest.Mock).mockImplementationOnce(() => new Promise(() => {}));

    fireEvent.click(screen.getByRole('button', { name: /unlock full analysis/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /starting checkout/i })).toBeDisabled();
    });
  });
});

// ---------------------------------------------------------------------------
// PaidDownloadCTA
// ---------------------------------------------------------------------------

describe('SolarYieldTool — PaidDownloadCTA after payment success', () => {
  it('shows PaidDownloadCTA when ?payment=success&report_id=X in URL', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        href: 'http://localhost/reports/solar-yield?payment=success&report_id=paid-report-uuid',
        search: '?payment=success&report_id=paid-report-uuid',
        pathname: '/reports/solar-yield',
      },
    });
    render(<SolarYieldTool />);
    await waitFor(() => {
      expect(screen.getByText('Payment confirmed — your report is ready.')).toBeInTheDocument();
    });
  });

  it('does NOT show SolarLockedPreviewCard when PaidDownloadCTA is shown', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        href: 'http://localhost/reports/solar-yield?payment=success&report_id=paid-report-uuid',
        search: '?payment=success&report_id=paid-report-uuid',
        pathname: '/reports/solar-yield',
      },
    });
    render(<SolarYieldTool />);
    await waitFor(() => {
      expect(screen.queryByText('Annual electricity savings')).not.toBeInTheDocument();
    });
  });

  it('download button POSTs to generate route with report_id', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        href: 'http://localhost/reports/solar-yield?payment=success&report_id=paid-uuid-123',
        search: '?payment=success&report_id=paid-uuid-123',
        pathname: '/reports/solar-yield',
      },
    });

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
