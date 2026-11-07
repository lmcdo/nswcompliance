/**
 * The card says what the area check measured, in plain words, and never says "can't tell" or "confirmed".
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
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

const BANNED = /can'?t tell|cannot tell|confirmed|eligible|compliant/i;

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

  it('a failed or missing result says "Not determined" with a next step, and loading says it is checking', () => {
    const { rerender } = render(<AreaCheckCard result={null} loading={false} failed={true} />);
    expect(screen.getByTestId('area-check-failed').textContent).toMatch(/^\s*Not determined:[\s\S]*Spatial Viewer/);
    rerender(<AreaCheckCard result={null} loading={true} failed={false} />);
    expect(screen.getByTestId('area-check-loading')).toBeTruthy();
  });

  it('none of the rendered text uses the words the product avoids', () => {
    const undetermined = result({ pathway: 'unknown', lmr: { answer: 'cant_tell' }, headline: 'Not determined: a map did not answer.' });
    for (const r of [result(), undetermined]) {
      const { container, unmount } = render(<AreaCheckCard result={r} loading={false} failed={false} />);
      expect(container.textContent).not.toMatch(BANNED);
      unmount();
    }
    const f = render(<AreaCheckCard result={null} loading={false} failed={true} />);
    expect(f.container.textContent).not.toMatch(BANNED);
  });
});
