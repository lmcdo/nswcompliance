import { buildScale, cardRows, distanceWords, fmtNum, lgaName, rowTitle, sentence, statusOf, tally, verdictWords, walkVerdict } from '@/lib/evidence-summary';
import type { Evidence, EvidenceExclusion } from '@/lib/evidence-statement';

type Walk = Evidence['walk'];
const walk = (o: Partial<Walk> = {}): Walk => ({ clause: null, page: null, anchor: null, limit_m: 800, walk_low_m: 454, walk_high_m: 754, detail: null, heuristic: null, ...o });
const row = (o: Partial<EvidenceExclusion> = {}): EvidenceExclusion => ({ para: 'a', clause: 's1', page: 1, law_words: 'w', result: 'clear', result_words: 'r', detail: null, source_checked: 's', ...o });

describe('fmtNum', () => {
  it('groups thousands and rounds to a whole number', () => {
    expect(fmtNum(1103)).toBe('1,103');
    expect(fmtNum(1234.5)).toBe('1,235');
    expect(fmtNum(0.4)).toBe('0');
    expect(fmtNum(800)).toBe('800');
  });
  it('does not throw on NaN (prints NaN, never a made-up figure)', () => {
    expect(fmtNum(NaN)).toBe('NaN');
  });
});

describe('distanceWords', () => {
  it('rounds before choosing the unit, so 999.96 m is 1.0 km and never 1000 m', () => {
    expect(distanceWords(999.96)).toBe('1.0 km');
    expect(distanceWords(999.94)).toBe('999.9 m');
  });
  it('uses metres under a kilometre, one decimal, dropping a trailing .0', () => {
    expect(distanceWords(5)).toBe('5 m');
    expect(distanceWords(12.34)).toBe('12.3 m');
    expect(distanceWords(454.5)).toBe('454.5 m');
  });
  it('uses kilometres from exactly 1000 m', () => {
    expect(distanceWords(1000)).toBe('1.0 km');
    expect(distanceWords(9900)).toBe('9.9 km');
    expect(distanceWords(999)).toBe('999 m');
  });
  it('says it could not be read for NaN, infinity and negatives, never a number', () => {
    for (const bad of [NaN, Infinity, -1]) expect(distanceWords(bad)).toBe('a distance that could not be read');
  });
  it('accepts zero', () => {
    expect(distanceWords(0)).toBe('0 m');
  });
});

describe('walkVerdict', () => {
  it('is over when even the shortest case is over the limit, with the gap', () => {
    const v = walkVerdict(walk({ limit_m: 800, walk_low_m: 850, walk_high_m: 950 }));
    expect(v).toMatchObject({ kind: 'over', limit: 800, low: 850, high: 950, gapM: 50 });
  });
  it('is within when even the longest case is inside the limit, with the gap', () => {
    const v = walkVerdict(walk({ limit_m: 800, walk_low_m: 454, walk_high_m: 754 }));
    expect(v).toMatchObject({ kind: 'within', gapM: 46 });
  });
  it('straddles when the range crosses the limit, and gives no gap', () => {
    const v = walkVerdict(walk({ limit_m: 800, walk_low_m: 700, walk_high_m: 900 }));
    expect(v.kind).toBe('straddles');
    expect(v.gapM).toBeNull();
  });
  it('treats a limit equal to the low end as straddles (low is not over), and equal to the high end as within with gap 0', () => {
    expect(walkVerdict(walk({ limit_m: 700, walk_low_m: 700, walk_high_m: 900 })).kind).toBe('straddles');
    const v = walkVerdict(walk({ limit_m: 900, walk_low_m: 700, walk_high_m: 900 }));
    expect(v.kind).toBe('within');
    expect(v.gapM).toBe(0);
  });
  it('is unknown when any of limit, low, high is null or not finite, or the range is back to front', () => {
    expect(walkVerdict(walk({ limit_m: null })).kind).toBe('unknown');
    expect(walkVerdict(walk({ walk_low_m: null })).kind).toBe('unknown');
    expect(walkVerdict(walk({ walk_high_m: null })).kind).toBe('unknown');
    expect(walkVerdict(walk({ walk_high_m: NaN })).kind).toBe('unknown');
    expect(walkVerdict(walk({ limit_m: Infinity })).kind).toBe('unknown');
    const back = walkVerdict(walk({ walk_low_m: 900, walk_high_m: 700 }));
    expect(back.kind).toBe('unknown');
    expect(back.gapM).toBeNull();
  });
  it('keeps the numbers it did read when unknown, and nulls the ones it did not', () => {
    const v = walkVerdict(walk({ limit_m: 800, walk_low_m: null, walk_high_m: 754 }));
    expect(v).toMatchObject({ limit: 800, low: null, high: 754 });
  });
  it('uses walk_best_m when given', () => {
    expect(walkVerdict(walk({ walk_best_m: 500 })).best).toBe(500);
  });
  it('derives the measured walk as low plus its margin when walk_best_m is absent, and null when there is no margin', () => {
    expect(walkVerdict(walk({ walk_low_m: 454, margin_low_m: 25 })).best).toBe(479);
    expect(walkVerdict(walk({ walk_low_m: 454 })).best).toBeNull();
    expect(walkVerdict(walk({ walk_low_m: null, margin_low_m: 25 })).best).toBeNull();
    expect(walkVerdict(walk({ walk_best_m: NaN, walk_low_m: 454, margin_low_m: 25 })).best).toBe(479);
  });
});

