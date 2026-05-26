/**
 * Adversarial tests for ShadowTool component.
 * Covers: form state machine, null-safety on result fields,
 * ADG badge logic, non-residential zone handling, PostHog capture.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ShadowTool } from '@/components/tools/ShadowTool';

// Prevent dynamic import of ShadowMap (requires DOM/mapbox)
jest.mock('next/dynamic', () => () => {
  const MockShadowMap = () => <div data-testid="shadow-map-mock" />;
  MockShadowMap.displayName = 'MockShadowMap';
  return MockShadowMap;
});

jest.mock('@/components/tools/OperationalTransparency', () => ({
  OperationalTransparency: ({ active, address, steps }: { active: boolean; address?: string; steps: { label: string }[]; note?: string }) =>
    active ? (
      <div data-testid="operational-transparency">
        <span>Analysing {address}...</span>
        {steps.map((s: { label: string }, i: number) => (
          <span key={i}>{s.label}</span>
        ))}
      </div>
    ) : null,
}));

jest.mock('@/components/reports/ToolCrossSell', () => ({
  ToolCrossSell: () => null,
}));

jest.mock('@/components/reports/WaitlistButton', () => ({
  WaitlistButton: () => null,
}));

// AddressAutocomplete — simple input passthrough for testing
jest.mock('@/components/reports/AddressAutocomplete', () => ({
  AddressAutocomplete: ({
    value,
    onChange,
    disabled,
    className,
  }: {
    value: string;
    onChange: (v: string) => void;
    disabled?: boolean;
    className?: string;
  }) => (
    <input
      data-testid="address-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={className}
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

function makeResult(overrides: Record<string, unknown> = {}) {
  return {
    address: '1 Smith St Surry Hills NSW 2010',
    lat: -33.88,
    lng: 151.21,
    run_date: '2024-06-21',
    zone: 'R2',
    confidence: 'high',
    data_sources: ['Planning Portal', 'Sentinel-2'],
    warnings: [],
    outputs: {
      height_m: 9.5,
      height_source: 'planning_portal',
      lep_name: 'Inner West LEP 2020',
      lot_polygon: null,
      north_proxy_polygon: null,
      worst_case_scenario: 'jun21_12pm',
      adg_compliant: true,
      construction_change_detected: false,
      construction_change_score: 0.042,
      scenarios: [
        {
          scenario: 'jun21_9am',
          label: '21 Jun 9am',
          date: '2024-06-21',
          time_local: '09:00',
          shadow_length_m: 12.3,
          shadow_overlap_fraction: 0.15,
          shadow_direction_deg: 180,
          overlaps_subject_lot: false,
          shadow_on_lot: null,
          shadow_polygon: null,
        },
        {
          scenario: 'jun21_12pm',
          label: '21 Jun 12pm',
          date: '2024-06-21',
          time_local: '12:00',
          shadow_length_m: 8.1,
          shadow_overlap_fraction: 0.72,
          shadow_direction_deg: 0,
          overlaps_subject_lot: true,
          shadow_on_lot: null,
          shadow_polygon: null,
        },
      ],
    },
    ...overrides,
  };
}

function mockSuccessFetch(result = makeResult()) {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => result,
  });
}

function mockErrorFetch(message: string) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({ error: message }),
  });
}

// ---------------------------------------------------------------------------
// Idle state
// ---------------------------------------------------------------------------

describe('ShadowTool — idle state', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockCapture.mockReset();
  });

  it('renders form with Analyse button', () => {
    render(<ShadowTool />);
    expect(screen.getByRole('button', { name: 'Analyse' })).toBeInTheDocument();
  });

  it('Analyse button disabled when address is empty', () => {
    render(<ShadowTool />);
    expect(screen.getByRole('button', { name: 'Analyse' })).toBeDisabled();
  });

  it('Analyse button enabled when address is typed', () => {
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    expect(screen.getByRole('button', { name: 'Analyse' })).toBeEnabled();
  });
});

// ---------------------------------------------------------------------------
// Running state
// ---------------------------------------------------------------------------

describe('ShadowTool — running state', () => {
  beforeEach(() => mockFetch.mockReset());

  it('shows operational transparency steps while analysing', async () => {
    mockFetch.mockReturnValue(new Promise(() => {})); // never resolves
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    // OperationalTransparency shows "Analysing {address}..." and step labels
    expect(await screen.findByText(/Analysing 1 Smith St/)).toBeInTheDocument();
    expect(screen.getByText('Calculating sun angles across 5 ADG scenarios…')).toBeInTheDocument();
  });

  it('fires posthog shadow_tool_run on submit', async () => {
    mockFetch.mockReturnValue(new Promise(() => {}));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '42 Test Rd' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    await waitFor(() => expect(mockCapture).toHaveBeenCalledWith('shadow_tool_run', expect.objectContaining({ address: '42 Test Rd' })));
  });
});

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

describe('ShadowTool — error state', () => {
  beforeEach(() => mockFetch.mockReset());

  it('shows API error message on failure', async () => {
    mockErrorFetch('No lot found for this address');
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText('No lot found for this address')).toBeInTheDocument();
  });

  it('shows generic error when fetch rejects entirely', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network failure'));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText('Network failure')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Complete state — ShadowCard rendering
// ---------------------------------------------------------------------------

describe('ShadowTool — complete state (ShadowCard)', () => {
  beforeEach(() => mockFetch.mockReset());

  it('shows address in card header', async () => {
    mockSuccessFetch();
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText('1 Smith St Surry Hills NSW 2010')).toBeInTheDocument();
  });

  it('ADG compliant result shows green badge', async () => {
    mockSuccessFetch(makeResult({ zone: 'R2' }));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    const badge = await screen.findByText('Meets ADG solar access test');
    expect(badge).toHaveClass('text-green-800');
  });

  it('ADG concern result shows red badge', async () => {
    const result = makeResult();
    result.outputs.adg_compliant = false;
    mockSuccessFetch(result);
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    const badge = await screen.findByText('ADG solar access concern');
    expect(badge).toHaveClass('text-red-800');
  });

  it('non-residential zone shows indicative badge regardless of adg_compliant', async () => {
    const result = makeResult({ zone: 'B2' });
    result.outputs.adg_compliant = false;
    mockSuccessFetch(result);
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    const badge = await screen.findByText('Indicative only');
    expect(badge).toHaveClass('text-gray-600');
  });

  it('E (employment) zone prefix treated as non-residential', async () => {
    mockSuccessFetch(makeResult({ zone: 'E2' }));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText('Indicative only')).toBeInTheDocument();
  });

  it('null run_date does not crash — renders empty string', async () => {
    mockSuccessFetch(makeResult({ run_date: null }));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    // Should render the card without throwing
    expect(await screen.findByText('1 Smith St Surry Hills NSW 2010')).toBeInTheDocument();
  });

  it('null zone does not crash — defaults to residential path', async () => {
    mockSuccessFetch(makeResult({ zone: null }));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    // Card renders; no non-residential override
    expect(await screen.findByText('Meets ADG solar access test')).toBeInTheDocument();
  });

  it('worst-case scenario label is shown in map overlay and locked preview', async () => {
    mockSuccessFetch();
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    await screen.findByText('1 Smith St Surry Hills NSW 2010');
    // The worst-case scenario (jun21_12pm) appears in map overlay and locked preview
    expect(screen.getAllByText('21 Jun — 12:00 pm').length).toBeGreaterThanOrEqual(1);
  });

  it('null construction_change_score does not crash', async () => {
    const result = makeResult();
    result.outputs.construction_change_score = null;
    mockSuccessFetch(result);
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    await screen.findByText('1 Smith St Surry Hills NSW 2010');
    expect(screen.queryByText(/toFixed/)).not.toBeInTheDocument();
  });

  it('height_source=default shows amber warning', async () => {
    const result = makeResult();
    result.outputs.height_source = 'default';
    mockSuccessFetch(result);
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText(/No specific height control found/)).toBeInTheDocument();
  });

  it('empty scenarios array does not crash', async () => {
    const result = makeResult();
    result.outputs.scenarios = [];
    mockSuccessFetch(result);
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText('1 Smith St Surry Hills NSW 2010')).toBeInTheDocument();
  });

  it('warning messages are shown when present', async () => {
    mockSuccessFetch(makeResult({ warnings: ['Height limit defaulted — no LEP data'] }));
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    expect(await screen.findByText('Height limit defaulted — no LEP data')).toBeInTheDocument();
  });

  it('fires posthog shadow_tool_complete with adg_compliant', async () => {
    mockSuccessFetch();
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    await screen.findByText('1 Smith St Surry Hills NSW 2010');
    expect(mockCapture).toHaveBeenCalledWith('shadow_tool_complete', expect.objectContaining({ adg_compliant: true }));
  });

  it('scenario with null shadow_overlap_fraction does not crash', async () => {
    const result = makeResult();
    result.outputs.scenarios[0].shadow_overlap_fraction = null as unknown as number;
    mockSuccessFetch(result);
    render(<ShadowTool />);
    fireEvent.change(screen.getByTestId('address-input'), { target: { value: '1 Smith St' } });
    fireEvent.click(screen.getByRole('button', { name: 'Analyse' }));
    // Should render the card without throwing
    expect(await screen.findByText('1 Smith St Surry Hills NSW 2010')).toBeInTheDocument();
  });
});
