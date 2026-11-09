/**
 * Plan brief: fixtures only (no database, no network).
 * zone grouping, row shaping (proven rows left out, one clause once), the view (3 shown, show more, empty row, wording).
 * prior-art-checked: your-project-summary.test.tsx covers the proven-figure table; nothing covered the plan-clause block.
 */
import React from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import {
  BRIEF_DEV_TYPES, BRIEF_EMPTY_TEXT, BRIEF_NOTE, isBriefDevType, shapeBriefRows, zoneGroup,
  type BriefItem, type StoredBriefRow,
} from '@/lib/plan-brief';
import { PlanBriefView } from '@/components/compliance/PlanBrief';
import { whereInPlan } from '@/lib/plan-brief';

function item(id: number, over: Partial<BriefItem> = {}): BriefItem {
  return { id, verdict: 'MIGHT', text: `Clause ${id} text.`, page: 10 + id, pageLabel: null, clauseLabel: `3.1.${id}`, sectionHeader: null, chapterKey: 'part-3', pageProven: true, ...over };
}
const stored = (row_type: string, rank: number, it: BriefItem): StoredBriefRow => ({ row_type, rank, item: it });

describe('zoneGroup', () => {
  test.each([['R2', 'R2'], ['R2 Low Density Residential', 'R2'], ['r3', 'R3'], ['R4:High', 'R4'], ['B4', 'B'], ['MU1', 'B'], ['E1', 'B'], ['IN1', 'ANY'], ['RU5', 'ANY'], [null, 'ANY'], ['', 'ANY']])( // noqa: zone-codes -- test inputs for the brief's zone-group mapping
    '%s -> %s', (zone, want) => expect(zoneGroup(zone as string | null)).toBe(want));
});

describe('isBriefDevType', () => {
  test('accepts the six housing types, rejects anything else', () => {
    for (const t of BRIEF_DEV_TYPES) expect(isBriefDevType(t)).toBe(true);
    expect(isBriefDevType('industrial_development')).toBe(false);
    expect(isBriefDevType(null)).toBe(false);
  });
});

describe('shapeBriefRows', () => {
  test('groups by row in table order, ranks within a row', () => {
    const rows = shapeBriefRows([
      stored('side_setback', 2, item(2)), stored('front_setback', 1, item(1)), stored('side_setback', 1, item(3)),
    ]);
    expect(rows.map((r) => r.key).slice(0, 3)).toEqual(['front', 'side', 'rear']);
    expect(rows.find((r) => r.key === 'side')!.items.map((i) => i.id)).toEqual([3, 2]);
  });

  test('a row with a proven figure is left out', () => {
    const rows = shapeBriefRows([stored('front_setback', 1, item(1)), stored('side_setback', 1, item(2))], new Set(['front']));
    expect(rows.find((r) => r.key === 'front')).toBeUndefined();
    expect(rows.find((r) => r.key === 'side')!.items).toHaveLength(1);
  });

  test('landscaped area and deep soil share a row; one clause is listed once', () => {
    const shared = item(7);
    const rows = shapeBriefRows([stored('landscaping_min', 1, shared), stored('deep_soil_min', 1, shared), stored('deep_soil_min', 2, item(8))]);
    expect(rows.find((r) => r.key === 'landscape')!.items.map((i) => i.id)).toEqual([7, 8]);
  });

  test('a row nothing matched is kept, empty (the view says so; it never invents)', () => {
    const rows = shapeBriefRows([stored('front_setback', 1, item(1))]);
    expect(rows.find((r) => r.key === 'rear')!.items).toEqual([]);
  });
});

describe('PlanBriefView', () => {
  const five = [1, 2, 3, 4, 5].map((n) => stored('front_setback', n, item(n, { verdict: n === 1 ? 'APPLIES' : 'MIGHT' })));

  test('shows 3 clauses first, 2 more on request, with page and tag', () => {
    render(<PlanBriefView rows={shapeBriefRows(five)} />);
    const row = screen.getByTestId('brief-row-front');
    expect(within(row).getAllByTestId('brief-item')).toHaveLength(3);
    expect(within(row).getAllByTestId('brief-tag')[0]).toHaveTextContent('Applies');
    expect(within(row).getAllByTestId('brief-tag')[1]).toHaveTextContent('May apply');
    expect(within(row).getAllByTestId('brief-place')[0]).toHaveTextContent('clause 3.1.1, page 11');
    fireEvent.click(within(row).getByTestId('brief-more'));
    expect(within(row).getAllByTestId('brief-item')).toHaveLength(5);
    expect(within(row).getByTestId('brief-more')).toHaveTextContent('Show fewer');
  });

  test('an empty row says so and links to the plan', () => {
    render(<PlanBriefView rows={shapeBriefRows([])} planUrl="https://example.test/plan.pdf" />);
    const empty = within(screen.getByTestId('brief-row-rear')).getByTestId('brief-empty');
    expect(empty).toHaveTextContent(BRIEF_EMPTY_TEXT);
    expect(within(empty).getByRole('link', { name: /open the plan/i })).toHaveAttribute('href', 'https://example.test/plan.pdf');
  });

  test('wording stays indicative: none of the banned claim words appear', () => {
    const { container } = render(<PlanBriefView rows={shapeBriefRows(five)} />);
    expect(screen.getByTestId('brief-note')).toHaveTextContent(BRIEF_NOTE);
    expect(container.textContent!.toLowerCase()).not.toMatch(/verified|complies|compliant|approved|guarantee/);
  });

  test('renders nothing when there are no rows (flag off or council not built)', () => {
    const { container } = render(<PlanBriefView rows={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});


describe('where a clause sits in the plan', () => {
  test('the chapter name comes first, then the section heading', () => {
    expect(whereInPlan({ chapterLabel: 'Part 6.1 Low density residential', sectionHeader: '# 6.1.3 Front setbacks' }))
      .toBe('Part 6.1 Low density residential \u203a 6.1.3 Front setbacks');
  });

  test('a section heading that repeats the chapter name is not shown twice', () => {
    expect(whereInPlan({ chapterLabel: 'Part 4', sectionHeader: 'Part 4' })).toBe('Part 4');
  });

  test('nothing is shown when the plan gives neither', () => {
    expect(whereInPlan({ chapterLabel: null, sectionHeader: null })).toBe('');
    expect(whereInPlan({})).toBe('');
  });

  test('the card shows where the clause sits', () => {
    render(<PlanBriefView rows={shapeBriefRows([stored('front_setback', 1, item(1, { chapterLabel: 'Part 4 Multi dwelling housing', sectionHeader: '4.2 Setbacks' }))])} />);
    expect(screen.getByTestId('brief-where')).toHaveTextContent('Part 4 Multi dwelling housing');
    expect(screen.getByTestId('brief-where')).toHaveTextContent('4.2 Setbacks');
  });
});