describe('verdictWords', () => {
  it('over: names the limit, the gap, and says the lot does not meet the test', () => {
    const w = verdictWords(walkVerdict(walk({ limit_m: 800, walk_low_m: 1103, walk_high_m: 1203 })), null);
    expect(w.pill).toBe('Over the 800 m limit');
    expect(w.margin).toBe('Even the shortest case is 303 m over.');
    expect(w.sentence).toContain('longer than 800 m');
    expect(w.bottom).toBe('On this measure the lot does not meet the walking test.');
  });
  it('within: names the limit and the gap under it', () => {
    const w = verdictWords(walkVerdict(walk({ limit_m: 800, walk_low_m: 454, walk_high_m: 754 })), null);
    expect(w.pill).toBe('Within the 800 m limit');
    expect(w.margin).toBe('Even the longest case is 46 m under.');
    expect(w.sentence).toContain('shorter than 800 m');
    expect(w.bottom).toBe('On this measure the lot meets the walking test.');
  });
  it('straddles: says the tool cannot say, with no margin line', () => {
    const w = verdictWords(walkVerdict(walk({ walk_low_m: 700, walk_high_m: 900 })), null);
    expect(w.pill).toBe('The range crosses the 800 m limit');
    expect(w.margin).toBeNull();
    expect(w.bottom).toContain('cannot say whether the lot meets the walking test');
  });
  it('unknown: uses the payload detail as the sentence when there is one, else a fixed line, and never a verdict', () => {
    const v = walkVerdict(walk({ walk_low_m: null }));
    expect(verdictWords(v, 'no route to the station').sentence).toBe('no route to the station');
    expect(verdictWords(v, null).sentence).toBe('No walking range was measured.');
    const w = verdictWords(v, null);
    expect(w.pill).toBe('No walking range');
    expect(w.margin).toBeNull();
    expect(w.bottom).toBe('No walking range was measured, so the walking test could not be applied.');
  });
  it('never uses the word complies', () => {
    for (const o of [{ walk_low_m: 900, walk_high_m: 950 }, { walk_low_m: 100, walk_high_m: 200 }, { walk_low_m: 700, walk_high_m: 900 }, { walk_low_m: null }]) {
      expect(JSON.stringify(verdictWords(walkVerdict(walk(o)), null)).toLowerCase()).not.toContain('complies');
    }
  });
});

describe('buildScale', () => {
  it('builds a 100 m step axis for a narrow span, with percentages that place each value', () => {
    const m = buildScale(800, 454, 754, 479)!;
    expect(m.min).toBe(300);
    expect(m.max).toBe(900);
    expect(m.ticks).toEqual([300, 400, 500, 600, 700, 800, 900]);
    expect(m.limitPct).toBeCloseTo(83.333, 2);
    expect(m.bandLeftPct).toBeCloseTo(25.667, 2);
    expect(m.bandWidthPct).toBeCloseTo(50, 5);
    expect(m.bestPct).toBeCloseTo(29.833, 2);
  });
  it('widens the step for a wide span and never starts below zero', () => {
    const mid = buildScale(800, 100, 900, null)!;
    expect(mid.min).toBe(0);
    expect(mid.ticks.slice(0, 3)).toEqual([0, 200, 400]);
    const wide = buildScale(800, 100, 2100, null)!;
    expect(wide.ticks.slice(0, 3)).toEqual([0, 500, 1000]);
    expect(wide.max).toBe(3000);
  });
  it('places the limit right of a range entirely inside it and left of one entirely over it', () => {
    const inside = buildScale(800, 100, 200, null)!;
    expect(inside.limitPct).toBeGreaterThan(inside.bandLeftPct + inside.bandWidthPct);
    const over = buildScale(800, 900, 1000, null)!;
    expect(over.limitPct).toBeLessThan(over.bandLeftPct);
  });
  it('handles a limit equal to low or to high (zero distance, still drawn)', () => {
    const a = buildScale(700, 700, 900, null)!;
    expect(a.limitPct).toBeCloseTo(a.bandLeftPct, 5);
    const b = buildScale(900, 700, 900, null)!;
    expect(b.limitPct).toBeCloseTo(b.bandLeftPct + b.bandWidthPct, 5);
    const flat = buildScale(800, 800, 800, null)!;
    expect(flat.bandWidthPct).toBe(0);
  });
  it('leaves bestPct null when best is null or not finite', () => {
    expect(buildScale(800, 454, 754, null)!.bestPct).toBeNull();
    expect(buildScale(800, 454, 754, NaN)!.bestPct).toBeNull();
  });
  it('returns null when the numbers cannot be drawn', () => {
    expect(buildScale(null, 454, 754, null)).toBeNull();
    expect(buildScale(800, null, 754, null)).toBeNull();
    expect(buildScale(800, 454, null, null)).toBeNull();
    expect(buildScale(NaN, 454, 754, null)).toBeNull();
    expect(buildScale(800, 454, Infinity, null)).toBeNull();
    expect(buildScale(0, 454, 754, null)).toBeNull();
    expect(buildScale(-5, 454, 754, null)).toBeNull();
    expect(buildScale(800, 754, 454, null)).toBeNull();
    expect(buildScale(800, -1, 754, null)).toBeNull();
  });
});

