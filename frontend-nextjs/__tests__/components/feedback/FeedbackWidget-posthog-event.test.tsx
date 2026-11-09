/**
 * FeedbackWidget — sends one PostHog event when feedback is saved, with the kind of feedback only.
 * The pilot needs to count how many testers send feedback; the text, the email and the address stay in user_feedback, never in analytics.
 * prior-art-checked: FeedbackWidget-cohort-copy.test.tsx covers the intro copy; nothing covered the submit path or analytics.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';

const capture = jest.fn();
jest.mock('@/components/providers/PostHogProvider', () => ({ posthog: { capture: (...a: unknown[]) => capture(...a) } }));
jest.mock('next/navigation', () => ({ usePathname: () => '/assessment' }));

function fillAndSubmit(text = 'The front setback on 12 Example Street looks wrong', email = 'tester@example.com') {
  fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
  fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: text } });
  const mail = screen.queryByPlaceholderText(/your\.email@example\.com/i);
  if (mail && email) fireEvent.change(mail, { target: { value: email } });
  fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
}

describe('FeedbackWidget analytics event', () => {
  beforeEach(() => {
    capture.mockClear();
    window.localStorage.clear();
  });
  afterEach(() => { (global as any).fetch = undefined; });

  it('sends feedback_submitted once when the save succeeds', async () => {
    (global as any).fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    render(<FeedbackWidget propertyAddress="12 Example Street, Hornsby NSW" />);
    fillAndSubmit();
    await waitFor(() => expect(capture).toHaveBeenCalledTimes(1));
    expect(capture.mock.calls[0][0]).toBe('feedback_submitted');
  });

  it('carries only the kind, never the text, the email or the address', async () => {
    (global as any).fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    render(<FeedbackWidget propertyAddress="12 Example Street, Hornsby NSW" />);
    fillAndSubmit();
    await waitFor(() => expect(capture).toHaveBeenCalled());
    const props = capture.mock.calls[0][1];
    expect(Object.keys(props).sort()).toEqual(['cohort', 'feedback_type', 'has_email', 'page', 'user_type']);
    const flat = JSON.stringify(props);
    expect(flat).not.toMatch(/setback|tester@example|Example Street|Hornsby/);
    expect(props.has_email).toBe(true);
  });

  it('records has_email false when no email is given', async () => {
    (global as any).fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    render(<FeedbackWidget />);
    fillAndSubmit('A note', '');
    await waitFor(() => expect(capture).toHaveBeenCalled());
    expect(capture.mock.calls[0][1].has_email).toBe(false);
  });

  it('sends nothing when the save fails (a 500 is not a submission)', async () => {
    (global as any).fetch = jest.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<FeedbackWidget />);
    fillAndSubmit();
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalled());
    await new Promise((r) => setTimeout(r, 20));
    expect(capture).not.toHaveBeenCalled();
  });

  it('sends nothing when the request itself throws', async () => {
    (global as any).fetch = jest.fn().mockRejectedValue(new Error('offline'));
    render(<FeedbackWidget />);
    fillAndSubmit();
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalled());
    await new Promise((r) => setTimeout(r, 20));
    expect(capture).not.toHaveBeenCalled();
  });
});
