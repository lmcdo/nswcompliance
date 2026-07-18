/**
 * Adversarial tests for BuilderReferralCard.
 * The dangerous failure modes: contact details passing WITHOUT consent, and
 * the referral payload losing the interest_type that separates
 * referral-consented rows from plain email-me rows.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const mockCapture = jest.fn();
jest.mock('posthog-js', () => ({
  __esModule: true,
  default: { capture: (...args: unknown[]) => mockCapture(...args) },
}));

import { BuilderReferralCard } from '@/components/tools/BuilderReferralCard';

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

const ADDR = '38 Park Rd, Bowral NSW 2576';

beforeEach(() => {
  mockFetch.mockReset();
  mockCapture.mockClear();
});

describe('BuilderReferralCard — consent gating', () => {
  it('submit button is disabled until consent is ticked', () => {
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    expect(screen.getByRole('button', { name: 'Request an intro' })).toBeDisabled();
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('button', { name: 'Request an intro' })).toBeEnabled();
  });

  it('never calls the lead API without consent', () => {
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'owner@example.com' },
    });
    fireEvent.submit(screen.getByRole('button', { name: 'Request an intro' }).closest('form')!);
    expect(mockFetch).not.toHaveBeenCalled();
    expect(screen.queryByText(/Request received/)).not.toBeInTheDocument();
  });

  it('renders the referral-fee disclosure before submit', () => {
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    expect(screen.getByText(/may receive a referral fee/)).toBeInTheDocument();
  });
});

describe('BuilderReferralCard — submit', () => {
  function fillAndSubmit() {
    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'owner@example.com' },
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Request an intro' }));
  }

  it('posts the referral interest_type with address, lga and eligible=true', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    fillAndSubmit();
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/canibuildit/lead');
    expect(JSON.parse(opts.body)).toEqual({
      email: 'owner@example.com',
      address: ADDR,
      eligible: true,
      lga_name: 'Wingecarribee',
      interest_type: 'dual-occ-referral',
    });
  });

  it('shows confirmation after submit', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    fillAndSubmit();
    await waitFor(() =>
      expect(screen.getByText(/Request received/)).toBeInTheDocument()
    );
  });

  it('still confirms when the API errors — capture must never block the result page', async () => {
    mockFetch.mockRejectedValueOnce(new Error('network down'));
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    fillAndSubmit();
    await waitFor(() =>
      expect(screen.getByText(/Request received/)).toBeInTheDocument()
    );
  });

  it('fires the funnel events: view on mount, submit on send', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    expect(mockCapture).toHaveBeenCalledWith('referral_cta_view', {
      tool: 'upzoning-check',
    });
    fillAndSubmit();
    await waitFor(() =>
      expect(mockCapture).toHaveBeenCalledWith('referral_lead_submitted', {
        tool: 'upzoning-check',
        lga: 'Wingecarribee',
      })
    );
  });
});

describe('BuilderReferralCard — null LGA', () => {
  it('renders generic area copy and posts null lga_name', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName={null} />);
    expect(screen.getByText(/in your area/)).toBeInTheDocument();
    fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
      target: { value: 'owner@example.com' },
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', { name: 'Request an intro' }));
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    expect(JSON.parse(mockFetch.mock.calls[0][1].body).lga_name).toBeNull();
  });
});