describe('tally', () => {
  const rows = [row({ para: 'a', result: 'clear' }), row({ para: 'b', result: 'excludes' }), row({ para: 'c', result: 'warn' }), row({ para: 'd', result: 'clear' }), row({ para: 'e', result: 'not_checked' })];
  it('counts clear, excluded and the rest from the rows', () => {
    const t = tally(rows);
    expect(t.total).toBe(5);
    expect(t.clear).toBe(2);
    expect(t.excludes).toBe(1);
    expect(t.other.map((r) => r.para)).toEqual(['b', 'c', 'e']);
    expect(t.clearRows.map((r) => r.para)).toEqual(['a', 'd']);
  });
  it('treats an unknown result as not clear', () => {
    const t = tally([row({ result: 'weird' })]);
    expect(t.clear).toBe(0);
    expect(t.other).toHaveLength(1);
  });
  it('is all zero for no rows', () => {
    expect(tally([])).toEqual({ total: 0, clear: 0, excludes: 0, other: [], clearRows: [] });
  });
});

describe('cardRows', () => {
  it('keeps every non-clear row and a clear row only when it carries facts', () => {
    const rows = [
      row({ para: 'plain', result: 'clear' }),
      row({ para: 'facts', result: 'clear', facts: { flood_state: 'outside', nearest_m: 300 } }),
      row({ para: 'emptyfacts', result: 'clear', facts: {} }),
      row({ para: 'nullfacts', result: 'clear', facts: null }),
      row({ para: 'ex', result: 'excludes' }),
      row({ para: 'nc', result: 'not_checked' }),
    ];
    expect(cardRows(rows).map((r) => r.para)).toEqual(['facts', 'ex', 'nc']);
  });
  it('is empty for no rows', () => {
    expect(cardRows([])).toEqual([]);
  });
});

describe('lgaName', () => {
  it('changes only the case', () => {
    expect(lgaName('KU-RING-GAI')).toBe('Ku-ring-gai');
    expect(lgaName('PENRITH')).toBe('Penrith');
    expect(lgaName('CITY OF SYDNEY')).toBe('City of Sydney');
    expect(lgaName('  blacktown ')).toBe('Blacktown');
  });
  it('keeps small words small except at the start', () => {
    expect(lgaName('THE HILLS AND DISTRICT')).toBe('The Hills and District');
  });
  it('returns null for null, undefined, empty and blank', () => {
    for (const v of [null, undefined, '', '   ']) expect(lgaName(v)).toBeNull();
  });
});

describe('sentence', () => {
  it('capitalises the first letter and leaves the rest', () => {
    expect(sentence('the lot is clear')).toBe('The lot is clear');
    expect(sentence('aBC')).toBe('ABC');
  });
  it('returns an empty string unchanged', () => {
    expect(sentence('')).toBe('');
  });
});

describe('rowTitle', () => {
  it('prefers the title, then the clause, then a fixed fallback', () => {
    expect(rowTitle({ title: 'Flooding', clause: 's164(1)(f)' })).toBe('Flooding');
    expect(rowTitle({ title: null, clause: 's164(1)(f)' })).toBe('s164(1)(f)');
    expect(rowTitle({})).toBe('Paragraph not named');
    expect(rowTitle({ title: null, clause: null })).toBe('Paragraph not named');
  });
});

describe('statusOf', () => {
  it('gives a distinct symbol and words for each result', () => {
    expect(statusOf('clear')).toEqual({ symbol: '✓', words: 'None found' });
    expect(statusOf('excludes')).toEqual({ symbol: '■', words: 'Excluded' });
    expect(statusOf('warn')).toEqual({ symbol: '◐', words: 'Check needed' });
    expect(statusOf('not_checked')).toEqual({ symbol: '○', words: 'Not checked' });
  });
  it('treats an unknown or empty result as could not be determined, never as clear', () => {
    expect(statusOf('weird')).toEqual({ symbol: '○', words: 'Could not be determined' });
    expect(statusOf('')).toEqual({ symbol: '○', words: 'Could not be determined' });
  });
});
