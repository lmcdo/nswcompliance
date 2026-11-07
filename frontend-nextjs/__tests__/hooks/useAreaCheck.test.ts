/**
 * lmrFlags turns the area check's answer into the true / false / null the rest of the page already understands.
 * The rule that matters: a borderline or undetermined lot is null, never true and never false, so no page claims an area it did not measure.
 * @jest-environment node
 */
import { lmrFlags, areaKey, isAreaCheck, type AreaCheck } from '@/hooks/useAreaCheck';

const base = (lmr: Partial<AreaCheck['lmr']>): AreaCheck => ({
  pathway: 'lmr', headline: 'h', tod: { answer: 'no' }, warnings: [], not_checked: [], notes: [], law_version_date: '2026-10-23',
  lmr: { answer: 'yes', ...lmr },
});

describe('lmrFlags', () => {
  it('yes is true; no is false', () => {
    expect(lmrFlags(base({ answer: 'yes' }))).toEqual({ inLmrArea: true, lmrExcluded: null });
    expect(lmrFlags(base({ answer: 'no', reason_code: 'beyond_straight_line' }))).toEqual({ inLmrArea: false, lmrExcluded: null });
  });

  it('a lot on the exclusion map is excluded (true) as well as not in the area', () => {
    expect(lmrFlags(base({ answer: 'no', reason_code: 'exclusion_map' }))).toEqual({ inLmrArea: false, lmrExcluded: true });
  });

  it('borderline, not determined, a missing result or a malformed one are null — never a guess', () => {
    for (const a of ['borderline', 'cant_tell'] as const) {
      expect(lmrFlags(base({ answer: a }))).toEqual({ inLmrArea: null, lmrExcluded: null });
    }
    expect(lmrFlags(null)).toEqual({ inLmrArea: null, lmrExcluded: null });
    expect(lmrFlags({} as AreaCheck)).toEqual({ inLmrArea: null, lmrExcluded: null });
  });

  it('a yes that carries a warning (an exclusion not ruled out) is null for the rest of the page; the card still shows the warning', () => {
    const w = { clause: 's164(1)(f1)', page: 78, detail: 'flood extent not checked' };
    const top = base({ answer: 'yes' });
    top.warnings = [w];
    expect(lmrFlags(top)).toEqual({ inLmrArea: null, lmrExcluded: null });
    const inner = base({ answer: 'yes', warnings: [w] });
    expect(lmrFlags(inner).inLmrArea).toBeNull();
    expect(lmrFlags(base({ answer: 'yes' })).inLmrArea).toBe(true);
  });
});

describe('areaKey', () => {
  it('is null unless both coordinates are finite numbers', () => {
    expect(areaKey(undefined, 151)).toBeNull();
    expect(areaKey(-33.8, NaN)).toBeNull();
    expect(areaKey(-33.8, 151.1)).toBe('-33.8,151.1');
  });
});

describe('isAreaCheck', () => {
  it('accepts a full answer', () => {
    expect(isAreaCheck(base({ answer: 'yes' }))).toBe(true);
  });

  it('rejects a partial or mismatched payload, so it becomes a failure and not a yes', () => {
    expect(isAreaCheck({ lmr: { answer: 'yes' } })).toBe(false);
    expect(isAreaCheck(null)).toBe(false);
    expect(isAreaCheck({ ...base({ answer: 'yes' }), tod: undefined })).toBe(false);
    expect(isAreaCheck({ ...base({ answer: 'yes' }), warnings: undefined })).toBe(false);
    expect(isAreaCheck(base({ answer: 'maybe' as never }))).toBe(false);
  });
});
