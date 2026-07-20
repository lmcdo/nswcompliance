/**
 * Adversarial tests for the multi-step BuilderReferralCard qualifier.
 * Dangerous failure modes guarded here: contact details passing WITHOUT
 * consent; the payload losing interest_type / qualification; and — the one that
 * bit us — a FAILED submit being shown as a success (false confirmation that
 * silently loses the lead).
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

const mockCapture = jest.fn();
jest.mock('posthog-js', () => ({
  __esModule: true,
  default: { capture: (...args: unknown[]) => mockCapture(...args) },
}));
// The card fires a Google Ads conversion on success; stub it (no-op in tests).
jest.mock('@/lib/gtag', () => ({
  __esModule: true,
  trackAdsConversion: jest.fn(),
  loadGoogleAds: jest.fn(),
}));

import { BuilderReferralCard } from '@/components/tools/BuilderReferralCard';

global.fetch = jest.fn();
const mockFetch = global.fetch as jest.Mock;

const ADDR = '38 Park Rd, Bowral NSW 2576';

beforeEach(() => {
  mockFetch.mockReset();
  mockCapture.mockClear();
});

// The qualifier is 3 steps: timeline -> ownership -> contact. Tap through the
// two select questions to reach the contact form.
function advanceToContact() {
  fireEvent.click(screen.getByRole('button', { name: 'As soon as possible' }));
  fireEvent.click(screen.getByRole('button', { name: 'I own it' }));
}

function fillContactAndSubmit() {
  fireEvent.change(screen.getByPlaceholderText('you@email.com'), {
    target: { value: 'owner@example.com' },
  });
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: /Request my duplex builder intro/ }));
}

describe('BuilderReferralCard — consent gating', () => {
  it('does not call the lead API when submitted without consent', () => {
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    advanceToContact();
    fireEvent.change(screen.getByPlaceholderText('you@email.com'), {
      target: { value: 'owner@example.com' },
    });
    // submit with an email but the consent box left un-ticked
    fireEvent.click(screen.getByRole('button', { name: /Request my duplex builder intro/ }));
    expect(mockFetch).not.toHaveBeenCalled();
    // Match a phrase unique to the consent ERROR - "tick the box" also appears in
    // the standing helper text below the checkbox, so it matches two elements.
    expect(screen.getByText(/pass your details to the builder/)).toBeInTheDocument();
  });

  it('renders the referral-fee disclosure on the contact step', () => {
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    advanceToContact();
    expect(screen.getByText(/may receive a referral fee/)).toBeInTheDocument();
  });
});

describe('BuilderReferralCard — submit', () => {
  it('posts the referral interest_type + qualification with address, lga and eligible=true', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    advanceToContact();
    fillContactAndSubmit();
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/canibuildit/lead');
    const body = JSON.parse(opts.body);
    expect(body).toMatchObject({
      email: 'owner@example.com',
      address: ADDR,
      eligible: true,
      lga_name: 'Wingecarribee',
      interest_type: 'dual-occ-referral',
    });
    expect(body.qualification).toMatchObject({ timeline: 'asap', ownership: 'owner' });
    expect(body.consent_wording).toMatch(/may receive a referral fee/);
  });

  it('shows the confirmation after a successful submit', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    advanceToContact();
    fillContactAndSubmit();
    await waitFor(() => expect(screen.getByText(/got your request/)).toBeInTheDocument());
  });

  it('shows an error and NOT a confirmation when the API returns non-ok', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    advanceToContact();
    fillContactAndSubmit();
    await waitFor(() =>
      expect(screen.getByText(/Something went wrong sending that/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/got your request/)).not.toBeInTheDocument();
  });

  it('shows an error and NOT a confirmation when the fetch rejects', async () => {
    mockFetch.mockRejectedValueOnce(new Error('network down'));
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    advanceToContact();
    fillContactAndSubmit();
    await waitFor(() =>
      expect(screen.getByText(/Something went wrong sending that/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/got your request/)).not.toBeInTheDocument();
  });

  it('fires the funnel events: view on mount, submit on send', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName="Wingecarribee" />);
    expect(mockCapture).toHaveBeenCalledWith('referral_cta_view', {
      tool: 'upzoning-check',
      verdict: 'eligible',
    });
    advanceToContact();
    fillContactAndSubmit();
    await waitFor(() =>
      expect(mockCapture).toHaveBeenCalledWith(
        'referral_lead_submitted',
        expect.objectContaining({
          tool: 'upzoning-check',
          lga: 'Wingecarribee',
          verdict: 'eligible',
          timeline: 'asap',
          ownership: 'owner',
        }),
      ),
    );
  });
});

describe('BuilderReferralCard — null LGA', () => {
  it('posts null lga_name', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) });
    render(<BuilderReferralCard address={ADDR} lgaName={null} />);
    advanceToContact();
    fillContactAndSubmit();
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));
    expect(JSON.parse(mockFetch.mock.calls[0][1].body).lga_name).toBeNull();
  });
});
