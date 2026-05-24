/**
 * FloodTool paywall behaviour.
 *
 * After a result with report_id:
 *   - FloodLockedPreviewCard renders with blurred real data values
 *   - WaitlistButton shown (no Stripe checkout)
 *
 * Alarm headline varies by flood_signal.
 * After payment success URL params: PaidDownloadCTA shown.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FloodTool } from '@/components/tools/FloodTool';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

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

const ELEVATED_RESULT = {
  address: '23 Flood St Lismore NSW 2480',
  lat: -28.81,
  lng: 153.28,
  run_date: '2026-04-30',
  outputs: {
    epi_flood_class: 'high_flood_risk',
    epi_flood_label: 'High flood risk zone',
    sar_flood_detected: true,
    sar_confidence: 'high',
    sar_analysis_date: '2022-03-01',
    ems_flood_detected: true,
    ems_activations: [
      { activation_id: 'ems-1', event_name: 'Lismore 2022', event_date: '2022-02-28', flood_type: 'riverine' },
      { activation_id: 'ems-2', event_name: 'Lismore 2022b', event_date: '2022-03-28', flood_type: 'riverine' },
    ],
    jrc_water_occurrence_pct: 34,
    jrc_data_year: 2022,
    bom_gauge_name: 'Lismore Wilson River',
    bom_gauge_distance_km: 0.4,
    bom_last_major_flood_date: '2022-03-28',
    bom_last_major_flood_peak_m: 14.4,
    s1_gap_warning: null,
    data_currency: '2026-04-01',
    flood_signal: 'elevated' as const,
    dea_wofs_frequency_pct: null,
    ses_in_flood_planning_area: null,
    ses_flood_class: null,
    ses_aep_tiers: null,
    ses_study_name: null,
    ses_study_lga: null,
    hawkesbury_flood_level_2aep: null,
    hawkesbury_flood_level_5aep: null,
    hawkesbury_flood_level_10aep: null,
    hawkesbury_flood_level_20aep: null,
    hawkesbury_flood_level_50aep: null,
    hawkesbury_flood_level_100aep: null,
    hawkesbury_flood_level_200aep: null,
    hawkesbury_flood_level_500aep: null,
    hawkesbury_flood_level_pmf: null,
    hawkesbury_flood_study: null,
  },
  confidence: 'high',
  data_sources: ['NSW EPI Flood WFS', 'Copernicus EMS', 'JRC GSW', 'BOM Gauge'],
  report_id: 'flood-report-uuid-1234',
};

const NONE_RESULT = {
  ...ELEVATED_RESULT,
  address: '5 High St Pymble NSW 2073',
  outputs: {
    ...ELEVATED_RESULT.outputs,
    epi_flood_class: 'none',
    epi_flood_label: null,
    sar_flood_detected: false,
    ems_flood_detected: false,
    ems_activations: [],
    jrc_water_occurrence_pct: 0,
    bom_last_major_flood_date: null,
    bom_last_major_flood_peak_m: null,
    flood_signal: 'none' as const,
  },
  report_id: 'flood-report-uuid-none',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function mockCheckFetch(result: typeof ELEVATED_RESULT) {
  (global.fetch as jest.Mock).mockResolvedValueOnce(
    new Response(JSON.stringify(result), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  );
}

async function runFloodCheck(result = ELEVATED_RESULT) {
  render(<FloodTool />);
  mockCheckFetch(result);
  fireEvent.change(screen.getByTestId('address-input'), { target: { value: result.address } });
  fireEvent.click(screen.getByRole('button', { name: /run flood check/i }));
  await waitFor(() => screen.getByText('Your flood data'));
}

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

beforeEach(() => {
  global.fetch = jest.fn();
  Object.defineProperty(window, 'location', {
    writable: true,
    value: { href: 'http://localhost/', search: '', pathname: '/reports/flood' },
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
// FloodLockedPreviewCard — elevated result
// ---------------------------------------------------------------------------

describe('FloodTool — FloodLockedPreviewCard (elevated signal)', () => {
  it('shows FloodLockedPreviewCard with real data rows', async () => {
    await runFloodCheck();
    expect(screen.getByText('Your flood data')).toBeInTheDocument();
    // WaitlistButton replaces Stripe checkout
    expect(screen.getByTestId('waitlist-btn-flood-truth')).toBeInTheDocument();
  });

  it('shows BOM last major flood date (blurred)', async () => {
    await runFloodCheck();
    expect(screen.getByText('BOM last major flood')).toBeInTheDocument();
    // Value: Mar 2022 (formatted from 2022-03-28)
    expect(screen.getByText(/Mar 2022/)).toBeInTheDocument();
  });

  it('shows peak river height (blurred)', async () => {
    await runFloodCheck();
    expect(screen.getByText('Peak river height')).toBeInTheDocument();
    expect(screen.getByText(/14\.4m/)).toBeInTheDocument();
  });

  it('shows EMS event count (blurred)', async () => {
    await runFloodCheck();
    expect(screen.getByText('Historical inundation events')).toBeInTheDocument();
    expect(screen.getByText(/2 events since 2000/)).toBeInTheDocument();
  });

  it('shows JRC water occurrence (blurred)', async () => {
    await runFloodCheck();
    expect(screen.getByText('40-year water occurrence')).toBeInTheDocument();
    expect(screen.getByText(/34%/)).toBeInTheDocument();
  });

  it('shows BOM gauge name and distance (blurred)', async () => {
    await runFloodCheck();
    expect(screen.getByText('Nearest BOM gauge')).toBeInTheDocument();
    expect(screen.getByText(/Lismore Wilson River.*0\.4km/)).toBeInTheDocument();
  });

  it('shows elevated signal alarm headline', async () => {
    await runFloodCheck();
    expect(screen.getByText(/Elevated flood signal/i)).toBeInTheDocument();
  });

  it('shows alarm headline about lender for elevated signal', async () => {
    await runFloodCheck();
    expect(screen.getByText(/multiple independent flood sources/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FloodLockedPreviewCard — no-signal result
// ---------------------------------------------------------------------------

describe('FloodTool — FloodLockedPreviewCard (no flood signal)', () => {
  it('still shows FloodLockedPreviewCard for conveyancing use case', async () => {
    await runFloodCheck(NONE_RESULT);
    expect(screen.getByText('Your flood data')).toBeInTheDocument();
  });

  it('shows "No flood indicators" headline for no-signal result', async () => {
    await runFloodCheck(NONE_RESULT);
    expect(screen.getByText(/No flood indicators detected across checked sources/i)).toBeInTheDocument();
  });

  it('shows 0 events for no EMS activations', async () => {
    await runFloodCheck(NONE_RESULT);
    expect(screen.getByText(/0 events since 2000/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// PaidDownloadCTA
// ---------------------------------------------------------------------------

describe('FloodTool — PaidDownloadCTA after payment success', () => {
  it('shows PaidDownloadCTA when ?payment=success&report_id=X in URL', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        href: 'http://localhost/reports/flood?payment=success&report_id=paid-flood-uuid',
        search: '?payment=success&report_id=paid-flood-uuid',
        pathname: '/reports/flood',
      },
    });
    render(<FloodTool />);
    await waitFor(() => {
      expect(screen.getByText('Payment confirmed — your report is ready.')).toBeInTheDocument();
    });
  });

  it('download button calls /api/reports/flood/generate with report_id', async () => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: {
        search: '?payment=success&report_id=paid-flood-uuid-123',
        pathname: '/reports/flood',
      },
    });

    (global.fetch as jest.Mock).mockResolvedValueOnce(
      new Response(new Uint8Array([37, 80, 68, 70]), {
        status: 200,
        headers: { 'Content-Type': 'application/pdf' },
      })
    );

    global.URL.createObjectURL = jest.fn().mockReturnValue('blob:mock');
    global.URL.revokeObjectURL = jest.fn();

    render(<FloodTool />);
    await waitFor(() => screen.getByText('Download PDF report →'));
    fireEvent.click(screen.getByText('Download PDF report →'));

    await waitFor(() => {
      const generateCall = (global.fetch as jest.Mock).mock.calls.find(([url]: [string]) =>
        String(url).includes('/api/reports/flood/generate')
      );
      expect(generateCall).toBeDefined();
      const body = JSON.parse(generateCall[1].body);
      expect(body.report_id).toBe('paid-flood-uuid-123');
    });
  });
});
