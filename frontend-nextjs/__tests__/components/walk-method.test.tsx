/**
 * WalkMethod: the plain-English box under the walk. The allowance line appears only for a finite figure above zero.
 */
import React from 'react';
import { render } from '@testing-library/react';
import WalkMethod from '@/components/reports/evidence/WalkMethod';
import type { Evidence } from '@/lib/evidence-statement';

const walkWith = (extra?: number): Evidence['walk'] => ({ clause: 's163', page: 77, anchor: 'Penrith station', limit_m: 800, walk_low_m: 454, walk_high_m: 754, detail: null, heuristic: null, walk_best_m: 479, ...(extra === undefined ? {} : { entrance_unmapped_extra_m: extra }) } as Evidence['walk']);

describe('WalkMethod', () => {
  it('renders the five numbered points, the sureness heading and the before-relying heading', () => {
    const { container, getByText } = render(<WalkMethod walk={walkWith()} />);
    expect(getByText('How the walk is calculated')).toBeTruthy();
    expect(getByText('How sure is this?')).toBeTruthy();
    expect(getByText('Before relying on it')).toBeTruthy();
    const items = Array.from(container.querySelectorAll('ol > li'));
    expect(items.map((li) => li.querySelector('strong')?.textContent)).toEqual(['The route.', 'The start.', 'The finish.', 'The distance.', 'Checks.']);
  });

  it.each([['absent', undefined], ['zero', 0], ['negative', -5], ['NaN', NaN], ['Infinity', Infinity]])('has no allowance line or digits when the extra is %s', (_n, v) => {
    const { container } = render(<WalkMethod walk={walkWith(v as number | undefined)} />);
    const text = container.textContent ?? '';
    expect(text).not.toContain('longer');
    expect(text).not.toContain('not on the map');
    expect(/\d/.test(text)).toBe(false);
  });

  it('says up to 120 m longer when the extra is 120', () => {
    const { container } = render(<WalkMethod walk={walkWith(120)} />);
    expect(container.textContent).toContain('The station entrance is not on the map, so the walk is measured to the station building: the real walk could be up to 120 m longer.');
  });

  it('formats a large allowance with a thousands separator', () => {
    const { container } = render(<WalkMethod walk={walkWith(1200)} />);
    expect(container.textContent).toContain('up to 1,200 m longer');
  });
});
