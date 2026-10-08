/**
 * GrannyFlatTool paywall behaviour.
 *
 * After an eligible result:
 *   - LockedPreviewCard renders with "Your Granny Flat Feasibility Report" heading
 *   - WaitlistButton shown (no Stripe checkout)
 *   - FreePaidComparison shown
 *
 * After an ineligible result:
 *   - LockedPreviewCard does NOT render
 *   - "If this lot qualified" yield calculator IS shown
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { GrannyFlatTool } from '@/components/tools/GrannyFlatTool';

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

jest.mock('@/components/reports/ToolCrossSell', () => ({
  ToolCrossSell: () => null,
}));

jest.mock('@/components/reports/WaitlistButton', () => ({
  WaitlistButton: ({ interestType }: { interestType: string }) => (
    <button data-testid={`waitlist-btn-${interestType}`}>Join waitlist</button>
  ),
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
  // Wait for the badge text. A passing quick check reads "No exclusion found",
  // not "Eligible": lot area is tested per approval path, not by this check.
  await waitFor(() => {
    const matches = screen.getAllByText(/no exclusion found|not eligible/i);
    if (matches.length === 0) throw new Error('Result not yet rendered');
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  // jsdom doesn't implement window.location.href assignment
  setTestUrl('/canibuildit');
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
    expect(screen.getByText('Your Granny Flat Feasibility Report')).toBeInTheDocument();
    // WaitlistButton replaces Stripe checkout
    expect(screen.getByTestId('waitlist-btn-granny-flat')).toBeInTheDocument();
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
    // The "If this lot qualified" label is for ineligible only
    expect(screen.queryByText('If this lot qualified')).not.toBeInTheDocument();
  });

  it('shows FreePaidComparison for eligible result', async () => {
    await runEligibilityCheck(ELIGIBLE_RESULT);
    expect(screen.getByText('Included free')).toBeInTheDocument();
    expect(screen.getByText('In paid report')).toBeInTheDocument();
  });
});

describe('GrannyFlatTool — ineligible result', () => {
  it('does NOT show LockedPreviewCard for ineligible result', async () => {
    await runEligibilityCheck(INELIGIBLE_RESULT);
    expect(screen.queryByText('Your Granny Flat Feasibility Report')).not.toBeInTheDocument();
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
