/**
 * The "why is this empty" copy for the Site Report.
 *
 * The rule this file protects: a reader must never be left with a bare label
 * that cannot distinguish "we checked and there is nothing here" from "we did
 * not check" or "the lookup broke". Every branch therefore owes a detail
 * sentence that is longer and more specific than its label, and the caller
 * renders it. These assertions fail if a branch is added that returns a label
 * with no explanation, or an explanation that just repeats the label.
 */
import { describeUnavailable } from '@/app/reports/intelligence-brief/unavailable';

const SECTIONS = [
  ['satellite.bushfire', 'bushfire attack level and vegetation category'],
  ['satellite.flood', 'flood screening'],
  ['satellite.granny_flat', 'secondary dwelling potential'],
  ['planning.overlays', 'planning overlays'],
  ['market_context', 'market context'],
] as const;

const REASONS = [
  null,
  undefined,
  '',
  'not requested',
  'premium data not requested',
  'site history timeout',
  'layer not ingested for this LGA',
  'overlay query did not complete',
  'unavailable',
  'error contacting service',
  'timed out',
  'no prop_id resolved',
  'address not matched',
  'something nobody has seen before',
];

describe('describeUnavailable — every branch explains itself', () => {
  const cases: Array<[string, string, boolean]> = [];
  for (const [section, desc] of SECTIONS) {
    for (const reason of REASONS) {
      for (const satelliteRan of [true, false]) {
        cases.push([String(reason), section, satelliteRan]);
        // exercised below via describeUnavailable(reason, section, ...)
        void desc;
      }
    }
  }

  it('always returns a non-empty label and a non-empty detail', () => {
    for (const [section, desc] of SECTIONS) {
      for (const reason of REASONS) {
        for (const satelliteRan of [true, false]) {
          const u = describeUnavailable(reason, section, satelliteRan, desc);
          expect(u.label.trim().length).toBeGreaterThan(0);
          expect(u.detail.trim().length).toBeGreaterThan(0);
        }
      }
    }
  });

  it('the detail is a real explanation, not a restatement of the label', () => {
    for (const [section, desc] of SECTIONS) {
      for (const reason of REASONS) {
        for (const satelliteRan of [true, false]) {
          const u = describeUnavailable(reason, section, satelliteRan, desc);
          expect(u.detail.trim()).not.toBe(u.label.trim());
          // An explanation is a sentence, not a two-word status.
          expect(u.detail.trim().split(/\s+/).length).toBeGreaterThanOrEqual(5);
        }
      }
    }
  });

  it('never leaks a raw internal reason string as the label', () => {
    const internal = ['layer not ingested for this LGA', 'premium data not requested', 'no prop_id resolved'];
    for (const reason of internal) {
      const u = describeUnavailable(reason, 'planning.overlays', false, 'planning overlays');
      expect(u.label.toLowerCase()).not.toContain('ingested');
      expect(u.label.toLowerCase()).not.toContain('prop_id');
      expect(u.label.toLowerCase()).not.toContain('premium');
    }
  });

  it('returns one of the five declared tones', () => {
    const tones = new Set(['clear', 'optional', 'pending', 'error', 'neutral']);
    for (const [section, desc] of SECTIONS) {
      for (const reason of REASONS) {
        const u = describeUnavailable(reason, section, false, desc);
        expect(tones.has(u.tone)).toBe(true);
      }
    }
  });
});

describe('describeUnavailable — absence is distinguished from failure', () => {
  it('a satellite layer that was never run tells the reader how to run it', () => {
    const u = describeUnavailable(null, 'satellite.flood', false, 'flood screening');
    expect(u.tone).toBe('optional');
    expect(u.detail).toMatch(/tick/i);
    expect(u.detail).toMatch(/re-run|run the report/i);
  });

  it('a satellite layer that RAN but produced nothing does not blame the tickbox', () => {
    const u = describeUnavailable(null, 'satellite.flood', true, 'flood screening');
    expect(u.detail).not.toMatch(/tick/i);
    expect(u.tone).not.toBe('optional');
  });

  it('a genuine retrieval failure reads as a failure, never as a clear result', () => {
    const u = describeUnavailable('overlay query did not complete', 'planning.overlays', false, 'planning overlays');
    expect(u.tone).toBe('error');
    expect(u.detail).toMatch(/retry|run the report again|did not respond/i);
  });

  it('an unrecognised reason is a retrieval miss, never "not part of this report"', () => {
    const u = describeUnavailable('something nobody has seen before', 'planning.overlays', false, 'planning overlays');
    expect(u.tone).toBe('error');
    expect(u.detail.toLowerCase()).not.toContain('not part of this report');
  });

  it('only an explicit "not requested" may say the layer is not part of the report', () => {
    const u = describeUnavailable('not requested', 'planning.overlays', false, 'planning overlays');
    expect(u.tone).toBe('neutral');
    expect(u.detail.toLowerCase()).toContain('not part of this report');
  });
});
