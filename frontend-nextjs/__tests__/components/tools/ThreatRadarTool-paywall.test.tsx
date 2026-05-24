/**
 * ThreatRadarTool paywall behaviour.
 *
 * Current UI:
 *   - ALL results shown (no partial gate)
 *   - MonitorPreviewCard with WaitlistButton (no email input / Stripe checkout)
 *   - Mock blurred DA card present in MonitorPreviewCard
 *   - FreePaidComparison shown
 *   - DownloadPdfButton and PostResultEmailStrip shown after results
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

jest.mock('@/components/reports/ToolCrossSell', () => ({
  ToolCrossSell: () => null,
}));

jest.mock('@/components/reports/WaitlistButton', () => ({
  WaitlistButton: ({ interestType, label }: { interestType: string; label?: string }) => (
    <button data-testid={`waitlist-btn-${interestType}`}>{label ?? 'Join waitlist'}</button>
  ),
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

function makeApp(i: number) {
  return {
    PlanningPortalApplicationNumber: `DA/2026/${1000 + i}`,
    ApplicationType: 'Development Application',
    DevelopmentType: 'Alterations & additions',
    ApplicationDescription: `Description for application ${i}`,
    LodgementDate: '2026-03-15',
    Status: 'Under Assessment',
    PropertyAddress: `${i} Test St Haberfield NSW 2045`,
    CostOfDevelopment: 100000,
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
    value: { href: 'http://localhost/', search: '', pathname: '/reports/threat-radar' },
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
// Many results (6) — all shown (no partial gate)
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — 6 results', () => {
  it('shows MonitorPreviewCard in results', async () => {
    await runSearch(6);
    expect(screen.getByTestId('monitor-preview-card')).toBeInTheDocument();
  });

  it('shows all 6 application numbers', async () => {
    await runSearch(6);
    expect(screen.getByText('DA/2026/1000')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1001')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1002')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1003')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1004')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1005')).toBeInTheDocument();
  });

  it('shows mock blurred DA card in MonitorPreviewCard', async () => {
    await runSearch(6);
    // Mock DA card text exists in DOM (blurred via CSS, not hidden from DOM)
    expect(screen.getByText(/DA\/2026\/8821/)).toBeInTheDocument();
  });

  it('shows "Weekly DA monitoring — coming soon" in MonitorPreviewCard', async () => {
    await runSearch(6);
    // Text appears in both MonitorPreviewCard and the top-level waitlist section
    const elements = screen.getAllByText(/Weekly DA monitoring — coming soon/);
    expect(elements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows WaitlistButton in MonitorPreviewCard', async () => {
    await runSearch(6);
    // WaitlistButton appears in both MonitorPreviewCard and the top-level waitlist section
    const waitlistBtns = screen.getAllByTestId('waitlist-btn-threat-radar');
    expect(waitlistBtns.length).toBeGreaterThanOrEqual(1);
  });
});

// ---------------------------------------------------------------------------
// Few results (2) — card shown after all results
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — 2 results', () => {
  it('shows MonitorPreviewCard after results', async () => {
    await runSearch(2);
    expect(screen.getByTestId('monitor-preview-card')).toBeInTheDocument();
  });

  it('shows both application results', async () => {
    await runSearch(2);
    expect(screen.getByText('DA/2026/1000')).toBeInTheDocument();
    expect(screen.getByText('DA/2026/1001')).toBeInTheDocument();
  });

  it('shows "Example alert" text in MonitorPreviewCard', async () => {
    await runSearch(2);
    expect(screen.getByText(/Example alert/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Zero results
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — 0 results', () => {
  it('shows "No applications found" when no results', async () => {
    render(<ThreatRadarTool />);
    mockSearchFetch(0);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '5 Commercial Rd Haberfield NSW 2045' } });
    fireEvent.click(screen.getByRole('button', { name: /check nearby applications/i }));
    await waitFor(() => screen.getByText(/No applications found/));
    expect(screen.getByText(/No applications found/)).toBeInTheDocument();
  });
});
