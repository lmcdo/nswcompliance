/**
 * Two words the reader is told: the figures are headlines (the surrounding wording can add tests or exceptions), and where a council sets a
 * control by map, on merit or in general wording the clause shown is the closest, not a figure. Fixtures only.
 * prior-art-checked: plan-brief.test.tsx covers the view and the standing note's presence; neither covered a per-clause note or the wording of the caveat.
 */
import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { BRIEF_NOTE, briefRowNote, shapeBriefRows, type BriefItem, type StoredBriefRow } from '@/lib/plan-brief';
import { PlanBriefView } from '@/components/compliance/PlanBrief';

function item(id: number, over: Partial<BriefItem> = {}): BriefItem {
  return { id, verdict: 'MIGHT', text: `Clause ${id} text.`, page: 10 + id, pageLabel: null, clauseLabel: `3.1.${id}`, sectionHeader: null, chapterKey: 'part-3', pageProven: true, ...over };
}
const stored = (row_type: string, rank: number, it: BriefItem): StoredBriefRow => ({ row_type, rank, item: it });

describe('briefRowNote', () => {
  test('a closest-clause reason becomes a sentence for the reader', () => {
    expect(briefRowNote('closest clause: the council sets this by map, on merit or in general wording, not as a single figure'))
      .toBe('The council sets this by map, on merit or in general wording, not as a single figure');
  });
  test('every other reason gives no note', () => {
    expect(briefRowNote('strict pick: the clause states the requirement for a house')).toBeNull();
    expect(briefRowNote('other: setbacks per Table 3.1.2-a')).toBeNull();
    expect(briefRowNote('')).toBeNull();
    expect(briefRowNote(null)).toBeNull();
    expect(briefRowNote(undefined)).toBeNull();
  });
  test('a reason that only says closest clause with nothing after it gives no note', () => {
    expect(briefRowNote('closest clause:')).toBeNull();
    expect(briefRowNote('closest clause:   ')).toBeNull();
  });
  test('a reason that merely contains the words is not a closest clause', () => {
    expect(briefRowNote('this is not the closest clause: it is a figure')).toBeNull();
  });
});

describe('the standing note', () => {
  test('says these are headline requirements and that surrounding wording can add tests or exceptions', () => {
    expect(BRIEF_NOTE).toMatch(/headline requirements/);
    expect(BRIEF_NOTE).toMatch(/tests or exceptions/);
    expect(BRIEF_NOTE).toMatch(/matching the neighbours|assessment on merit/);
  });
  test('keeps the indicative wording and uses none of the banned claim words', () => {
    expect(BRIEF_NOTE).toMatch(/Indicative only/);
    expect(BRIEF_NOTE.toLowerCase()).not.toMatch(/verified|complies|compliant|approved|guarantee|reliable|accurate|ensure/);
  });
});

describe('a closest-clause row on the page', () => {
  test('shows its note above the clause, and a normal clause shows none', () => {
    const rows = shapeBriefRows([
      stored('front_setback', 1, item(1, { note: 'The council sets this by map, on merit or in general wording, not as a single figure' })),
      stored('side_setback', 1, item(2)),
    ]);
    render(<PlanBriefView rows={rows} />);
    const front = within(screen.getByTestId('brief-row-front'));
    expect(front.getByTestId('brief-closest')).toHaveTextContent(/Closest clause in the plan: The council sets this by map, on merit/);
    expect(within(screen.getByTestId('brief-row-side')).queryByTestId('brief-closest')).toBeNull();
  });
  test('the note is plain text, not markup', () => {
    const rows = shapeBriefRows([stored('front_setback', 1, item(1, { note: '<b>bold</b>' }))]);
    const { container } = render(<PlanBriefView rows={rows} />);
    expect(container.querySelector('b')).toBeNull();
    expect(screen.getByTestId('brief-closest')).toHaveTextContent('<b>bold</b>');
  });
});
