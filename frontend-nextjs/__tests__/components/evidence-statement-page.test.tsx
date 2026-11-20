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
    // an older server answer has none of the newer parts: they are left out, never printed empty
    expect(screen.queryByText(/To check by hand/)).toBeNull();
    expect(screen.queryByText(/Crossings-only walk, for information/)).toBeNull();
    expect(screen.queryByText(/The walk is a range because/)).toBeNull();
  });

  it('shows the count line, the range reason, the crossings-only walk, the by-hand list, the scope line and the footer', async () => {
    params = 'lat=-33.75&lng=150.70';
    const base = payload();
    mockFetch(payload({
      summary: { total: 13, counts: { clear: 11, not_checked: 2 }, line: '13 paragraphs of section 164(1): 2 not checked by this tool; 11 no exclusion found.' },
      manual_checks: [{ clause: 's164(1)(i)', page: 79, law_words: 'a gas pipeline,', result_words: 'Not checked by this tool', detail: null, not_seen: null }],
      walk: { ...base.walk, margin_low_m: 25, margin_high_m: 75, entrance_unmapped_extra_m: 0, crossings_only_walk_m: 861, crossings_only_note: 'Crossing busy roads only at lights, the walk is about 861 m (+85 m compared with the normal walk). Check the crossings on the ground.' },
    }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/13 paragraphs of section 164\(1\): 2 not checked by this tool; 11 no exclusion found/)).toBeTruthy());
    expect(screen.getByText(/less 25 m to the measured walk plus 75 m/)).toBeTruthy();
    expect(screen.getByText(/Crossings-only walk, for information/)).toBeTruthy();
    expect(screen.getByText(/about 861 m \(\+85 m compared with the normal walk\)/)).toBeTruthy();
    expect(screen.getByText(/It does not change the result above/)).toBeTruthy();
    expect(screen.getByText('To check by hand')).toBeTruthy();
    expect(screen.getByText(/s164\(1\)\(i\) \(page 79\): a gas pipeline,/)).toBeTruthy();
    expect(screen.getByText(/controls that apply only to part of a council area, are not shown here/)).toBeTruthy();
    expect(screen.getByText(/It is not a planning certificate/)).toBeTruthy();
    expect(screen.getByText(/Section 164 exclusions \(law version dated 2026-10-23\)/)).toBeTruthy();
  });

  it('shows an error, not a page with a missing section, when an optional part arrives in the wrong shape', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ manual_checks: { clause: 's164(1)(i)' } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
    mockFetch(payload({ summary: { total: 13, counts: {}, line: 42 } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getAllByRole('alert').length).toBeGreaterThan(1));
  });

  it('still prints the crossings-only distance when its note is missing', async () => {
    params = 'lat=-33.75&lng=150.70';
    const base = payload();
    mockFetch(payload({ walk: { ...base.walk, crossings_only_walk_m: 861, crossings_only_note: null } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/the walk is about 861 m/)).toBeTruthy());
    expect(screen.getByText(/It does not change the result above/)).toBeTruthy();
  });

  it('says when our records for the council begin, from the dates in the files table', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ council_files: { status: 'ok', files: [
      { chapter: 'ch1', version: 'v1.2', held_from: '2026-10-26T00:00:00', replaced_on: null, current: true, council_file_date: 'x', council_file_date_note: null },
      { chapter: 'ch1', version: 'v1.1', held_from: '2026-02-28T04:00:00', replaced_on: '2026-10-26T00:00:00', current: false, council_file_date: null, council_file_date_note: 'not kept for earlier versions' },
      { chapter: 'ch2', version: 'v1.0', held_from: null, replaced_on: null, current: true, council_file_date: null, council_file_date_note: null },
    ] } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/earliest file we hold for this council is held from 2026-02-28/)).toBeTruthy());
  });

  it('says nothing about when records begin when no file has a held-from date, or the files could not be read', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ council_files: { status: 'ok', files: [{ chapter: 'ch1', version: 'v1', held_from: null, replaced_on: null, current: true, council_file_date: null, council_file_date_note: null }] } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/Council files held/)).toBeTruthy());
    expect(screen.queryByText(/earliest file we hold/)).toBeNull();
  });

  it('puts the notes before the walking range so a reader meets them first', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload());
    const { container } = render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText('A note')).toBeTruthy());
    const text = container.textContent ?? '';
    expect(text.indexOf('A note')).toBeGreaterThan(-1);
    expect(text.indexOf('A note')).toBeLessThan(text.indexOf('Walking range'));
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
