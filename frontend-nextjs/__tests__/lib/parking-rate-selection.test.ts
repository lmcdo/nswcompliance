import { selectParkingRate, type ParkingControlRow } from '@/lib/parking-rate-selection';
import { readFileSync } from 'fs';
import { join } from 'path';

/**
 * The failure this guards is a WRONG NUMBER, not a crash: hand back a visitor
 * parking rate as though it were the dwelling rate and nothing errors, nothing
 * logs, and the answer is quietly wrong. That is the DQ-32 class.
 *
 * Mutation note: a `selectParkingRate` stubbed to always return the first row
 * fails `states no single rate when every row is conditioned`; one stubbed to
 * return `{kind:'none'}` fails the single-row tests. Neither direction passes.
 */
const row = (over: Partial<ParkingControlRow> = {}): ParkingControlRow => ({
  value_min: 1,
  value_max: null,
  unit: 'spaces/dwelling',
  condition: null,
  source_text: 'Provide 1 space per dwelling.',
  section_ref: 'Table 3',
  dcp_version: 'Comprehensive Inner West DCP 2016 (Ashfield)',
  pdf_page: 12,
  dev_type: 'dwelling_house',
  ...over,
});

describe('selectParkingRate', () => {
  it('returns none for an empty result', () => {
    expect(selectParkingRate([]).kind).toBe('none');
  });

  it('states the rate when exactly one row is unconditioned', () => {
    const got = selectParkingRate([row()]);
    expect(got.kind).toBe('single');
    if (got.kind !== 'single') throw new Error('unreachable');
    expect(got.base.rate).toBe(1);
    expect(got.base.applies_when).toBeNull();
    expect(got.dcpVersion).toContain('Ashfield');
  });

  it('keeps conditioned siblings as ADDITIONAL, not as the rate', () => {
    // Real Ashfield shape: base resident rate + a visitor rate.
    const got = selectParkingRate([
      row({ value_min: 1 }),
      row({ value_min: 0.2, condition: 'visitor parking; plus 1 car wash bay' }),
    ]);
    if (got.kind !== 'single') throw new Error('expected single');
    expect(got.base.rate).toBe(1);
    expect(got.additional).toHaveLength(1);
    expect(got.additional[0].rate).toBe(0.2);
    expect(got.additional[0].applies_when).toMatch(/visitor/);
  });

  it('states NO single rate when every row is conditioned', () => {
    // The 96-of-123 case. Picking either of these would be a fabricated answer.
    const got = selectParkingRate([
      row({ value_min: 1, condition: 'R3 zone; plus 1 space per 5 x 2-bedroom' }),
      row({ value_min: 0.2, condition: 'visitor parking' }),
    ]);
    expect(got.kind).toBe('conditional');
    if (got.kind !== 'conditional') throw new Error('unreachable');
    expect(got.rates).toHaveLength(2);
    expect(got.rates.every((r) => r.applies_when !== null)).toBe(true);
  });

  it('refuses to break a tie between two unconditioned rows', () => {
    const got = selectParkingRate([row({ value_min: 1 }), row({ value_min: 2 })]);
    expect(got.kind).toBe('conditional');
  });

  it('treats a whitespace-only condition as no condition', () => {
    expect(selectParkingRate([row({ condition: '   ' })]).kind).toBe('single');
  });

  it('parses numeric strings from pg and nulls anything unparseable', () => {
    const got = selectParkingRate([row({ value_min: '0.75' as unknown as string, value_max: 'n/a' as unknown as string })]);
    if (got.kind !== 'single') throw new Error('expected single');
    expect(got.base.rate).toBe(0.75);
    // Not NaN — a caller checking `rate !== null` must be able to trust it.
    expect(got.base.rate_max).toBeNull();
  });

  it('defaults a missing unit rather than emitting undefined', () => {
    const got = selectParkingRate([row({ unit: null })]);
    if (got.kind !== 'single') throw new Error('expected single');
    expect(got.base.unit).toBe('spaces');
  });
});

/**
 * Source-level guards, same pattern as __tests__/api/capacity-repoint.test.ts:
 * the route cannot be unit-run without a live DB, so these fail the moment the
 * query is repointed back at the dropped table or loses a currency guard.
 */
describe('parking-rates route source', () => {
  const raw = readFileSync(join(process.cwd(), 'app/api/tod/parking-rates/route.ts'), 'utf8');
  // Comments are stripped first: the guard is about what the route EXECUTES, and
  // the comment above the query legitimately names the dropped table it was
  // repointed away from. Matching prose would forbid documenting the fix.
  const src = raw.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|\s)\/\/[^\n]*/g, ' ');

  it('sources DCP rows from the guarded proxy, never inline SQL (item 5 FLIP)', () => {
    // FLIPPED 2026-08-03: previously pinned the route's own
    // `FROM dcp_setback_controls` query and its guard predicates. The guards
    // (is_current strict, needs_review exclusion, zone, deterministic order)
    // now live solely in conveyancing_db.fetch_dcp_setbacks behind
    // /pipeline/dcp-controls; this route filters car_parking rows and sorts
    // for presentation.
    // (is_current = TRUE + needs_review guards live in fetch_dcp_setbacks
    // behind the proxy — that is the point of the flip.)
    expect(src).not.toMatch(/FROM dcp_setback_controls/);
    expect(src).toMatch(/fetchDcpControls\(/);
    expect(src).toMatch(/semantic_type === 'car_parking'/);
  });

  it('never queries the dropped `dcps` table or its phantom columns', () => {
    expect(src).not.toMatch(/JOIN\s+dcps\b/);
    expect(src).not.toMatch(/rp\.provision_title/);
    expect(src).not.toMatch(/rp\.numeric_value/);
  });

  it('routes every tier failure through runTier, so no catch is silent', () => {
    // Each tier's catch returns an explicit { ok: false } AND records a
    // user-facing reason, rather than logging and falling through.
    expect(src).toMatch(/degraded\.push\(/);
    expect(src).toMatch(/return \{ ok: false \}/);
  });

  it('carries no silent-failure suppressions any more', () => {
    // Every catch in this route now records into `degraded` instead of being
    // annotated away. A reinstated qa-ignore here should fail review loudly.
    expect(src).not.toMatch(/qa-ignore:\s*silent-failure/);
  });

  it('reports an unavailable state distinctly from a genuine absence', () => {
    expect(src).toMatch(/unavailable: true/);
    expect(src).toMatch(/status: 503/);
  });
});
