/**
 * FeedbackWidget — the panel's intro line must branch on the cohort tag.
 *
 * A tagged visitor is a student. The professional intro ("certifiers and
 * planners") told them they were in the wrong place, while every other cue —
 * button label, tag, panel title, role default — had already switched. This
 * pins that line to the same condition as the rest, in both directions, so a
 * future copy edit cannot silently restore the mismatch.
 *
 * The cohort is seeded through localStorage rather than by mocking getCohort,
 * so the real reader in lib/cohort.ts is exercised.
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';

jest.mock('next/navigation', () => ({
  usePathname: () => '/assessment',
}));

const PROFESSIONAL = /As a professional user/i;
const STUDENT = /two most useful reports/i;

function openPanel() {
  fireEvent.click(screen.getByRole('button', { name: /open feedback panel/i }));
}

describe('FeedbackWidget intro copy', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('uses the professional intro when no cohort is tagged', () => {
    render(<FeedbackWidget />);
    openPanel();

    expect(screen.getByText(PROFESSIONAL)).toBeInTheDocument();
    expect(screen.queryByText(STUDENT)).not.toBeInTheDocument();
  });

  it('uses the student intro when a cohort is tagged', () => {
    window.localStorage.setItem('pd.cohort', 'uts-16658');
    render(<FeedbackWidget />);
    openPanel();

    expect(screen.getByText(STUDENT)).toBeInTheDocument();
    expect(screen.queryByText(PROFESSIONAL)).not.toBeInTheDocument();
  });

  it('names the two reports the student brief asks for', () => {
    window.localStorage.setItem('pd.cohort', 'uts-16658');
    render(<FeedbackWidget />);
    openPanel();

    // A missing control and a mismatched number are the two findings the
    // exercise exists to collect; generic "send us feedback" copy does not
    // produce them.
    const intro = screen.getByText(STUDENT).textContent ?? '';
    expect(intro).toMatch(/control missing/i);
    expect(intro).toMatch(/does not match the DCP/i);
  });

  it('rejects a cohort code too short to be valid, and stays professional', () => {
    // Guards the copy branch against the validator: '1' fails lib/cohort.ts,
    // so the widget must fall back rather than render an untagged student view.
    window.localStorage.setItem('pd.cohort', '1');
    render(<FeedbackWidget />);
    openPanel();

    expect(screen.getByText(PROFESSIONAL)).toBeInTheDocument();
    expect(screen.queryByText(STUDENT)).not.toBeInTheDocument();
  });
});
