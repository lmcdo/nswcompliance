/**
 * Adversarial tests for ThreatRadarTool component.
 * Covers: search state machine, subscribe state machine,
 * null-safety on applications field, optional app fields,
 * reset flow, PostHog capture.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool';

jest.mock('@/components/reports/AddressAutocomplete', () => ({
  AddressAutocomplete: ({
    value,
    onChange,
    disabled,
    placeholder,
  }: {
    value: string;
    onChange: (v: string) => void;
    disabled?: boolean;
    placeholder?: string;
  }) => (
    <input
      data-testid="address-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      placeholder={placeholder}
    />
  ),
}));

const mockCapture = jest.fn();
jest.mock('@/components/providers/PostHogProvider', () => ({
  posthog: { capture: (...args: unknown[]) => mockCapture(...args) },
}));

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeSearchResult(overrides: Partial<{
  applications: unknown;
  council_name: string;
  window_days: number;
}> = {}) {
  return {
    address: '1 Smith St Surry Hills NSW 2010',
    prop_id: 'prop_123',
    lat: -33.88,
    lng: 151.21,
    council_name: 'Inner West Council',
    window_days: 90,
    applications: [],
    ...overrides,
  };
}

function makeApplication(overrides: Record<string, unknown> = {}) {
  return {
    PlanningPortalApplicationNumber: 'DA-2024-001',
    ApplicationType: 'Development Application',
    ApplicationDescription: 'Demolish existing dwelling and construct new 2-storey dwelling',
    LodgementDate: '2024-01-15',
    DeterminationDate: '2024-03-10',
    Status: 'Determined',
    PropertyAddress: '3 Smith St Surry Hills',
    LotDescription: 'Lot 1 DP 12345',
    CostOfDevelopment: 450000,
    NumberOfNewDwellings: 1,
    _distance_m: 45,
    ...overrides,
  };
}

function mockSearchSuccess(result = makeSearchResult()) {
  mockFetch.mockResolvedValueOnce({ ok: true, json: async () => result });
}

function mockSearchError(message: string) {
  mockFetch.mockResolvedValueOnce({ ok: false, json: async () => ({ error: message }) });
}

function mockSubscribeSuccess() {
  mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ checkout_url: 'https://checkout.stripe.com/mock' }) });
}

function mockSubscribeError(message: string) {
  mockFetch.mockResolvedValueOnce({ ok: false, json: async () => ({ error: message }) });
}

// ---------------------------------------------------------------------------
// Idle state
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — idle state', () => {
  beforeEach(() => { mockFetch.mockReset(); mockCapture.mockReset(); });

  it('renders form with search button', () => {
    render(<ThreatRadarTool />);
    expect(screen.getByRole('button', { name: 'Check nearby applications' })).toBeInTheDocument();
  });

  it('search button disabled when address is empty', () => {
    render(<ThreatRadarTool />);
    expect(screen.getByRole('button', { name: 'Check nearby applications' })).toBeDisabled();
  });

  it('waitlist section is visible on initial render', () => {
    render(<ThreatRadarTool />);
    expect(screen.getByText(/Weekly DA monitoring — coming soon/i)).toBeInTheDocument();
  });

  it('waitlist join button disabled when email is empty', () => {
    render(<ThreatRadarTool />);
    expect(screen.getByRole('button', { name: /Join waitlist/i })).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
// Search state machine
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — search', () => {
  beforeEach(() => { mockFetch.mockReset(); mockCapture.mockReset(); });

  it('hides search form while request is pending', async () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    // In searching state, form is replaced with address text and "Search new address" button
    expect(await screen.findByText('Search new address')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Check nearby applications' })).not.toBeInTheDocument();
  });

  it('fires posthog threat_radar_search on submit', async () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '42 Test Rd' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    await waitFor(() => expect(mockCapture).toHaveBeenCalledWith('threat_radar_search', expect.objectContaining({ address: '42 Test Rd' })));
  });

  it('shows search error message on API failure', async () => {
    mockSearchError('Address not found in NSW');
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('Address not found in NSW')).toBeInTheDocument();
  });

  it('shows generic error when fetch rejects entirely', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('Network error')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Search results
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — search results', () => {
  beforeEach(() => { mockFetch.mockReset(); mockCapture.mockReset(); });

  it('shows "No applications found" when applications is empty array', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('No applications found')).toBeInTheDocument();
  });

  it('null applications from API does not crash — treated as empty', async () => {
    mockSearchSuccess(makeSearchResult({ applications: null }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('No applications found')).toBeInTheDocument();
  });

  it('shows application count in findings (singular)', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication()] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    const matches = await screen.findAllByText(/1 application/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('shows application count in findings (plural)', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication(), makeApplication({ PlanningPortalApplicationNumber: 'DA-2024-002' })] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    const matches = await screen.findAllByText(/2 applications/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it('shows application number and description', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication()] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('DA-2024-001')).toBeInTheDocument();
    expect(screen.getByText('Demolish existing dwelling and construct new 2-storey dwelling')).toBeInTheDocument();
  });

  it('shows distance badge when _distance_m is present', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication({ _distance_m: 45 })] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('45m away')).toBeInTheDocument();
  });

  it('application with all optional fields null does not crash', async () => {
    const minimalApp = {
      PlanningPortalApplicationNumber: 'DA-2024-003',
      ApplicationType: undefined,
      DevelopmentType: undefined,
      ApplicationDescription: undefined,
      LodgementDate: undefined,
      DeterminationDate: undefined,
      Status: undefined,
      PropertyAddress: undefined,
      LotDescription: undefined,
      CostOfDevelopment: null,
      NumberOfNewDwellings: null,
      _distance_m: null,
    };
    mockSearchSuccess(makeSearchResult({ applications: [minimalApp] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('DA-2024-003')).toBeInTheDocument();
  });

  it('CostOfDevelopment=0 not rendered as currency', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication({ CostOfDevelopment: 0 })] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    await screen.findByText('DA-2024-001');
    expect(screen.queryByText(/Cost \$0/)).not.toBeInTheDocument();
  });

  it('falls back to ApplicationNumber when PlanningPortalApplicationNumber absent', async () => {
    const app = makeApplication({ PlanningPortalApplicationNumber: undefined, ApplicationNumber: 'CDC-2024-005' });
    mockSearchSuccess(makeSearchResult({ applications: [app] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    expect(await screen.findByText('CDC-2024-005')).toBeInTheDocument();
  });

  it('New search button resets results', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication()] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    await screen.findByText('DA-2024-001');
    fireEvent.click(screen.getByRole('button', { name: 'New search' }));
    expect(screen.queryByText('DA-2024-001')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Check nearby applications' })).toBeInTheDocument();
  });

  it('fires posthog threat_radar_search_complete with application count', async () => {
    mockSearchSuccess(makeSearchResult({ applications: [makeApplication()] }));
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check nearby applications' }));
    await screen.findAllByText(/1 application/);
    expect(mockCapture).toHaveBeenCalledWith('threat_radar_search_complete', expect.objectContaining({ application_count: 1 }));
  });
});

// ---------------------------------------------------------------------------
// Waitlist
// ---------------------------------------------------------------------------

describe('ThreatRadarTool — waitlist', () => {
  beforeEach(() => { mockFetch.mockReset(); mockCapture.mockReset(); });

  it('shows waitlist section with join button', () => {
    render(<ThreatRadarTool />);
    expect(screen.getByText(/Weekly DA monitoring — coming soon/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Join waitlist/i })).toBeInTheDocument();
  });

  it('waitlist join button enabled when email is filled', () => {
    render(<ThreatRadarTool />);
    fireEvent.change(screen.getByPlaceholderText('your@email.com'), { target: { value: 'user@example.com' } });
    expect(screen.getByRole('button', { name: /Join waitlist/i })).toBeEnabled();
  });
});
