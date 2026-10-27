/**
 * WaitlistButton variant="email-result": the offer that unlocks on-screen numbers.
 * onSuccess must fire only after the lead is stored — a failed request must not
 * unlock (or the email gate collects nothing and nobody notices).
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

jest.mock('posthog-js', () => ({ __esModule: true, default: { capture: jest.fn() } }));

import posthog from 'posthog-js';
import { WaitlistButton } from '@/components/reports/WaitlistButton';

const fetchMock = jest.fn();
beforeEach(() => {
  jest.clearAllMocks();
  global.fetch = fetchMock as unknown as typeof fetch;
});

function submit(email = 'owner@example.com') {
  fireEvent.change(screen.getByPlaceholderText('your@email.com'), { target: { value: email } });
  fireEvent.click(screen.getByRole('button'));
}

it('sends the consent wording shown and unlocks on success', async () => {
  fetchMock.mockResolvedValue({ ok: true, json: async () => ({ ok: true }) });
  const onSuccess = jest.fn();
  render(<WaitlistButton interestType="flood-truth" address="1 A St" variant="email-result" onSuccess={onSuccess} />);
  const shown = screen.getByText(/Email me a link to this result/).textContent;
  submit();
  await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  const body = JSON.parse(fetchMock.mock.calls[0][1].body);
  expect(body.consent_wording).toBe(shown);
  expect(body.consent_version).toBeTruthy();
  // conversion event carries no PII
  expect(posthog.capture).toHaveBeenCalledWith('lead_submitted', { interest_type: 'flood-truth', variant: 'email-result' });
  expect(JSON.stringify((posthog.capture as jest.Mock).mock.calls)).not.toContain('owner@example.com');
});

it('does not unlock when the server rejects the lead', async () => {
  fetchMock.mockResolvedValue({ ok: false, json: async () => ({ error: 'Please use a valid email address.' }) });
  const onSuccess = jest.fn();
  render(<WaitlistButton interestType="flood-truth" variant="email-result" onSuccess={onSuccess} />);
  submit();
  expect(await screen.findByText('Please use a valid email address.')).toBeInTheDocument();
  expect(onSuccess).not.toHaveBeenCalled();
  expect(posthog.capture).not.toHaveBeenCalled();
});

it('keeps the waitlist copy by default', () => {
  render(<WaitlistButton interestType="solar" />);
  expect(screen.getByRole('button')).toHaveTextContent('Join waitlist');
  expect(screen.getByText(/Paid reports launching soon/)).toBeInTheDocument();
});
