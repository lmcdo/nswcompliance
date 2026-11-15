/**
 * FeedbackPrompt — a visible entry point that opens the existing FeedbackWidget.
 * The point of these tests: it opens the SAME form, records the tab, counts the click on its own, and changes nothing
 * for someone who uses the floating button.
 * prior-art-checked: FeedbackWidget-posthog-event.test.tsx covers the widget's own analytics event; none covered an
 * inline entry point.
 */
import React from 'react';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';
import FeedbackPrompt from '@/components/feedback/FeedbackPrompt';

const capture = jest.fn();
jest.mock('@/components/providers/PostHogProvider', () => ({ posthog: { capture: (...a: unknown[]) => capture(...a) } }));
jest.mock('next/navigation', () => ({ usePathname: () => '/assessment' }));

const realFetch = (global as any).fetch;

function mount(tab = 'sepp') {
  return render(
    <>
      <FeedbackPrompt tab={tab} />
      <FeedbackWidget propertyAddress="12 Example Street, Hornsby NSW" />
    </>,
  );
}

function postedBody(): any {
  return JSON.parse(((global as any).fetch as jest.Mock).mock.calls[0][1].body);
}

describe('FeedbackPrompt', () => {
  beforeEach(() => {
    capture.mockClear();
    window.localStorage.clear();
    (global as any).fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
  });
  afterEach(() => {
    (global as any).fetch = realFetch;
  });

  it('opens the existing feedback form with "Feature Request" selected', () => {
    mount();
    expect(screen.queryByPlaceholderText(/describe your feedback/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    expect(screen.getByPlaceholderText(/describe your feedback/i)).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /feature request/i })).toBeChecked();
  });

  it('counts the click on its own, with the tab and nothing else', () => {
    mount('lep');
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    expect(capture).toHaveBeenCalledWith('feedback_prompt_clicked', { tab: 'lep' });
    expect(Object.keys(capture.mock.calls[0][1])).toEqual(['tab']);
  });

  it('still opens the form when analytics throws', () => {
    capture.mockImplementationOnce(() => {
      throw new Error('posthog down');
    });
    mount();
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    expect(screen.getByPlaceholderText(/describe your feedback/i)).toBeInTheDocument();
  });

  it('writes the tab into the stored message when opened from the prompt', async () => {
    mount('sepp');
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'I wanted the heritage status' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(1));
    const body = postedBody();
    expect(body.feedbackText).toBe('[From: SEPP tab]\nI wanted the heritage status');
    expect(body.feedbackType).toBe('feature_request');
  });

  it('sends a new role as "other" and records it in the text', async () => {
    mount('dcp');
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'builder' } });
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'Need the rear setback' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(1));
    const body = postedBody();
    expect(body.userType).toBe('other');
    expect(body.feedbackText).toBe('[From: DCP Provisions tab | Role: Builder]\nNeed the rear setback');
  });

  it('keeps an existing role in user_type and does not repeat it in the text', async () => {
    mount('sepp');
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'town_planner' } });
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'A note' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(1));
    const body = postedBody();
    expect(body.userType).toBe('town_planner');
    expect(body.feedbackText).toBe('[From: SEPP tab]\nA note');
  });

  it('changes nothing for the floating button: no tab line, default role, general type', async () => {
    mount();
    fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'Plain note' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(1));
    const body = postedBody();
    expect(body.feedbackText).toBe('Plain note');
    expect(body.userType).toBe('certifier');
    expect(body.feedbackType).toBe('general');
  });

  it('does not carry the tab into the next submission after a save', async () => {
    jest.useFakeTimers();
    try {
      mount('lep');
      fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
      fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'First' } });
      fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
      await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(1));
      await waitFor(() => expect(screen.getByText(/thank you/i)).toBeInTheDocument());
      await act(async () => {
        jest.advanceTimersByTime(3500); // the widget closes and resets itself after 3 seconds
      });
      fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
      fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'Second' } });
      fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
      await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(2));
      const second = JSON.parse(((global as any).fetch as jest.Mock).mock.calls[1][1].body);
      expect(second.feedbackText).toBe('Second');
    } finally {
      jest.useRealTimers();
    }
  });

  it('does not carry the tab or the feature-request type when the form is closed unsent and reopened from the floating button', async () => {
    // Found by the pre-push cross-review: only a successful save cleared them, so closing with the X left both behind.
    mount('lep');
    fireEvent.click(screen.getByRole('button', { name: /tell us what you were looking for/i }));
    expect(screen.getByRole('radio', { name: /feature request/i })).toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: /close feedback panel/i }));
    fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
    expect(screen.getByRole('radio', { name: /general comment/i })).toBeChecked();
    fireEvent.change(screen.getByPlaceholderText(/describe your feedback/i), { target: { value: 'A general message' } });
    fireEvent.submit(screen.getByPlaceholderText(/describe your feedback/i).closest('form')!);
    await waitFor(() => expect((global as any).fetch).toHaveBeenCalledTimes(1));
    const body = postedBody();
    expect(body.feedbackText).toBe('A general message');
    expect(body.feedbackType).toBe('general');
  });

  it('keeps what the user chose when they close and reopen a form that did not come from the prompt', () => {
    mount();
    fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
    fireEvent.click(screen.getByRole('radio', { name: /bug report/i }));
    fireEvent.click(screen.getByRole('button', { name: /close feedback panel/i }));
    fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
    expect(screen.getByRole('radio', { name: /bug report/i })).toBeChecked();
  });

  it('uses no liability wording in its own copy (pre-pr-review check 5)', () => {
    mount();
    const copy = screen.getByTestId('feedback-prompt').textContent ?? '';
    // One line on purpose: the scanner skips any line containing expect(, which is how a list of banned words can sit in a test.
    expect(copy).not.toMatch(/\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|guaranteed|certified|confirmed|verified|ensure|assure|accurate|definitive|comprehensive|reliable)\b/i);
  });
});
