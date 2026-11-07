/**
 * The card says what the area check measured, in plain words, and never says "can't tell" or "confirmed".
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { BANNED_READER_WORDS } from '@/test-support/banned-reader-words';
import { AreaCheckCard } from '@/components/compliance/AreaCheckCard';
import type { AreaCheck } from '@/hooks/useAreaCheck';

const result = (over: Partial<AreaCheck> = {}): AreaCheck => ({
  pathway: 'lmr',
  headline: 'Within the Chapter 6 walking limit: walking range 100-420 m from Ashfield station, limit 800 m (s163, p77).',
  lmr: { answer: 'yes', figures: { walk_low_m: 100, walk_high_m: 420, limit_m: 800, anchor: 'Ashfield station' } },
  tod: { answer: 'no' },
  warnings: [], notes: [], not_checked: [{ para: 'i', what: 'land within 200 m of a relevant pipeline', clause: 's164(1)(i)', page: 79 }],
  law_version_date: '2026-10-23', ...over,
});

import { rowsToFacts, type LawFactRow } from '@/lib/law-facts';

const BANNED = BANNED_READER_WORDS;

describe('AreaCheckCard', () => {
  it('shows the walking range, the limit, the law date and what was not checked', () => {
    render(<AreaCheckCard result={result()} loading={false} failed={false} />);
    expect(screen.getByTestId('area-check-lead').textContent).toMatch(/within the low and mid-rise walking distance/);
    expect(screen.getByTestId('area-check-range').textContent).toMatch(/between 100 and 420 m.*limit is 800 m/);
    expect(screen.getByTestId('area-check-not-checked').textContent).toMatch(/pipeline.*s164\(1\)\(i\), page 79/);
    expect(screen.getByTestId('area-check-card').textContent).toMatch(/law as at 2026-10-23/);
  });

  it('lists each warning with its clause and page', () => {
    const r = result({ warnings: [{ clause: 's164(1)(f1)', page: 78, detail: 'flood extent not checked' }] });
    render(<AreaCheckCard result={r} loading={false} failed={false} />);
    expect(screen.getByTestId('area-check-warnings').textContent).toMatch(/s164\(1\)\(f1\) \(page 78\): flood extent not checked/);
  });

  it('a borderline lot shows the range and the stated method', () => {
    const r = result({
      pathway: 'borderline',
      lmr: { answer: 'borderline', heuristic: 'the walk is assumed equally likely anywhere in the range', figures: { walk_low_m: 700, walk_high_m: 1000, limit_m: 800 } },
    });
    render(<AreaCheckCard result={r} loading={false} failed={false} />);
    expect(screen.getByTestId('area-check-lead').textContent).toMatch(/close to the low and mid-rise walking limit/);
    expect(screen.getByTestId('area-check-method').textContent).toMatch(/equally likely/);
  });

  it('a lot in a Chapter 5 area leads with Chapter 5 and shows no walking range', () => {
    const r = result({ pathway: 'tod', lmr: { answer: 'no', reason_code: 'chapter5' }, tod: { answer: 'yes' } });
    render(<AreaCheckCard result={r} loading={false} failed={false} />);
    expect(screen.getByTestId('area-check-lead').textContent).toMatch(/Chapter 5/);
    expect(screen.queryByTestId('area-check-range')).toBeNull();
  });

  it('a failed or missing result says it could not work out the area and why, with a next step, and loading says it is checking', () => {
    const { rerender } = render(<AreaCheckCard result={null} loading={false} failed={true} />);
    expect(screen.getByTestId('area-check-failed').textContent).toMatch(/^\s*We could not work out the area for this lot\. Why:[\s\S]*Spatial Viewer/);
    rerender(<AreaCheckCard result={null} loading={true} failed={false} />);
    expect(screen.getByTestId('area-check-loading')).toBeTruthy();
  });

  it('none of the rendered text uses the words the product avoids', () => {
    const undetermined = result({ pathway: 'unknown', lmr: { answer: 'cant_tell' }, headline: 'Why: a map did not answer.' });
    for (const r of [result(), undetermined]) {
      const { container, unmount } = render(<AreaCheckCard result={r} loading={false} failed={false} />);
      expect(container.textContent).not.toMatch(BANNED);
      unmount();
    }
    const f = render(<AreaCheckCard result={null} loading={false} failed={true} />);
    expect(f.container.textContent).not.toMatch(BANNED);
  });
});


describe('AreaCheckCard parking', () => {
  const row = (key: string, n: number, clause: string, page: number, heading: string, applies: string): LawFactRow => ({
    fact_key: key, value: n, value_number: n, unit: 'spaces per dwelling', clause, pdf_page: page, quote: 'q', law_version_date: '2026-10-23',
    extra: { section_heading: heading, applies_to: applies },
  });
  const facts = rowsToFacts([
    row('parking_min_s168_2', 1, 's168(2)(c)', 81, 'Non-discretionary development standards—dual occupancies', '(2) apply—'),
    row('parking_min_s172_3', 0.5, 's172(3)(c)', 82, 'Non-discretionary development standards—multi dwelling housing', '(3) for the purposes of multi dwelling housing (terraces)—'),
  ]);

  it('shows each stored minimum with its clause and page, and the maximum-by-another-plan condition', () => {
    render(<AreaCheckCard result={result()} loading={false} failed={false} lawFacts={facts} />);
    const t = screen.getByTestId('area-check-parking').textContent!;
    expect(t).toMatch(/dual occupancies: 1 space per dwelling \(s168\(2\)\(c\), page 81\)/);
    expect(t).toMatch(/multi dwelling housing \(terraces\): 0\.5 spaces per dwelling \(s172\(3\)\(c\), page 82\)/);
    expect(t).toMatch(/only if no environmental planning instrument or development control plan/);
  });

  it('shows no parking when the facts are missing, or when the lot is not in the low and mid-rise area', () => {
    render(<AreaCheckCard result={result()} loading={false} failed={false} lawFacts={null} />);
    expect(screen.queryByTestId('area-check-parking')).toBeNull();
    const no = result({ pathway: 'neither', lmr: { answer: 'no', reason_code: 'beyond_straight_line' } });
    render(<AreaCheckCard result={no} loading={false} failed={false} lawFacts={facts} />);
    expect(screen.queryAllByTestId('area-check-parking')).toHaveLength(0);
  });

  const todFacts = rowsToFacts([
    row('tod_affordable_parking_1_bed', 0.4, 's157(2)(a)', 76, 'Parking', '(2)'),
    row('tod_affordable_parking_3_plus_bed', 1, 's157(2)(c)', 76, 'Parking', '(2)'),
  ]);
  const todResult = () => result({
    pathway: 'tod', lmr: { answer: 'no', reason_code: 'chapter5' },
    tod: { answer: 'yes', standards: {
      tod_affordable_parking_1_bed: { value: 9.9, clause: 'from the Python answer', page: 1, law_version_date: '2026-10-23' },
      tod_fsr: { value: '2.5:1', clause: 's155(4)', page: 76, law_version_date: '2026-10-23' },
    } },
  });

  it('a TOD lot shows the affordable-housing parking from the stored law facts, labelled by bedrooms', () => {
    render(<AreaCheckCard result={todResult()} loading={false} failed={false} lawFacts={todFacts} />);
    const t = screen.getByTestId('area-check-tod-parking').textContent!;
    expect(t).toMatch(/1 bedroom: 0\.4 per dwelling \(s157\(2\)\(a\), page 76\)/);
    expect(t).toMatch(/3 or more bedrooms: 1 per dwelling \(s157\(2\)\(c\), page 76\)/);
    expect(t).not.toMatch(/2\.5|9\.9/);
    expect(screen.queryByTestId('area-check-parking')).toBeNull();
  });

  it('a TOD lot shows no parking figure when the law facts are missing, even if the Python answer carries one', () => {
    render(<AreaCheckCard result={todResult()} loading={false} failed={false} lawFacts={null} />);
    expect(screen.queryByTestId('area-check-tod-parking')).toBeNull();
    expect(document.body.textContent).not.toMatch(/9\.9/);
  });
});
