/**
 * The evidence page prints every source with its own state: an unreadable source says so, it is never shown as empty or clear.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

let params = 'lat=-33.75&lng=150.70';
jest.mock('next/navigation', () => ({ useSearchParams: () => new URLSearchParams(params) }));

// eslint-disable-next-line @typescript-eslint/no-require-imports
const EvidenceStatement = require('@/app/reports/evidence-statement/EvidenceStatement').default;

const payload = (over: Record<string, unknown> = {}) => ({
  law_version_date: '2026-10-23', headline: 'Head line', lga: 'PENRITH', notes: ['A note'],
  exclusions: [{ para: 'a', clause: 's164(1)(a)', page: 78, law_words: 'bush fire prone land,', result: 'clear', result_words: 'No exclusion found', detail: 'lot outline is not on bush fire prone land', source_checked: 'NSW bush fire map' }],
  walk: { clause: 's163', page: 77, anchor: 'Penrith station', limit_m: 800, walk_low_m: 454, walk_high_m: 754, detail: null, heuristic: null },
  council_controls: { status: 'ok', as_at_line: null, controls: [{ control_type: 'front_setback', requirement: '4.5 m', council_words: 'words here', clause: '2.8', clause_shown: false, page: 32, version_checks: { status: 'ok', versions: [{ version: 'v1.1', verdict: 'not_found', result_words: 'These words were not found in this file', checked_page: 32, stale: false }, { version: 'v1.2', verdict: 'verbatim', result_words: 'Same words on the cited page', checked_page: 32, stale: false }] } }] },
  council_files: { status: 'unreadable', reason: 'the file ledger did not answer', files: [] },
  ...over,
});

function mockFetch(body: unknown, ok = true) {
  global.fetch = jest.fn().mockResolvedValue({ ok, json: async () => body }) as unknown as typeof fetch;
}

describe('evidence statement page', () => {
  it('shows law words, clause and page, the council words, and an unreadable source as unreadable', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload());
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText('bush fire prone land,')).toBeTruthy());
    expect(screen.getByText(/454 to 754 m/)).toBeTruthy();
    expect(screen.getByText('words here')).toBeTruthy();
    expect(screen.getByText(/label not checked against the page/)).toBeTruthy();
    expect(screen.getByText(/v1.1: These words were not found in this file/)).toBeTruthy();
    expect(screen.getByText(/v1.2: Same words on the cited page/)).toBeTruthy();
    expect(screen.getByText(/Could not be read: the file ledger did not answer/)).toBeTruthy();
  });

  it('shows an error, not an empty statement, when the data is partial or the call fails', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch({ exclusions: [] });
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
  });

  it('asks for coordinates when the address has none, and calls nothing', async () => {
    params = '';
    const f = jest.fn(); global.fetch = f as unknown as typeof fetch;
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    expect(f).not.toHaveBeenCalled();
  });
});
