/**
 * /tools/upzoning-check (the LMR and TOD tool) — the feedback prompt and the form it opens, on the real page.
 * The risk this guards: the page shows the prompt but nothing is mounted to open, so a click counts and then nothing
 * happens, and no one notices from the code. Here the real page is rendered, a result is loaded, and the prompt is clicked.
 * prior-art-checked: no test rendered this page before (only BuilderReferralCard has one); FeedbackPrompt.test.tsx
 * covers the prompt and the widget together, but not this page's mounting of them.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import UpzoningCheckPage from '@/app/tools/upzoning-check/page';

const capture = jest.fn();
jest.mock('posthog-js', () => ({ __esModule: true, default: { capture: (...a: unknown[]) => capture(...a) } }));
jest.mock('@/components/providers/PostHogProvider', () => ({ posthog: { capture: (...a: unknown[]) => capture(...a) } }));
jest.mock('next/navigation', () => ({ usePathname: () => '/tools/upzoning-check' }));
jest.mock('@/components/marketing/SiteNav', () => ({ SiteNav: () => null }));
jest.mock('@/components/marketing/SiteFooter', () => ({ SiteFooter: () => null }));
jest.mock('@/components/property/PropertySearch', () => ({
  PropertySearch: ({ onAddressSelect }: { onAddressSelect: (address: string) => void }) => (
    <>
      <button onClick={() => onAddressSelect('12 Example Street, Hornsby NSW')}>pick address</button>
      <button onClick={() => onAddressSelect('34 Other Road, Epping NSW')}>pick other address</button>
    </>
  ),
}));

const ADDRESS = '12 Example Street, Hornsby NSW';
const realFetch = (global as any).fetch;

// A data outage is the smallest result the page renders; the prompt must still show, because "this page did not
// tell me" matters most when the page could not answer.
const OUTAGE = {
  status: 'unavailable',
  address: ADDRESS,
  zone: null,
  zone_epi: null,
  zone_full: null,
  legislation_url: null,
  lot_area_m2: null,
  lot_width_m: null,
  lot_type: null,
  lga_name: null,
  forms: [],
  gates: { in_lmr_area: false, in_tod: false, dual_occ_prohibited: false },
  heritage: { flag: false, items: [], hca: [] },
};

function mockNetwork() {
  (global as any).fetch = jest.fn().mockImplementation((url: string, init?: { body?: string }) => {
    if (String(url).includes('/api/upzoning')) {
      // Echo the address asked about, as the real endpoint does.
      const address = init?.body ? JSON.parse(init.body).address : ADDRESS;
      return Promise.resolve({ ok: true, json: async () => ({ ...OUTAGE, address }) });
    }
    return Promise.resolve({ ok: true, json: async () => ({}) });
  });
}

function feedbackCall(): any | undefined {
  const calls = ((global as any).fetch as jest.Mock).mock.calls.filter((c) => String(c[0]) === '/api/feedback');
  return calls.length ? JSON.parse(calls[0][1].body) : undefined;
}

describe('/tools/upzoning-check feedback prompt', () => {
  beforeEach(() => {
    capture.mockClear();
    window.localStorage.clear();
    mockNetwork();
  });
  afterEach(() => {
    (global as any).fetch = realFetch;
  });

  it('shows no prompt and no floating button before an address is checked', () => {
    render(<UpzoningCheckPage />);
    expect(screen.queryByTestId('feedback-prompt')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /open feedback panel/i })).not.toBeInTheDocument();
  });

  it('shows the prompt once a result is loaded, and still adds no floating button to the public page', async () => {
    render(<UpzoningCheckPage />);
    fireEvent.click(screen.getByRole('button', { name: /pick address/i }));
    expect(await screen.findByTestId('feedback-prompt')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /open feedback panel/i })).not.toBeInTheDocument();
  });

  it('opens the form from the prompt, with Feature Request chosen and the address in the context', async () => {
    render(<UpzoningCheckPage />);
    fireEvent.click(screen.getByRole('button', { name: /pick address/i }));
    fireEvent.click(await screen.findByRole('button', { name: /tell us what you were looking for/i }));
    expect(screen.getByPlaceholderText(/describe your feedback/i)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /feature request/i })).toBeChecked();
    // Once in the page header and once in the form's own context box.
    expect(screen.getAllByText(/12 Example Street/)).toHaveLength(2);
  });

  it('saves the message with the page named in the first line and the address in the context', async () => {
    render(<UpzoningCheckPage />);
    fireEvent.click(screen.getByRole('button', { name: /pick address/i }));
    fireEvent.click(await screen.findByRole('button', { name: /tell us what you were looking for/i }));
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'I wanted the height limit' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect(feedbackCall()).toBeDefined());
    const body = feedbackCall();
    expect(body.feedbackText).toBe('[From: Upzoning Check (LMR and TOD) page]\nI wanted the height limit');
    expect(body.feedbackType).toBe('feature_request');
    expect(body.context.propertyAddress).toBe(ADDRESS);
    expect(body.context.page).toBe('/tools/upzoning-check');
  });

  it('does not carry a draft written for one address onto the next address checked', async () => {
    // Found by the pre-push cross-review: the form is mounted at the foot of the page, so it outlived the result.
    render(<UpzoningCheckPage />);
    fireEvent.click(screen.getByRole('button', { name: /pick address/i }));
    fireEvent.click(await screen.findByRole('button', { name: /tell us what you were looking for/i }));
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'About the first address' } });

    fireEvent.click(screen.getByRole('button', { name: /pick other address/i }));
    // The first draft is gone with its address: the form is closed and nothing of it is left to submit.
    await waitFor(() => expect(screen.getAllByText(/34 Other Road/).length).toBeGreaterThan(0));
    expect(screen.queryByPlaceholderText(/describe your feedback/i)).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole('button', { name: /tell us what you were looking for/i }));
    expect(screen.getByPlaceholderText(/describe your feedback/i)).toHaveValue('');
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'About the second address' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect(feedbackCall()).toBeDefined());
    const body = feedbackCall();
    expect(body.feedbackText).toBe('[From: Upzoning Check (LMR and TOD) page]\nAbout the second address');
    expect(body.context.propertyAddress).toBe('34 Other Road, Epping NSW');
  });

  it('counts the click on its own with the page name', async () => {
    render(<UpzoningCheckPage />);
    fireEvent.click(screen.getByRole('button', { name: /pick address/i }));
    fireEvent.click(await screen.findByRole('button', { name: /tell us what you were looking for/i }));
    expect(capture).toHaveBeenCalledWith('feedback_prompt_clicked', { tab: 'upzoning' });
  });
});
