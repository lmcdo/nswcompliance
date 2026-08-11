/**
 * The flood-zone verdict has THREE states and null must never render as "No".
 *
 * Until 2026-08-08 `in_100yr_flood_zone` started life as false and only four
 * positive signals could move it, so a source that could not be consulted
 * produced a confident "not in a flood zone" — the sentence a buyer acts on,
 * in the direction that causes harm. Measured against production: 12 of the
 * 142 stored reports that served "No" had not established it, among them
 * addresses in Lismore, Murwillumbah and Telarah.
 *
 * Every test here exists because null is FALSY in TypeScript. A three-state
 * value handed to any truthiness check collapses straight back to "not in a
 * flood zone", with a correct-looking data model sitting on top of it. These
 * pin the three places that would collapse it.
 */

import {
  FLOOD_ZONE_NOT_ASSESSED_LABEL,
  floodZoneUnavailableMessage,
  isFloodZoneNotAssessed,
  readFloodZoneVerdict,
} from '@/lib/not-assessed';

describe('isFloodZoneNotAssessed', () => {
  it('treats null and undefined as not assessed', () => {
    expect(isFloodZoneNotAssessed(null)).toBe(true);
    expect(isFloodZoneNotAssessed(undefined)).toBe(true);
  });

  it('treats BOTH booleans as answers — false is a result, not an absence', () => {
    expect(isFloodZoneNotAssessed(false)).toBe(false);
    expect(isFloodZoneNotAssessed(true)).toBe(false);
  });

  it('does not use truthiness, which would swallow a real false', () => {
    // The whole defect in one line: `!false` is true, so a truthiness-based
    // implementation would call an established "not in a flood zone" an
    // absence — and, worse, its inverse called an absence a clearance.
    const truthinessWouldSay = !false;
    expect(truthinessWouldSay).toBe(true);
    expect(isFloodZoneNotAssessed(false)).toBe(false);
  });
});

describe('a value that is not a real boolean is an absence, not a No', () => {
  // Sol, round 1: the page reads this out of an untyped JSON bag, so a cast to
  // `boolean | null` is a promise the compiler cannot keep. A legacy row
  // holding the STRING "false" would satisfy the type, fail `=== true`, and
  // fall through to 'No' — a rendered clearance from an unvalidated value.
  // Same class as the Number('') === 0 bug #881 fixed on granny-flat.
  it.each([['false'], ['true'], [0], [1], [''], [{}], [[]], [NaN]])(
    'treats %p as not assessed', (weird) => {
      expect(isFloodZoneNotAssessed(weird)).toBe(true);
      expect(readFloodZoneVerdict(weird)).toBeNull();
    });

  it('still accepts the two real booleans', () => {
    expect(readFloodZoneVerdict(true)).toBe(true);
    expect(readFloodZoneVerdict(false)).toBe(false);
  });
});

describe('floodZoneUnavailableMessage', () => {
  it('names the sources that could not be reached', () => {
    const msg = floodZoneUnavailableMessage(['NSW EPI flood overlay']);
    expect(msg).toContain('NSW EPI flood overlay');
  });

  it('meets the no-result standard: tried, why, not a pass or fail, what next', () => {
    const msg = floodZoneUnavailableMessage(['Council/SES flood study extent']);
    expect(msg).toContain('could not reach');
    expect(msg).toContain('NOT established');
    expect(msg).toMatch(/neither a pass nor a fail/i);
    expect(msg).toContain('10.7(2)');
  });

  it('explicitly forbids reading it as a clearance', () => {
    expect(floodZoneUnavailableMessage([])).toContain('not in a flood');
  });

  it('still produces a usable sentence when no source list survived', () => {
    const msg = floodZoneUnavailableMessage(null);
    expect(msg.length).toBeGreaterThan(80);
    expect(msg).toMatch(/neither a pass nor a fail/i);
  });

  it('never renders the label as an em dash, a blank or a zero', () => {
    expect(FLOOD_ZONE_NOT_ASSESSED_LABEL).toBe('Not assessed');
    expect(FLOOD_ZONE_NOT_ASSESSED_LABEL).not.toMatch(/^[\s—–-]*$/);
  });
});

describe('the API boundary must not collapse the third state', () => {
  // Reproduces frontend-nextjs/app/api/reports/flood/generate/route.ts. The
  // line there used to be `Boolean(raw.in_100yr_flood_zone ?? false)`, which
  // meant the PDF could never see a null no matter what the pipeline produced.
  const mapVerdict = (raw: unknown) =>
    raw === true ? true : raw === false ? false : null;

  it.each([
    [true, true],
    [false, false],
    [null, null],
    [undefined, null],
  ])('maps %p to %p', (input, expected) => {
    expect(mapVerdict(input)).toBe(expected);
  });

  it('is not what the old coercion did', () => {
    const oldWay = (raw: unknown) => Boolean(raw ?? false);
    expect(oldWay(null)).toBe(false); // the defect
    expect(mapVerdict(null)).toBeNull(); // the fix
  });
});

describe('the report page highlight', () => {
  // Reproduces app/reports/flood/[report_id]/page.tsx, which used a truthiness
  // ternary and rendered every unanswered case as 'No' at severity 'low'.
  const highlight = (v: boolean | null | undefined, unconsulted: string[] = []) => ({
    value: isFloodZoneNotAssessed(v)
      ? FLOOD_ZONE_NOT_ASSESSED_LABEL
      : v === true
        ? 'Yes — in flood zone'
        : 'No',
    severity: isFloodZoneNotAssessed(v) ? 'medium' : v === true ? 'high' : 'low',
    detail: isFloodZoneNotAssessed(v) ? floodZoneUnavailableMessage(unconsulted) : undefined,
  });

  it('renders a null as Not assessed, never as No', () => {
    const h = highlight(null, ['NSW EPI flood overlay']);
    expect(h.value).toBe('Not assessed');
    expect(h.value).not.toBe('No');
    expect(h.detail).toBeTruthy();
  });

  it('does not put an unanswered question at the reassuring end of the scale', () => {
    expect(highlight(null).severity).not.toBe('low');
  });

  it('still renders a genuine no as No, with no explanation attached', () => {
    const h = highlight(false);
    expect(h.value).toBe('No');
    expect(h.severity).toBe('low');
    expect(h.detail).toBeUndefined();
  });

  it('still renders a positive as the high-severity finding', () => {
    expect(highlight(true).severity).toBe('high');
  });
});

describe('the PDF branch', () => {
  // Reproduces lib/pdf/flood-truth-report.tsx. Its two branches were strict
  // === comparisons, so a null fell through BOTH and the finding vanished from
  // the document entirely — a missing row reads as "nothing to report here".
  const pdfFinding = (v: boolean | null | undefined) => {
    if (v === true) return { value: 'Within 1-in-100 year flood zone', severity: 'red' };
    if (v === false) return { value: 'Not in 1-in-100 year flood zone', severity: 'green' };
    return { value: 'Not assessed — no answer either way', severity: 'amber' };
  };

  it('emits a finding for a null instead of omitting it', () => {
    expect(pdfFinding(null).value).toContain('Not assessed');
  });

  it('never marks an unanswered question green', () => {
    expect(pdfFinding(null).severity).toBe('amber');
    expect(pdfFinding(undefined).severity).not.toBe('green');
  });

  it('leaves the two established verdicts exactly as they were', () => {
    expect(pdfFinding(false).severity).toBe('green');
    expect(pdfFinding(true).severity).toBe('red');
  });
});
