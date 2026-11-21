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
      { chapter: 'ch2', version: 'v1.0', held_from: '2026-06-01T00:00:00', replaced_on: null, current: true, council_file_date: null, council_file_date_note: null },
    ] } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/earliest file we hold for this council is held from 2026-02-28/)).toBeTruthy());
  });

  it('says nothing about when records begin when ANY listed file has no held-from date, because that file could be older', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ council_files: { status: 'ok', files: [
      { chapter: 'ch1', version: 'v1.1', held_from: '2026-02-28T04:00:00', replaced_on: null, current: true, council_file_date: null, council_file_date_note: null },
      { chapter: 'ch2', version: 'v1.0', held_from: null, replaced_on: null, current: false, council_file_date: null, council_file_date_note: null },
    ] } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/Council files held/)).toBeTruthy());
    expect(screen.queryByText(/earliest file we hold/)).toBeNull();
  });

  it('says nothing about when records begin when a date is not in YYYY-MM-DD form, because it would not sort correctly', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ council_files: { status: 'ok', files: [
      { chapter: 'ch1', version: 'v1.1', held_from: '2026-2-28', replaced_on: null, current: false, council_file_date: null, council_file_date_note: null },
      { chapter: 'ch1', version: 'v1.2', held_from: '2026-10-26T00:00:00Z', replaced_on: null, current: true, council_file_date: null, council_file_date_note: null },
    ] } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/Council files held/)).toBeTruthy());
    expect(screen.queryByText(/earliest file we hold/)).toBeNull();
  });

  it('says nothing about when records begin when no file has a held-from date, or the files could not be read', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ council_files: { status: 'ok', files: [{ chapter: 'ch1', version: 'v1', held_from: null, replaced_on: null, current: true, council_file_date: null, council_file_date_note: null }] } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/Council files held/)).toBeTruthy());
    expect(screen.queryByText(/earliest file we hold/)).toBeNull();
  });

  const ROAD_RULES = {
    status: 'ok', instrument: 'Road Rules 2014 (NSW), regulations 231, 232 and 234', copied_on: '2026-11-20',
    rules: [
      { clause: 'reg 234(1)', heading: 'Crossing a road on or near a crossing for pedestrians', source_url: 'https://www5.austlii.edu.au/au/legis/nsw/consol_reg/rr2014104/s234.html',
        quote: '(1) A pedestrian must not cross a road, or part of a road, within 20 metres of a crossing on the road, except at the crossing or another crossing, unless the pedestrian is--\n(a) crossing, or helping another pedestrian to cross' },
      { clause: 'reg 234(4)', heading: 'Crossing a road on or near a crossing for pedestrians', source_url: 'https://www5.austlii.edu.au/au/legis/nsw/consol_reg/rr2014104/s234.html',
        quote: '"crossing" means a children\'s crossing, marked foot crossing or pedestrian crossing.' },
    ],
  };
  const WITH_CROSSINGS = { crossings_only_walk_m: 861, crossings_only_note: 'Crossing busy roads only at lights, the walk is about 861 m. Check the crossings on the ground.' };

  it('shows the road rules word for word, with clause and source, beside the crossings-only line', async () => {
    params = 'lat=-33.75&lng=150.70';
    const base = payload();
    mockFetch(payload({ road_rules: ROAD_RULES, walk: { ...base.walk, ...WITH_CROSSINGS } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/NSW road rules for pedestrians at lights and near crossings/)).toBeTruthy());
    expect(screen.getByText(/A pedestrian must not cross a road, or part of a road, within 20 metres of a crossing on the road/)).toBeTruthy();
    expect(screen.getByText(/"crossing" means a children's crossing, marked foot crossing or pedestrian crossing\./)).toBeTruthy();
    expect(screen.getByText(/reg 234\(1\), Crossing a road on or near a crossing for pedestrians\. Source: https:\/\/www5\.austlii\.edu\.au\/au\/legis\/nsw\/consol_reg\/rr2014104\/s234\.html/)).toBeTruthy();
    expect(screen.getByText(/This tool does not decide whether a walk is lawful/)).toBeTruthy();
  });

  it('does not show the road rules when there is no crossings-only line to read them against', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ road_rules: ROAD_RULES }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/Council files held/)).toBeTruthy());
    expect(screen.queryByText(/NSW road rules for pedestrians/)).toBeNull();
  });

  it('says the road rules could not be shown when the data says unreadable, and never an empty box', async () => {
    params = 'lat=-33.75&lng=150.70';
    const base = payload();
    mockFetch(payload({ road_rules: { status: 'unreadable', reason: 'the saved road-rules text does not match its fingerprint' }, walk: { ...base.walk, ...WITH_CROSSINGS } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/The road rules wording could not be shown: the saved road-rules text does not match its fingerprint/)).toBeTruthy());
  });

  it('shows an error when road_rules arrives in the wrong shape', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ road_rules: { status: 'ok', rules: 'not a list' } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
  });

  it('shows an error, not an empty legal quotation, when a road rule has a null or blank quote', async () => {
    params = 'lat=-33.75&lng=150.70';
    const base = payload();
    for (const quote of [null, '', '   ']) {
      mockFetch(payload({ road_rules: { ...ROAD_RULES, rules: [{ ...ROAD_RULES.rules[0], quote }] }, walk: { ...base.walk, ...WITH_CROSSINGS } }));
      const { unmount } = render(<EvidenceStatement />);
      await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
      unmount();
    }
  });

  it('shows an error, not a crashed page, when a road-rules display field is not text', async () => {
    params = 'lat=-33.75&lng=150.70';
    const base = payload();
    const withCrossings = { ...base.walk, ...WITH_CROSSINGS };
    const bad = [
      { ...ROAD_RULES, copied_on: { day: 20 } },
      { ...ROAD_RULES, instrument: ['x'] },
      { ...ROAD_RULES, rules: [{ ...ROAD_RULES.rules[0], heading: { a: 1 } }] },
      { status: 'unreadable', reason: { why: 'x' } },
    ];
    for (const rr of bad) {
      mockFetch(payload({ road_rules: rr, walk: withCrossings }));
      const { unmount } = render(<EvidenceStatement />);
      await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
      unmount();
    }
  });

  const ROUTE_DEST = { name: 'Turramurra station and town centre', kind: 'town_centre_edge' };
  const routeLine = (walk_m: number, points: unknown, over: Record<string, unknown> = {}) => ({
    length_m: walk_m, walk_m, points, entrance: null, destination: ROUTE_DEST,
    busy_road_points: [[-33.7362, 151.1371], [-33.7358, 151.1378]], osm_extract: '2026-11-19T22:29:33Z', ...over,
  });
  const CAREFUL_POINTS = [[-33.7400, 151.1300], [-33.7380, 151.1340], [-33.7355, 151.1385]];
  const NORMAL_POINTS = [[-33.7400, 151.1300], [-33.7385, 151.1330], [-33.7355, 151.1385]];
  const ROUTE_MAP = {
    status: 'ok', reason: null,
    destination: ROUTE_DEST,   // the figure names the destination from the top level of the route map, not from a line
    careful: routeLine(962.8, CAREFUL_POINTS),
    normal: routeLine(877.7, NORMAL_POINTS),
    attribution: 'Map data from OpenStreetMap contributors (ODbL), extract of 2026-11-19',
    note: 'The lines follow mapped footpaths and roads and may differ from the walk on the ground.',
  };
  const withRouteMap = (over: Record<string, unknown> = {}) => payload({ route_map: { ...ROUTE_MAP, ...over } });
  const legendOf = (c: HTMLElement) => c.querySelector('figcaption')?.textContent ?? '';

  it('draws the route map as a labelled picture with both distances, the difference, the attribution and the note', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(withRouteMap());
    const { container } = render(<EvidenceStatement />);
    expect(await screen.findByRole('img')).toBeTruthy();
    expect(container.querySelector('svg title')?.textContent).toContain('Turramurra station and town centre');
    const desc = container.querySelector('svg desc')?.textContent ?? '';
    expect(desc).toContain('878');
    expect(desc).toContain('963');
    expect(desc).toContain('+85');
    const legend = legendOf(container);
    expect(legend).toContain('Normal route');
    expect(legend).toContain('Crossings-only route');
    expect(legend).toContain('878 m');
    expect(legend).toContain('963 m');
    expect(legend).toContain('(+85 m compared with the normal route)');
    expect(screen.getByText(ROUTE_MAP.attribution)).toBeTruthy();
    expect(screen.getByText(ROUTE_MAP.note)).toBeTruthy();
    // the normal route is dashed, the crossings-only route is a solid line
    const lines = Array.from(container.querySelectorAll('polyline'));
    expect(lines).toHaveLength(2);
    expect(lines.filter((l) => l.getAttribute('stroke-dasharray'))).toHaveLength(1);
    expect(lines.filter((l) => !l.getAttribute('stroke-dasharray'))).toHaveLength(1);
  });

  it('draws no route map, and says nothing about one, when the server sent none or null', async () => {
    params = 'lat=-33.75&lng=150.70';
    for (const body of [payload(), payload({ route_map: null })]) {
      mockFetch(body);
      const { container, unmount } = render(<EvidenceStatement />);
      await waitFor(() => expect(screen.getByText(/Council files held/)).toBeTruthy());
      expect(screen.queryByRole('img')).toBeNull();
      expect(container.querySelector('svg')).toBeNull();
      expect(container.textContent ?? '').not.toMatch(/route map/i);
      unmount();
    }
  });

  it('shows the note, and draws one line only, when there is no normal route', async () => {
    params = 'lat=-33.75&lng=150.70';
    const note = 'No normal route is drawn: the normal walk is measured to a different point than the one shown.';
    mockFetch(withRouteMap({ normal: null, normal_note: note }));
    const { container } = render(<EvidenceStatement />);
    expect(await screen.findByRole('img')).toBeTruthy();
    expect(legendOf(container)).toContain(note);
    expect(legendOf(container)).toContain('963 m');
    expect(container.querySelectorAll('polyline')).toHaveLength(1);
    expect(container.querySelector('polyline')?.getAttribute('stroke-dasharray')).toBeNull();
  });

  it('shows the note when there is no crossings-only route, and draws the normal line only', async () => {
    params = 'lat=-33.75&lng=150.70';
    const note = 'No crossings-only route is drawn: no route avoids crossing busy roads away from lights.';
    mockFetch(withRouteMap({ careful: null, careful_note: note }));
    const { container } = render(<EvidenceStatement />);
    expect(await screen.findByRole('img')).toBeTruthy();
    expect(legendOf(container)).toContain(note);
    expect(legendOf(container)).toContain('878 m');
    expect(container.querySelectorAll('polyline')).toHaveLength(1);
    expect(container.querySelector('polyline')?.getAttribute('stroke-dasharray')).toBeTruthy();
  });

  it('says why the route map is not drawn, in words and with no picture, when the data says unavailable', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(payload({ route_map: { status: 'unavailable', reason: 'the street map for this area could not be read' } }));
    render(<EvidenceStatement />);
    await waitFor(() => expect(screen.getByText(/The route map is not drawn: the street map for this area could not be read/)).toBeTruthy());
    expect(screen.queryByRole('img')).toBeNull();
  });

  it('shows an error, not a missing or half-drawn map, when the route map arrives in the wrong shape', async () => {
    params = 'lat=-33.75&lng=150.70';
    const bad: Record<string, unknown>[] = [
      { careful: routeLine(962.8, 'not a list') },
      { careful: routeLine(962.8, [[null, 151.1300], [-33.7380, 151.1340], [-33.7355, 151.1385]]) },
      { careful: routeLine(962.8, [[-33.7400, 151.1300]]) },
      { careful: null, normal: null },
      { careful: routeLine(962.8, CAREFUL_POINTS, { destination: { name: 'Turramurra', kind: 'bogus' } }) },
      { reason: { why: 'x' } },
      { careful: routeLine(962.8, [[200, 151.1300], [-33.7380, 151.1340], [-33.7355, 151.1385]]) },
    ];
    for (const over of bad) {
      mockFetch(withRouteMap(over));
      const { unmount } = render(<EvidenceStatement />);
      await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy());
      expect(screen.queryByRole('img')).toBeNull();
      unmount();
    }
  });

  it('shows each route distance as its walk_m rounded, never its length_m', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(withRouteMap({
      normal: routeLine(877.7, NORMAL_POINTS, { length_m: 880.1 }),
      careful: routeLine(962.8, CAREFUL_POINTS, { length_m: 965.4 }),
    }));
    const { container } = render(<EvidenceStatement />);
    expect(await screen.findByRole('img')).toBeTruthy();
    const legend = legendOf(container);
    const desc = container.querySelector('svg desc')?.textContent ?? '';
    for (const text of [legend, desc]) {
      expect(text).toContain('878');
      expect(text).toContain('963');
      expect(text).not.toContain('880');
      expect(text).not.toContain('965');
    }
  });

  it('names the destination from the route when the top level of the route map has none, never the generic label', async () => {
    params = 'lat=-33.75&lng=150.70';
    mockFetch(withRouteMap({ destination: undefined }));
    const { container } = render(<EvidenceStatement />);
    expect(await screen.findByRole('img')).toBeTruthy();
    expect(container.querySelector('svg title')?.textContent).toContain('Turramurra station and town centre');
    expect(container.querySelector('svg title')?.textContent).not.toContain('the destination');
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
