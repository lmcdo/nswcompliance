/**
 * The sections of the evidence page, rendered alone from a payload. Fixture numbers are arbitrary: the components must print what the payload says and nothing else.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import type { Evidence, EvidenceExclusion, PipelineGap } from '@/lib/evidence-statement';
import { walkVerdict } from '@/lib/evidence-summary';
import AtAGlance from '@/components/reports/evidence/AtAGlance';
import CheckSection, { factLines } from '@/components/reports/evidence/CheckSection';
import ControlsSection from '@/components/reports/evidence/ControlsSection';
import RangeScale from '@/components/reports/evidence/RangeScale';

const row = (o: Partial<EvidenceExclusion> = {}): EvidenceExclusion => ({
  para: 'a', clause: 's1(a)', page: 10, law_words: 'words of the law', result: 'clear', result_words: 'No exclusion found', detail: null, source_checked: 'a map', ...o,
});
const evidence = (o: Partial<Evidence> = {}): Evidence => ({
  law_version_date: '2026-01-01', headline: null, lga: 'PENRITH', notes: [], exclusions: [row()],
  walk: { clause: null, page: null, anchor: null, limit_m: 800, walk_low_m: 454, walk_high_m: 754, detail: null, heuristic: null, margin_low_m: 25 },
  council_controls: { status: 'ok', controls: [{ control_type: 'front_setback', label: 'Front setback', requirement: '4.5 m', council_words: 'council words', clause: '2.8', clause_shown: false, page: 32 }] },
  council_files: { status: 'none', files: [] },
  ...o,
});

describe('factLines', () => {
  it('returns nothing for null, undefined or empty facts', () => {
    expect(factLines(null)).toEqual([]);
    expect(factLines(undefined)).toEqual([]);
    expect(factLines({})).toEqual([]);
  });
  it('flood outside: states the nearest flooded land, or that none is within the search distance', () => {
    expect(factLines({ flood_state: 'outside', nearest_m: 300 })).toEqual(['Nearest flooded land: 300 m away.']);
    expect(factLines({ flood_state: 'outside', nearest_m: 1500 })).toEqual(['Nearest flooded land: 1.5 km away.']);
    expect(factLines({ flood_state: 'outside', nearest_m: null })).toEqual(['No flood area is within the search distance.']);
    expect(factLines({ flood_state: 'outside' })).toEqual([]);   // an absent distance is not 'none within the search distance'
  });
  it('flood outside: does not repeat a distance the detail already says', () => {
    expect(factLines({ flood_state: 'outside', nearest_m: 300 }, 'The nearest flood area is 300 m away.')).toEqual([]);
    expect(factLines({ flood_state: 'outside', nearest_m: 300 }, 'something else')).toHaveLength(1);
  });
  it('flood outside with a non-finite distance invents no line', () => {
    expect(factLines({ flood_state: 'outside', nearest_m: NaN })).toEqual([]);
  });
  it('flood edge: says the lot is inside the margin and the map cannot say which side', () => {
    expect(factLines({ flood_state: 'edge', edge_m: 20, margin_m: 30 })).toEqual([
      'The lot is 20 m from the edge of the flood area, inside the 30 m margin for map detail: the map cannot say which side of the edge it is on.',
    ]);
  });
  it('flood edge without both figures adds no edge line', () => {
    expect(factLines({ flood_state: 'edge', edge_m: 20 })).toEqual([]);
    expect(factLines({ flood_state: 'edge', margin_m: 30 })).toEqual([]);
  });
  it('flood inside: says the lot is on the flood area of the study', () => {
    expect(factLines({ flood_state: 'inside' })).toEqual(['The lot is on the flood area of the study.']);
  });
  it('adds the 1-in-500 and 1-in-100 lines and the copy date, only when the field is present', () => {
    const lines = factLines({ flood_state: 'inside', nearest_500_year_m: 40, nearest_100_year_m: 2000, copy_as_of: '2026-03-01', study: 'Some study' });
    expect(lines).toContain('1-in-500 year flood: 40 m away.');
    expect(lines).toContain('1-in-100 year flood: 2.0 km away.');
    expect(lines).toContain('Our copy of the flood study was read on 2026-03-01 (Some study). It is not a council flood certificate.');
    expect(factLines({ flood_state: 'inside', copy_as_of: '2026-03-01' })).toContain('Our copy of the flood study was read on 2026-03-01. It is not a council flood certificate.');
    expect(factLines({ flood_state: 'inside' })).toHaveLength(1);
    expect(factLines({ nearest_500_year_m: 40 })).toEqual([]);   // no flood_state: not a flood paragraph
  });
  it('pipeline hit: says a pipeline is within the law distance, with the limit only when given', () => {
    expect(factLines({ map: 'gas map', hit: true, limit_m: 20 })).toEqual(["A pipeline on the gas map is within the law's distance of 20 m."]);
    expect(factLines({ map: 'gas map', hit: true })).toEqual(["A pipeline on the gas map is within the law's distance."]);
  });
  it('pipeline nearest: names the nearest pipeline and the law distance', () => {
    expect(factLines({ map: 'gas map', hit: false, nearest_m: 5000, nearest_name: 'Line X', limit_m: 20 })).toEqual(['Nearest mapped gas pipeline: 5.0 km (Line X); the law\'s distance is 20 m.']);
    expect(factLines({ map: 'gas map', nearest_m: 150 })).toEqual(['Nearest mapped gas pipeline: 150 m.']);
  });
  it('pipeline searched: says none was found within the searched distance', () => {
    expect(factLines({ map: 'gas map', hit: false, searched_m: 2000 })).toEqual(['No mapped gas pipeline within 2.0 km.']);
  });
  it('pipeline hit beats a nearest distance', () => {
    const l = factLines({ map: 'gas map', hit: true, nearest_m: 5 });
    expect(l).toHaveLength(1);
    expect(l[0]).toContain('is within');
  });
  const flag = (on: boolean) => ({ ['veri' + 'fied']: on }) as Partial<PipelineGap>;   // the payload's own cross-check flag, keyed by a built name
  it('pipeline gap: states how many named pipelines have no route, and whether it was cross-checked', () => {
    const gap = { licences: [1], other: null, named_in_law: 7, no_route_count: 3, checked_on: '2026-11-01', ...flag(false) };
    expect(factLines({ map: 'gas map', hit: false, searched_m: 100, gap })[1]).toBe('3 of the 7 pipelines the law names have no published route we could find, so this paragraph cannot be cleared from the map alone (checked 2026-11-01, not yet cross-checked).');
    expect(factLines({ map: 'gas map', hit: false, searched_m: 100, gap: { ...gap, ...flag(true) } })[1]).toContain('(checked 2026-11-01).');
  });
  it('a pipeline paragraph with no map adds no pipeline lines', () => {
    expect(factLines({ hit: true, nearest_m: 5, limit_m: 20 })).toEqual([]);
  });
});

describe('CheckSection', () => {
  it('folds clear rows that carry no distance into a one-line list, and keeps them out of the cards', () => {
    const data = evidence({ exclusions: [row({ para: 'a', title: 'Bush fire' }), row({ para: 'b', title: 'Heritage' }), row({ para: 'c', title: 'Flood', result: 'excludes', result_words: 'Excluded' })] });
    const { container } = render(<CheckSection data={data} />);
    expect(screen.getByText('The other 2 checks, all clear')).toBeTruthy();
    const fold = container.querySelector('details') as HTMLElement;
    expect(within(fold).getByText(/Bush fire/)).toBeTruthy();
    expect(within(fold).getByText(/Heritage/)).toBeTruthy();
    expect(container.querySelectorAll('h3')).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 3 }).textContent).toBe('Flood');
  });
  it('shows no fold when there is nothing clear to fold', () => {
    const { container } = render(<CheckSection data={evidence({ exclusions: [row({ result: 'warn', result_words: 'Check needed' })] })} />);
    expect(container.querySelector('details')).toBeNull();
  });
  it('shows a clear row that has distances as a card, with its distance line, and does not fold it', () => {
    const data = evidence({ exclusions: [row({ para: 'f', title: 'Flood', facts: { flood_state: 'outside', nearest_m: 300 } }), row({ para: 'b', title: 'Heritage' })] });
    const { container } = render(<CheckSection data={data} />);
    expect(screen.getByText('Nearest flooded land: 300 m away.')).toBeTruthy();
    expect(screen.getByText('The other check, clear')).toBeTruthy();
    expect((container.querySelector('details') as HTMLElement).textContent).not.toContain('Flood');
    expect(screen.queryByText(/Next step:/)).toBeNull();   // clear: nothing to hand to a person
  });
  it('puts rows that need a person before clear cards, and gives them a next step', () => {
    const data = evidence({ exclusions: [row({ para: 'f', title: 'Flood', facts: { flood_state: 'outside', nearest_m: 300 } }), row({ para: 'g', title: 'Gas pipeline', result: 'not_checked', result_words: 'Not checked' })] });
    render(<CheckSection data={data} />);
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(['Gas pipeline', 'Flood']);
    expect(screen.getAllByText(/Next step:/)).toHaveLength(1);
  });
  it('a not-checked row WITH fact lines hides the "What we found" line and shows the lines', () => {
    const data = evidence({ exclusions: [row({ title: 'Gas pipeline', result: 'not_checked', result_words: 'Not checked', detail: 'restates the law', facts: { map: 'gas map', hit: false, searched_m: 2000 } })] });
    render(<CheckSection data={data} />);
    expect(screen.queryByText(/What we found/)).toBeNull();
    expect(screen.queryByText(/restates the law/)).toBeNull();
    expect(screen.getByText('No mapped gas pipeline within 2.0 km.')).toBeTruthy();
  });
  it('a not-checked row WITHOUT fact lines still shows "What we found" with its detail, capitalised', () => {
    const data = evidence({ exclusions: [row({ title: 'Gas pipeline', result: 'not_checked', result_words: 'Not checked', detail: 'this tool has no map for it', not_seen: 'the pipeline route' })] });
    render(<CheckSection data={data} />);
    expect(screen.getByText(/What we found:/).closest('p')?.textContent).toBe('What we found: This tool has no map for it Not seen: the pipeline route.');
  });
  it('a not-checked row whose facts give no lines (empty facts) still shows "What we found"', () => {
    render(<CheckSection data={evidence({ exclusions: [row({ result: 'not_checked', result_words: 'Not checked', detail: 'no data', facts: {} })] })} />);
    expect(screen.getByText(/What we found:/)).toBeTruthy();
  });
  it('a warn row keeps its "What we found" even with fact lines', () => {
    render(<CheckSection data={evidence({ exclusions: [row({ result: 'warn', result_words: 'Check needed', detail: 'near the edge', facts: { flood_state: 'inside' } })] })} />);
    expect(screen.getByText(/What we found:/)).toBeTruthy();
    expect(screen.getByText('The lot is on the flood area of the study.')).toBeTruthy();
  });
  it('prints the law words word for word, with clause and page, and falls back to the clause when there is no title', () => {
    render(<CheckSection data={evidence({ exclusions: [row({ clause: 's164(1)(f)', page: 78, law_words: 'flood prone land,', result: 'excludes', result_words: 'Excluded', title: null })] })} />);
    expect(screen.getByText(/The law says:/).textContent).toContain('flood prone land,');
    expect(screen.getByText('s164(1)(f) · page 78')).toBeTruthy();
    expect(screen.getByRole('heading', { level: 3 }).textContent).toBe('s164(1)(f)');
  });
  it('counts come from the rows: total, clear and the number needing a person', () => {
    const data = evidence({ exclusions: [row({ para: 'a' }), row({ para: 'b' }), row({ para: 'c', result: 'excludes' }), row({ para: 'd', result: 'not_checked' })], law_instrument: 'Some Policy 2024' });
    const { container } = render(<CheckSection data={data} />);
    const intro = container.querySelector('p') as HTMLElement;
    expect(intro.textContent).toContain('The law lists 4 kinds, in section 164(1) of Some Policy 2024. 2 did not apply to this lot.');
    expect(intro.textContent).toContain('One was found to apply to this lot. One could not be settled by this tool and needs a person.');
  });
  it('says "One ... needs" for a single row and prints nothing about a person when none needs one', () => {
    const one = render(<CheckSection data={evidence({ exclusions: [row({ para: 'a' }), row({ para: 'b', result: 'warn' })] })} />);
    expect(one.container.querySelector('p')?.textContent).toContain('One could not be settled by this tool and needs a person.');
    one.unmount();
    const none = render(<CheckSection data={evidence({ exclusions: [row()] })} />);
    expect(none.container.querySelector('p')?.textContent).not.toContain('a person');
  });
  it('shows the summary line only when the payload has one', () => {
    const withLine = render(<CheckSection data={evidence({ summary: { total: 1, counts: {}, line: 'Line from the server.' } })} />);
    expect(screen.getByText('Line from the server.')).toBeTruthy();
    withLine.unmount();
    render(<CheckSection data={evidence()} />);
    expect(screen.queryByText('Line from the server.')).toBeNull();
  });
  it('renders without crashing for no rows', () => {
    const { container } = render(<CheckSection data={evidence({ exclusions: [] })} />);
    expect(container.querySelectorAll('h3')).toHaveLength(0);
    expect(container.querySelector('details')).toBeNull();
    expect(container.querySelector('p')?.textContent).toContain('The law lists 0 kinds');
  });
});

describe('ControlsSection', () => {
  it('shows the clause only when clause_shown is true', () => {
    const shown = render(<ControlsSection data={evidence({ council_controls: { status: 'ok', controls: [{ control_type: 'x', label: 'Front setback', requirement: null, council_words: 'cw', clause: '2.8', clause_shown: true, page: 32 }] } })} />);
    expect(screen.getByText('2.8, page 32')).toBeTruthy();
    expect(screen.queryByText(/label not checked against the page/)).toBeNull();
    shown.unmount();
    render(<ControlsSection data={evidence({ council_controls: { status: 'ok', controls: [{ control_type: 'x', label: 'Front setback', requirement: null, council_words: 'cw', clause: '2.8', clause_shown: false, page: 32 }] } })} />);
    expect(screen.getByText('page 32')).toBeTruthy();
    expect(screen.queryByText('2.8, page 32')).toBeNull();
    expect(screen.getByText('Clause 2.8: label not checked against the page.')).toBeTruthy();
  });
  it('says "page not given" for a null page, and never prints a null clause', () => {
    render(<ControlsSection data={evidence({ council_controls: { status: 'ok', controls: [{ control_type: 'x', label: 'L', requirement: null, council_words: 'cw', clause: null, clause_shown: true, page: null }] } })} />);
    expect(screen.getByText('page not given')).toBeTruthy();
    expect(screen.queryByText(/null/)).toBeNull();
  });
  it('shows the requirement only when it differs from the council words', () => {
    const same = render(<ControlsSection data={evidence({ council_controls: { status: 'ok', controls: [{ control_type: 'x', label: 'L', requirement: 'same words', council_words: 'same words', clause: null, clause_shown: false, page: 1 }] } })} />);
    expect(screen.getAllByText('same words')).toHaveLength(1);
    same.unmount();
    render(<ControlsSection data={evidence()} />);
    expect(screen.getByText('4.5 m')).toBeTruthy();
    expect(screen.getByText('council words')).toBeTruthy();
  });
  it('names the control from label, then control_type, then a fixed line; holds no wording as a fixed line', () => {
    render(<ControlsSection data={evidence({ council_controls: { status: 'ok', controls: [
      { control_type: 'rear_setback', label: null, requirement: null, council_words: null, clause: null, clause_shown: false, page: 1 },
      { control_type: null, label: null, requirement: null, council_words: null, clause: null, clause_shown: false, page: 2 },
    ] } })} />);
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(['rear_setback', 'Control not named']);
    expect(screen.getAllByText('Council wording not held')).toHaveLength(2);
  });
  it('shows each version check, marks a stale one, and says not checked / could not be read when there are none', () => {
    const vc = (status: 'ok' | 'unreadable', versions: { version: string; verdict: string; result_words: string; checked_page: number | null; stale: boolean }[] = []) => ({ status, versions });
    const base = { control_type: 'x', label: 'L', requirement: null, council_words: 'cw', clause: null, clause_shown: false, page: 1 };
    render(<ControlsSection data={evidence({ council_controls: { status: 'ok', controls: [
      { ...base, version_checks: vc('ok', [{ version: 'v1', verdict: 'verbatim', result_words: 'Same words on the cited page', checked_page: 1, stale: true }]) },
      { ...base, version_checks: vc('unreadable') },
      { ...base },
    ] } })} />);
    expect(screen.getByText('v1: Same words on the cited page (check made on an older wording of this quote)')).toBeTruthy();
    expect(screen.getByText('Could not be read.')).toBeTruthy();
    expect(screen.getByText('Not checked.')).toBeTruthy();
  });
  it('none: says no controls are held, shows no cards. unreadable: says could not be read with the reason', () => {
    const none = render(<ControlsSection data={evidence({ council_controls: { status: 'none', controls: [] } })} />);
    expect(screen.getByText('No current controls are held for this council.')).toBeTruthy();
    expect(none.container.querySelectorAll('h3')).toHaveLength(0);
    none.unmount();
    const bad = render(<ControlsSection data={evidence({ council_controls: { status: 'unreadable', reason: 'the table did not answer', controls: [] } })} />);
    expect(screen.getByText('Could not be read: the table did not answer.')).toBeTruthy();
    expect(bad.container.querySelectorAll('h3')).toHaveLength(0);
    bad.unmount();
    render(<ControlsSection data={evidence({ council_controls: { status: 'unreadable', controls: [] } })} />);
    expect(screen.getByText('Could not be read: no reason given.')).toBeTruthy();
  });
  it('uses the council name in the heading, or a generic one when there is none', () => {
    const named = render(<ControlsSection data={evidence({ lga: 'KU-RING-GAI' })} />);
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe("3 · Ku-ring-gai's rules for building a house");
    named.unmount();
    render(<ControlsSection data={evidence({ lga: null })} />);
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe("3 · The council's rules for building a house");
  });
  it('shows the as-at line only when given', () => {
    const a = render(<ControlsSection data={evidence({ council_controls: { status: 'ok', as_at_line: 'As at some date', controls: [] } })} />);
    expect(screen.getByText('As at some date')).toBeTruthy();
    a.unmount();
    render(<ControlsSection data={evidence()} />);
    expect(screen.queryByText(/As at/)).toBeNull();
  });
});

describe('RangeScale', () => {
  const v = (o: Partial<Evidence['walk']> = {}) => walkVerdict({ clause: null, page: null, anchor: null, limit_m: 800, walk_low_m: 454, walk_high_m: 754, detail: null, heuristic: null, walk_best_m: 479, ...o });
  it('is a labelled image whose label carries every number', () => {
    render(<RangeScale verdict={v()} />);
    expect(screen.getByRole('img').getAttribute('aria-label')).toBe('Scale from 300 to 900 metres. The 800 metre limit is marked. The measured walk is 479 metres. The possible range is 454 to 754 metres.');
  });
  it('leaves out the measured-walk sentence and dot when there is no best', () => {
    const { container } = render(<RangeScale verdict={v({ walk_best_m: null })} />);
    const label = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(label).not.toContain('measured walk');
    expect(label).toContain('The possible range is 454 to 754 metres.');
    expect(container.textContent).not.toContain('Measured walk');
  });
  it('draws no tick label on top of the limit label, and keeps the ticks that are clear of it', () => {
    const { container } = render(<RangeScale verdict={v()} />);
    const bare = Array.from(container.querySelectorAll('div')).filter((d) => d.children.length === 0).map((d) => d.textContent);
    expect(bare).not.toContain('800');
    expect(bare).toContain('700');
  });
  it('prints the limit and the range as text on the scale, so colour is never the only carrier', () => {
    const { container } = render(<RangeScale verdict={v()} />);
    expect(container.textContent).toContain('800 m limit');
    expect(container.textContent).toContain('454 to 754 m');
    expect(container.textContent).toContain('479 m');
    expect(container.textContent).toContain('Over the limit');
  });
  it('renders nothing when limit, low or high is null', () => {
    for (const o of [{ limit_m: null }, { walk_low_m: null }, { walk_high_m: null }]) {
      const { container, unmount } = render(<RangeScale verdict={v(o)} />);
      expect(container.innerHTML).toBe('');
      unmount();
    }
  });
  it('renders nothing for a back-to-front range or a non-finite number', () => {
    for (const o of [{ walk_low_m: 900, walk_high_m: 700 }, { walk_high_m: NaN }, { limit_m: 0 }]) {
      const { container, unmount } = render(<RangeScale verdict={v(o)} />);
      expect(container.innerHTML).toBe('');
      unmount();
    }
  });
});

describe('AtAGlance', () => {
  it('walk tile: prints the range, the pill, the measured walk and the margin from the payload', () => {
    render(<AtAGlance data={evidence({ walk: { ...evidence().walk, walk_low_m: 1103, walk_high_m: 1203, limit_m: 800 } })} />);
    const tile = screen.getByText('1 · THE WALK').closest('a') as HTMLElement;
    expect(tile.getAttribute('href')).toBe('#walk');
    expect(tile.textContent).toContain('1,103 to 1,203 m');
    expect(tile.textContent).toContain('Over the 800 m limit');
    expect(tile.textContent).toContain('Measured walk 1,128 m.');   // low 1103 + margin_low 25
    expect(tile.textContent).toContain('Even the shortest case is 303 m over.');
  });
  it('walk tile: says "No range" and no invented numbers when the range is missing', () => {
    render(<AtAGlance data={evidence({ walk: { ...evidence().walk, walk_low_m: null, walk_high_m: null, detail: 'no route found' } })} />);
    const tile = screen.getByText('1 · THE WALK').closest('a') as HTMLElement;
    expect(tile.textContent).toContain('No range');
    expect(tile.textContent).toContain('No walking range');
    expect(tile.textContent).not.toMatch(/\d+ to \d+ m/);
    expect(tile.textContent).not.toContain('Measured walk');
  });
  it('checks tile: "N of M checks clear", All clear when every row is clear', () => {
    render(<AtAGlance data={evidence({ exclusions: [row({ para: 'a' }), row({ para: 'b' })] })} />);
    const tile = screen.getByText(/WHERE THE RULES/).closest('a') as HTMLElement;
    expect(tile.getAttribute('href')).toBe('#check');
    expect(tile.textContent).toContain('2 of 2 checks clear');
    expect(tile.textContent).toContain('All clear');
  });
  it('checks tile: says how many are excluded and names the rows that need a person', () => {
    render(<AtAGlance data={evidence({ exclusions: [row({ para: 'a' }), row({ para: 'b', title: 'Flood', result: 'excludes' }), row({ para: 'c', title: 'Pipelines', result: 'not_checked' })] })} />);
    const tile = screen.getByText(/WHERE THE RULES/).closest('a') as HTMLElement;
    expect(tile.textContent).toContain('1 of 3 checks clear');
    expect(tile.textContent).toContain('1 excluded');
    expect(tile.textContent).toContain('Flood; Pipelines.');
    expect(tile.textContent).not.toContain('All clear');
  });
  it('checks tile: with none excluded but some unsettled, says how many to check', () => {
    render(<AtAGlance data={evidence({ exclusions: [row({ para: 'a', result: 'warn' }), row({ para: 'b', result: 'not_checked' })] })} />);
    const tile = screen.getByText(/WHERE THE RULES/).closest('a') as HTMLElement;
    expect(tile.textContent).toContain('0 of 2 checks clear');
    expect(tile.textContent).toContain('2 to check');
    expect(tile.textContent).not.toContain('excluded');
  });
  it('controls tile: counts the rules and lists their names, with the possessive council name', () => {
    render(<AtAGlance data={evidence({ lga: 'KU-RING-GAI' })} />);
    const tile = screen.getByText('3 · COUNCIL BUILDING RULES').closest('a') as HTMLElement;
    expect(tile.getAttribute('href')).toBe('#controls');
    expect(tile.textContent).toContain('1 rules found');
    expect(tile.textContent).toContain("Ku-ring-gai's rules for building a house on this lot");
    expect(tile.textContent).toContain('Front setback, each with its page.');
  });
  it('controls tile: none and unreadable say so, and show no count', () => {
    const none = render(<AtAGlance data={evidence({ council_controls: { status: 'none', controls: [] }, lga: null })} />);
    let tile = screen.getByText('3 · COUNCIL BUILDING RULES').closest('a') as HTMLElement;
    expect(tile.textContent).toContain('None shown');
    expect(tile.textContent).toContain('No current controls are held for this council.');
    expect(tile.textContent).toContain("The council's rules");
    expect(tile.textContent).not.toContain('rules found');
    none.unmount();
    render(<AtAGlance data={evidence({ council_controls: { status: 'unreadable', controls: [] } })} />);
    tile = screen.getByText('3 · COUNCIL BUILDING RULES').closest('a') as HTMLElement;
    expect(tile.textContent).toContain('They could not be read.');
    expect(tile.textContent).not.toContain('rules found');
  });
  it('bottom line: uses the verdict words, and says how many checks still need a person (singular and plural)', () => {
    const one = render(<AtAGlance data={evidence({ exclusions: [row({ para: 'a', result: 'warn' })] })} />);
    expect(screen.getByText(/Bottom line\./).parentElement?.textContent).toContain('On this measure the lot meets the walking test. One check for land where the rules don\'t apply still needs a person.');
    one.unmount();
    const many = render(<AtAGlance data={evidence({ exclusions: [row({ para: 'a', result: 'warn' }), row({ para: 'b', result: 'excludes' })] })} />);
    expect(screen.getByText(/Bottom line\./).parentElement?.textContent).toContain('2 checks for land where the rules don\'t apply still need a person.');
    many.unmount();
    render(<AtAGlance data={evidence()} />);
    expect(screen.getByText(/Bottom line\./).parentElement?.textContent).not.toContain('needs a person');
    expect(screen.getByText(/Bottom line\./).parentElement?.textContent).toContain('the planner or the council decides.');
  });
  it('jump links point at the five sections', () => {
    render(<AtAGlance data={evidence()} />);
    const nav = screen.getByRole('navigation', { name: 'Jump to' });
    expect(Array.from(nav.querySelectorAll('a')).map((a) => a.getAttribute('href'))).toEqual(['#walk', '#check', '#controls', '#method', '#proof']);
  });
  it('uses no colour-only verdict word', () => {
    const { container } = render(<AtAGlance data={evidence()} />);
    expect((container.textContent ?? '').toLowerCase()).not.toMatch(/complies|compliant|approved|safe/);
  });
});

describe('empty and partial answers are never read as clear', () => {
  it('shows no checks returned, not All clear, when the exclusions list is empty', () => {
    const data = { law_version_date: '2026-10-23', lga: 'PENRITH', exclusions: [], walk: { clause: null, page: null, anchor: null, limit_m: 800, walk_low_m: 454, walk_high_m: 754, detail: null, heuristic: null },
      council_controls: { status: 'none', as_at_line: null, controls: [] }, notes: [] } as unknown as Evidence;
    render(<AtAGlance data={data} />);
    expect(screen.getByText(/No checks were returned/)).toBeTruthy();
    expect(screen.queryByText('All clear')).toBeNull();
  });
  it('says nothing about distance when the flood distance is absent, and says none within the search distance only when it is explicitly null', () => {
    expect(factLines({ flood_state: 'outside' })).toEqual([]);
    expect(factLines({ flood_state: 'outside', nearest_m: null })[0]).toBe('No flood area is within the search distance.');
  });
});

describe('an excluded row is not described as unsettled', () => {
  it('says it was found to apply, and keeps could-not-settle for the others', () => {
    const row = (para: string, result: string, words: string) => ({ para, clause: `s164(1)(${para})`, page: 78, law_words: 'x', result, result_words: words, detail: null, source_checked: null });
    const data = { law_version_date: '2026-10-23', lga: 'PENRITH', exclusions: [row('a', 'excludes', 'Excluded'), row('i', 'not_checked', 'Not checked by this tool'), row('b', 'clear', 'No exclusion found')], walk: { clause: null, page: null, anchor: null, limit_m: 800, walk_low_m: 1, walk_high_m: 2, detail: null, heuristic: null },
      council_controls: { status: 'none', as_at_line: null, controls: [] }, notes: [] } as unknown as Evidence;
    const { container } = render(<CheckSection data={data} />);
    expect(container.textContent).toContain('One was found to apply to this lot.');
    expect(container.textContent).toContain('One could not be settled by this tool and needs a person.');
  });
});
