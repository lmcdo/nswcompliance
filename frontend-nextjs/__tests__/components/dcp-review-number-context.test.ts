/**
 * The flagged-row number panel in the DCP review queue.
 *
 * A reviewer is told "the source check could not match 15 in this rule to the
 * council's PDF" and then has to decide approve/reject. Without showing WHERE
 * that number sits, the only way to decide is to search a 170-page PDF — the
 * cost that made 433 flagged rows unworkable.
 *
 * The dangerous case these tests exist for (Sol cross-review, 2026-09-09):
 * the first version silently discarded a match that was glued to another digit
 * ("15" inside "150") and then reported the number as absent entirely. That
 * buried the single most consequential situation — the gate looked for 15, the
 * rule carries 150, i.e. a control value potentially wrong by a factor of ten —
 * behind reassuring copy about harmless checker splitting.
 */
import { missingNumbers, occurrencesOf } from '@/app/internal/dcp-review/DcpReviewQueue';

describe('missingNumbers', () => {
  it('pulls the tokens out of the gate detail string', () => {
    expect(missingNumbers('numbers not in source: 15, 2.4, 94304')).toEqual(['15', '2.4', '94304']);
  });

  it('is empty for null, empty, or an unrelated detail', () => {
    expect(missingNumbers(null)).toEqual([]);
    expect(missingNumbers('')).toEqual([]);
    expect(missingNumbers('wording not in source: frontage')).toEqual([]);
  });
});

describe('occurrencesOf', () => {
  it('shows a standalone number with the words around it', () => {
    const text = 'Buildings must be set back 6 m from the boundary at ground level.';
    const { standalone, embedded } = occurrencesOf('6', text);
    expect(standalone).toHaveLength(1);
    expect(standalone[0]).toContain('set back 6 m from the boundary');
    expect(embedded).toEqual([]);
  });

  it('keeps a page-footer match, which is the common benign case', () => {
    const text = 'Objectives ... Sydney DCP 2012 - December 2012 2.4-15';
    const { standalone } = occurrencesOf('15', text);
    expect(standalone).toHaveLength(1);
    expect(standalone[0]).toContain('2.4-15');
  });

  it('SURFACES a number found only inside a longer one, instead of hiding it', () => {
    // The gate looked for 15; the rule says 150. Reporting "15 does not appear"
    // would hide a control value that may be wrong by a factor of ten.
    const text = 'The maximum building height is 150 m above ground level.';
    const { standalone, embedded } = occurrencesOf('15', text);
    expect(standalone).toEqual([]);
    expect(embedded).toEqual(['150']);
  });

  it('captures the whole longer token including decimals', () => {
    const text = 'A setback of 12.5 m applies.';
    const { standalone, embedded } = occurrencesOf('12', text);
    expect(standalone).toEqual([]);
    expect(embedded).toEqual(['12.5']);
  });

  it('reports genuinely absent numbers as absent', () => {
    const text = 'Development must respond to the heritage character of the area.';
    expect(occurrencesOf('913', text)).toEqual({ standalone: [], embedded: [] });
  });

  it('survives untyped API input rather than throwing and blanking the panel', () => {
    // new_text arrives as untyped JSON; a non-string must not take out the one
    // screen the human approval gate depends on.
    expect(occurrencesOf('15', null)).toEqual({ standalone: [], embedded: [] });
    expect(occurrencesOf('15', 12345 as unknown as string)).toEqual({ standalone: [], embedded: [] });
    expect(occurrencesOf('', 'some text')).toEqual({ standalone: [], embedded: [] });
  });
});
