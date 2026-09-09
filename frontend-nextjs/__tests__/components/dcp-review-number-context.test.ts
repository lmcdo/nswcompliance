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
import {
  looksLikeAControl,
  missingNumbers,
  occurrencesOf,
} from '@/app/internal/dcp-review/DcpReviewQueue';

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

describe('looksLikeAControl', () => {
  // These are the real strings, taken verbatim from the pending queue on
  // 2026-09-09 — the split this function drives is 56 rows that need a human
  // against 354 that do not, so a wrong answer here either buries a real
  // control or manufactures work.
  it.each([
    ['1.8', 'The height of side boundary fencing is not to exceed 1.8m.'],
    ['600', 'no higher than 600mm above the ground level abutting the wall'],
    ['0.2', 'the outer edge of the excavation is within 0.2m of the footings'],
    ['11.5', 'Create a consistent 3 storey (11.5 metres) street wall'],
    ['50', 'sunlight is provided to at least 50% or 35m2 with minimum dimensions'],
    ['20', 'Landscaped street setback 20m min Landscaped side/rear setback'],
  ])('treats %s as a possible control', (num, text) => {
    expect(looksLikeAControl(num, text)).toBe(true);
  });

  it.each([
    ['18', 'Figure 3.18 Glebe Town Hall is an example of an early community building'],
    ['15', 'Sydney DCP 2012 - December 2012 2.4-15'],
    ['24', 'uses to ensure 24 hour activity and surveillance of the streetscape'],
    ['0', 'Surry Hills North ![](images/0.jpg)'],
    ['1893', 'the terraces were built between 1893 and 1905'],
  ])('treats %s as NOT a control', (num, text) => {
    expect(looksLikeAControl(num, text)).toBe(false);
  });

  it('does not mistake a longer decimal for a unit', () => {
    // "3.18" — the ".18" continuation must not read as a unit on "3".
    expect(looksLikeAControl('3', 'see Figure 3.18 for detail')).toBe(false);
  });

  it('survives untyped input', () => {
    expect(looksLikeAControl('15', null)).toBe(false);
    expect(looksLikeAControl('15', 999 as unknown as string)).toBe(false);
  });
});

describe('looksLikeAControl — numeric boundaries (Sol MEDIUM 0.96)', () => {
  it('does not judge the flagged number by a longer number containing it', () => {
    // The gate flagged 5. The rule mentions 5 as a page reference and separately
    // carries an unrelated 15m. Without a leading boundary the scan finds the "5"
    // inside "15m" and wrongly tells the reviewer the flagged 5 is a measurement.
    expect(looksLikeAControl('5', 'see page 5 for detail; the wall is 15m high')).toBe(false);
  });

  it('still detects the number when it is genuinely the measurement', () => {
    expect(looksLikeAControl('5', 'the wall is 5m high')).toBe(true);
  });

  it('is not fooled by a decimal that merely starts with the flagged number', () => {
    expect(looksLikeAControl('11', 'a street wall of 11.5 metres applies')).toBe(false);
  });
});
