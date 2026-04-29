/**
 * GrannyFlatTool paywall behaviour.
 *
 * After an eligible result:
 *   - LockedPreviewCard renders with "Unlock full analysis — $49" button
 *   - No yield calculator shown (it's behind the paywall)
 *   - Clicking Unlock fires detect then checkout in sequence
 *
 * After an ineligible result:
 *   - LockedPreviewCard does NOT render
 *   - "If this lot qualified" yield calculator IS shown
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GrannyFlatTool } from '@/components/tools/GrannyFlatTool';

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
    placeholder: string;
    className: string;
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

jest.mock('@/components/providers/PostHogProvider', () => ({
  posthog: { capture: jest.fn() },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const ELIGIBLE_RESULT = {
  detect_id: null,
  address: '5 Commercial Rd Haberfield NSW 2045',
  lat: -33.87,
  lng: 151.09,
  lot_polygon: null,
  lga_name: 'Inner West Council',
  epi_name: 'Inner West LEP 2022',
  lot_area_m2: 600,
  lot_width_m: 15,
  lot_depth_m: 40,
  zone: 'R2',
  height_of_buildings: '9.5m',
  fsr: '0.55:1',
  min_lot_size_m2: null,
  nearby_secondary_dwelling_count: 3,
  dcp_available: true,
  sepp_eligible: true,
  sepp_ineligible_reason: null,
  confirmation_required: false,
  checks: {
    lot_area: 'pass',
    zone: 'pass',
    heritage: 'pass',
    flood: 'pass',
    biodiversity: 'pass',
    acid_sulfate: 'pass',
  },
};

const INELIGIBLE_RESULT = {
  ...ELIGIBLE_RESULT,
  lot_area_m2: 380,
  sepp_eligible: false,
  sepp_ineligible_reason: 'Lot area 380 m² is below the 450 m² minimum',
  checks: {
    lot_area: 'fail',
    zone: 'pass',
    heritage: 'pass',
    flood: 'pass',
    biodiversity: 'pass',
    acid_sulfate: 'pass',
  },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockCheckFetch(result: typeof ELIGIBLE_RESULT) {
  (global.fetch as jest.Mock).mockResolvedValueOnce(
    new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  );
}

async function runEligibilityCheck(result: typeof ELIGIBLE_RESULT) {
  render(<GrannyFlatTool />);
  mockCheckFetch(result);
  const input = screen.getByTestId('address-input');
  fireEvent.change(input, { target: { value: result.address } });
  const btn = screen.getByRole('button', { name: /check my property/i });
  fireEvent.click(btn);
  await waitFor(() => screen.getByText(/eligible|not eligible/i));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  // jsdom doesn't implement window.location.href assignment
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: 'http://localhost/', search: '' },
  });
  Object.defineProperty(window, 'history', {
    writable: true,
    value: { replaceState: jest.fn() },
  });
  Object.defineProperty(navigator, 'clipboard', {
    writable: true,
    value: { writeText: jest.fn().mockResolvedValue(undefined) },
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

describe('GrannyFlatTool — eligible result paywall', () => {
  it('shows LockedPreviewCard after eligible result', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);
    expect(screen.getByText('Full property analysis')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /unlock full analysis.*\$49/i })).toBeInTheDocument();
  });

  it('shows blurred preview rows in LockedPreviewCard', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);
    expect(screen.getByText('Aerial structure analysis')).toBeInTheDocument();
    expect(screen.getByText('Your rental income estimate')).toBeInTheDocument();
    expect(screen.getByText('Yield on build cost')).toBeInTheDocument();
    expect(screen.getByText('Break-even projection')).toBeInTheDocument();
  });

  it('shows LGA name in DCP setbacks row', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);
    expect(screen.getByText('DCP setbacks — Inner West Council')).toBeInTheDocument();
  });

  it('does NOT show interactive yield calculator for eligible result', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);
    // The "Estimated return" label only appears in the old eligible yield calculator
    expect(screen.queryByText('Estimated return')).not.toBeInTheDocument();
    // The "If this lot qualified" label is for ineligible only
    expect(screen.queryByText('If this lot qualified')).not.toBeInTheDocument();
  });

  it('handleUnlock fires detect then checkout and redirects', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);

    // Mock detect response
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ jobId: 'job-uuid-test-123' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );
    // Mock checkout response
    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ checkout_url: 'https://checkout.stripe.com/pay/cs_test' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    fireEvent.click(screen.getByRole('button', { name: /unlock full analysis/i }));

    await waitFor(() => {
      expect(window.location.href).toBe('https://checkout.stripe.com/pay/cs_test');
    });

    // Verify detect was called with correct action
    const detectCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
      String(url).includes('/api/satellite/granny-flat')
    );
    expect(detectCall).toBeDefined();
    const detectBody = JSON.parse(detectCall[1].body);
    expect(detectBody.action).toBe('detect');

    // Verify checkout was called with job_id (not report_id)
    const checkoutCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
      String(url).includes('/api/stripe/checkout/granny-flat')
    );
    expect(checkoutCall).toBeDefined();
    const checkoutBody = JSON.parse(checkoutCall[1].body);
    expect(checkoutBody.job_id).toBe('job-uuid-test-123');
    expect(checkoutBody).not.toHaveProperty('report_id');
  });

  it('shows error message when unlock detect call fails', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'Service unavailable' }), {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    fireEvent.click(screen.getByRole('button', { name: /unlock full analysis/i }));

    await waitFor(() => {
      expect(screen.getByText('Service unavailable')).toBeInTheDocument();
    });
  });

  it('button shows "Starting analysis…" while unlocking', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);

    // Never resolve to keep it in-flight
    (global.fetch as jest.Mock).mockImplementationOnce(
      () => new Promise(() => {})
    );

    fireEvent.click(screen.getByRole('button', { name: /unlock full analysis/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /starting analysis/i })).toBeDisabled();
    });
  });
});

describe('GrannyFlatTool — ineligible result', () => {
  it('does NOT show LockedPreviewCard for ineligible result', async () => {
    await runEligibilityCheck(INELIGIBLE_RESULT);
    expect(screen.queryByText('Full property analysis')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /unlock full analysis/i })).not.toBeInTheDocument();
  });

  it('shows "If this lot qualified" yield calculator for ineligible', async () => {
    await runEligibilityCheck(INELIGIBLE_RESULT);
    expect(screen.getByText('If this lot qualified')).toBeInTheDocument();
  });

  it('shows "What could change this?" section for ineligible', async () => {
    await runEligibilityCheck(INELIGIBLE_RESULT);
    expect(screen.getByText('What could change this?')).toBeInTheDocument();
  });
});
