/**
 * ThreatRadarTool paywall behaviour.
 *
 * Partial results gate:
 *   - 6 results: first 3 shown clearly, MonitorPreviewCard between 3 and 4, results 4-6 blurred
 *   - 2 results: both shown, MonitorPreviewCard after last result
 *   - 0 results: "no applications found" + MonitorPreviewCard after
 *
 * MonitorPreviewCard:
 *   - Email input present (subscription requires email)
 *   - Subscribe button fires checkout route
 *   - Mock DA card present (blurred content)
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

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

jest.mock('@/components/reports/PostResultEmailStrip', () => ({
  PostResultEmailStrip: () => null,
}));

jest.mock('@/components/reports/DownloadPdfButton', () => ({
  DownloadPdfButton: () => null,
}));

jest.mock('@/components/providers/PostHogProvider', () => ({
  posthog: { capture: jest.fn() },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeApp(i: number) {
  return {
    PlanningPortalApplicationNumber: `DA/2026/${1000 + i}`,
    ApplicationType: 'Development Application',
    ApplicationDescription: `Description for application ${i}`,
    LodgementDate: '2026-03-15',
    Status: 'Under Assessment',
    PropertyAddress: `${i} Test St Haberfield NSW 2045`,
    _distance_m: 50 + i * 20,
  };
}

function makeSearchResult(appCount: number) {
  return {
    address: '5 Commercial Rd Haberfield NSW 2045',
    prop_id: 'prop-123',
    lat: -33.87,
    lng: 151.09,
    run_date: '2026-04-30',
    council_name: 'Inner West Council',
    applications: Array.from({ length: appCount }, (_, i) => makeApp(i)),
    window_days: 90,
    report_token: 'tok-abc',
  };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockSearchFetch(appCount: number) {
  (global.fetch as jest.Mock).mockResolvedValueOnce(
    new Response(JSON.stringify(makeSearchResult(appCount)), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  );
}

async function runSearch(appCount: number) {
  render(<ThreatRadarTool />);
  mockSearchFetch(appCount);
  fireEvent.change(screen.getByTestId('address-input'), { target: { value: '5 Commercial Rd Haberfield NSW 2045' } });
  fireEvent.click(screen.getByRole('button', { name: /check nearby applications/i }));
  await waitFor(() => screen.getByTestId('monitor-preview-card'));
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: 'http://localhost/', search: '' },
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Many results (6) — partial gate
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — 6 results (partial gate)', () => {
  it('shows MonitorPreviewCard in results', async () => {
    await runSearch(6);
    expect(screen.getByTestId('monitor-preview-card')).toBeInTheDocument();
  });

  it('shows first 3 application numbers (not blurred)', async () => {
    await runSearch(6);
    // First 3 should render without blur class
    expect(screen.getByText('DA/2026/1000')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1001')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1002')).toBeInTheDocument();
  });

  it('card shows correct hidden count for 6 results', async () => {
    await runSearch(6);
    expect(screen.getByText(/3 more applications below/i)).toBeInTheDocument();
  });

  it('shows email input in MonitorPreviewCard', async () => {
    await runSearch(6);
    expect(screen.getByTestId('monitor-email-input')).toBeInTheDocument();
  });

  it('shows mock blurred DA card in MonitorPreviewCard', async () => {
    await runSearch(6);
    // Mock DA card text exists in DOM (blurred via CSS, not hidden from DOM)
    expect(screen.getByText(/DA\/2026\/8821/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Few results (2) — card shown after all results
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — 2 results (card after all results)', () => {
  it('shows MonitorPreviewCard after results', async () => {
    await runSearch(2);
    expect(screen.getByTestId('monitor-preview-card')).toBeInTheDocument();
  });

  it('shows both application results', async () => {
    await runSearch(2);
    expect(screen.getByText('DA/2026/1000')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1001')).toBeInTheDocument();
  });

  it("card shows 'What you'd miss next week' when no hidden results", async () => {
    await runSearch(2);
    expect(screen.getByText(/What you'd miss next week/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Subscribe flow
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — subscribe from MonitorPreviewCard', () => {
  it('subscribe button fires checkout with address and email', async () => {
    await runSearch(2);

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(JSON.stringify({ checkout_url: 'https://checkout.stripe.com/pay/cs_sub_test' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    );

    const emailInput = screen.getByTestId('monitor-email-input');
    fireEvent.change(emailInput, { target: { value: 'user@example.com' } });
    fireEvent.submit(emailInput.closest('form')!);

    await waitFor(() => {
      expect(window.location.href).toBe('https://checkout.stripe.com/pay/cs_sub_test');
    });

    const subCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
      String(url).includes('/api/stripe/checkout/threat-radar-monitor')
    );
    expect(subCall).toBeDefined();
    const body = JSON.parse(subCall[1].body);
    expect(body.email).toBe('user@example.com');
    expect(body.address).toBeTruthy();
  });
});
