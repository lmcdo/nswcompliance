/**
 * Regression tests for granny flat email capture state split.
 *
 * Key invariant (the bug we fixed):
 *   Entering email at the idle address-input step must NOT pre-submit the
 *   post-result CTA (reportEmailCaptured). The post-result form must always
 *   render explicitly so the user actively opts in after seeing the result.
 *
 * Tests use the ineligible path (no polling required) to reach a result state
 * fast. The same reportEmailCaptured state is used on complete state too.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// GrannyFlatPage wraps GrannyFlatPageInner in Suspense — import via default
import GrannyFlatPage from '@/app/reports/granny-flat/page';

// ---- mocks ----

jest.mock('next/navigation', () => ({
  useSearchParams: () => ({ get: () => null }),
}));

jest.mock('react-map-gl/maplibre', () => ({
  __esModule: true,
  default: ({ children }: { children?: React.ReactNode }) => <div data-testid="map-mock">{children}</div>,
  Source: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
  Layer: () => null,
  NavigationControl: () => null,
}));

jest.mock('@/components/reports/AddressAutocomplete', () => ({
  AddressAutocomplete: ({
    value,
    onChange,
    disabled,
  }: {
    value: string;
    onChange: (v: string) => void;
    onSelect: (v: string) => void;
    disabled?: boolean;
  }) => (
    <input
      data-testid="address-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
    />
  ),
}));

jest.mock('@/components/providers/PostHogProvider', () => ({
  posthog: { capture: jest.fn() },
}));

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

// Ineligible detect response — returns immediately, no polling needed
function mockIneligibleDetect(reason = 'This property is not in a residential zone.') {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    json: async () => ({
      ineligible: true,
      error: reason,
      evidence: 'B4 — Mixed Use',
      evidence_label: 'Zone',
    }),
  });
}

// Lead API response
function mockLeadApi() {
  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: async () => ({ ok: true }),
  });
}

beforeEach(() => mockFetch.mockReset());

// ---------------------------------------------------------------------------
// Core regression: idle email must NOT pre-submit post-result CTA
// ---------------------------------------------------------------------------

describe('GrannyFlat email capture — idle email does not pre-submit CTA', () => {
  it('post-result Notify me form is shown even when email was entered at idle', async () => {
    mockIneligibleDetect();
    render(<GrannyFlatPage />);

    // Enter email BEFORE running detect (idle state)
    const emailInput = screen.getByPlaceholderText('your@email.com');
    fireEvent.change(emailInput, { target: { value: 'early@test.com' } });

    // Run detect
    fireEvent.change(screen.getByTestId('address-input'), {
      target: { value: '5 Commercial Rd Haberfield NSW 2045' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Detect structures' }));

    // Wait for ineligible result
    await screen.findByText('Not eligible');

    // The "What could change this?" section should show the form, not the confirmation
    // (regression: previously emailSubmitted=true here caused confirmation to show immediately)
    expect(screen.getByRole('button', { name: 'Notify me' })).toBeInTheDocument();
    expect(screen.queryByText(/Got it — we'll be in touch/)).not.toBeInTheDocument();
  });

  it('email field in post-result form is pre-filled with idle email', async () => {
    mockIneligibleDetect();
    render(<GrannyFlatPage />);

    // Enter email at idle
    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'prefilled@test.com' },
    });

    fireEvent.change(screen.getByTestId('address-input'), {
      target: { value: '5 Commercial Rd Haberfield NSW 2045' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Detect structures' }));

    await screen.findByText('Not eligible');

    // Email field should still be present and pre-filled
    const notifyEmailInput = screen.getByPlaceholderText('your@email.com');
    expect((notifyEmailInput as HTMLInputElement).value).toBe('prefilled@test.com');
  });
});

// ---------------------------------------------------------------------------
// Post-result form submits to lead API with eligible=null (ineligible path)
// ---------------------------------------------------------------------------

describe('GrannyFlat email capture — post-result form submission', () => {
  it('submitting post-result form calls lead API and shows confirmation', async () => {
    mockIneligibleDetect();
    mockLeadApi(); // lead API call from detect (idle email)
    mockLeadApi(); // lead API call from post-result submit
    render(<GrannyFlatPage />);

    fireEvent.change(screen.getByTestId('address-input'), {
      target: { value: '5 Commercial Rd Haberfield NSW 2045' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Detect structures' }));

    await screen.findByText('Not eligible');

    // Enter email in the post-result form
    const emailInput = screen.getByPlaceholderText('your@email.com');
    fireEvent.change(emailInput, { target: { value: 'notify@test.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Notify me' }));

    // Confirmation should appear
    expect(await screen.findByText(/Got it — we'll be in touch if anything changes/)).toBeInTheDocument();

    // Form should be gone
    expect(screen.queryByRole('button', { name: 'Notify me' })).not.toBeInTheDocument();
  });

  it('submitting post-result form twice does not submit twice — confirmation replaces form', async () => {
    mockIneligibleDetect();
    mockLeadApi();
    render(<GrannyFlatPage />);

    fireEvent.change(screen.getByTestId('address-input'), {
      target: { value: '5 Commercial Rd Haberfield NSW 2045' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Detect structures' }));

    await screen.findByText('Not eligible');

    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'double@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Notify me' }));

    // After first submit, button is gone — can't submit twice
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Notify me' })).not.toBeInTheDocument()
    );
  });
});

// ---------------------------------------------------------------------------
// Reset clears reportEmailCaptured
// ---------------------------------------------------------------------------

describe('GrannyFlat email capture — reset behaviour', () => {
  it('searching another address resets the post-result form', async () => {
    mockIneligibleDetect();
    mockLeadApi();
    render(<GrannyFlatPage />);

    fireEvent.change(screen.getByTestId('address-input'), {
      target: { value: '5 Commercial Rd Haberfield NSW 2045' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Detect structures' }));

    await screen.findByText('Not eligible');

    // Submit post-result form
    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'reset@test.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Notify me' }));
    await screen.findByText(/Got it — we'll be in touch/);

    // Click "Search another address"
    fireEvent.click(screen.getByRole('button', { name: 'Search another address' }));

    // Back to idle — email strip no longer showing
    expect(screen.queryByText(/Got it — we'll be in touch/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Detect structures' })).toBeInTheDocument();
  });
});
