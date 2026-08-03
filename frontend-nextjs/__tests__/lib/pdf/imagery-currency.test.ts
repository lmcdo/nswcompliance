/**
 * Campaign item 4 — imagery-currency wording, the single source used by the
 * shadow / solar / flood PDFs' data-currency tables.
 *
 * Rule: state only what the run recorded. An acquisition date when scene
 * identity exists; an explicit not-recorded/not-stated when it does not;
 * never a bare query date dressed as imagery currency, and never 'Most
 * recent pass' for a SAR analysis that has never run (DQ-44).
 */
import {
  s2ImageryCurrency,
  sarImageryCurrency,
  solarImageryCurrency,
} from '@/lib/pdf/imagery-currency';

describe('s2ImageryCurrency (shadow)', () => {
  it('states the acquisition date when the run recorded scene identity', () => {
    expect(s2ImageryCurrency('2026-07-30', '2026-08-03')).toBe(
      'Imagery acquired 2026-07-30; queried 2026-08-03'
    );
  });

  it('says acquisition dates were not recorded when identity is absent', () => {
    const line = s2ImageryCurrency(null, '2026-08-03');
    expect(line).toContain('acquisition dates not recorded for this run');
    expect(line).not.toContain('Imagery acquired');
  });
});

describe('solarImageryCurrency', () => {
  it('states the provider capture month at MONTH precision wording', () => {
    expect(solarImageryCurrency('2024-06', '2026-08-03')).toBe(
      'Imagery captured 2024-06 (month stated by provider); queried 2026-08-03'
    );
  });

  it("treats the backend's 'unknown' sentinel as not stated", () => {
    const line = solarImageryCurrency('unknown', '2026-08-03');
    expect(line).toContain('not stated by provider');
    expect(line).not.toContain('Imagery captured');
  });
});

describe('sarImageryCurrency (flood, DQ-44)', () => {
  it('never implies a pass occurred when no analysis has run', () => {
    expect(sarImageryCurrency(null)).toBe('Not analysed in this report');
    expect(sarImageryCurrency(undefined)).not.toContain('recent pass');
  });

  it('passes a real analysis date through', () => {
    expect(sarImageryCurrency('2026-02-14')).toBe('2026-02-14');
  });
});
