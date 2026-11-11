/** @jest-environment node */
/**
 * DQ-153: whether we have been able to look at a council's plan, and when the page says so.
 * The page uses the SAME rule as the red number: over 14 days, never checked, or blocked.
 */
import { loadPlanCheck, planNotice, PLAN_CONFIRMED_SQL, PLAN_STALE_AFTER_DAYS, type PlanCheck } from '@/lib/plan-confirmed';

const NOW = new Date('2026-11-10T00:00:00Z');
const check = (o: Partial<PlanCheck>): PlanCheck => ({ checked_on: '2026-11-10T02:00:26Z', never_checked: false, blocked: false, ...o });

describe('planNotice', () => {
  it('uses 14 days, the same as the red number', () => {
    expect(PLAN_STALE_AFTER_DAYS).toBe(14);
  });
  it('is old after 14 days (waverley, last checked 2026-06-29)', () => {
    expect(planNotice(check({ checked_on: '2026-06-29T02:03:55Z' }), NOW)).toBe('old');
  });
  it('shows nothing when checked today (blacktown)', () => {
    expect(planNotice(check({}), NOW)).toBeNull();
  });
  it('is exactly at the line: 14 days is fine, 15 is old', () => {
    expect(planNotice(check({ checked_on: '2026-10-27T00:00:00Z' }), NOW)).toBeNull();
    expect(planNotice(check({ checked_on: '2026-10-26T00:00:00Z' }), NOW)).toBe('old');
  });
  it('a chapter never checked is shown, even when the others are fresh', () => {
    expect(planNotice(check({ never_checked: true }), NOW)).toBe('never');
    expect(planNotice(check({ never_checked: true, checked_on: null }), NOW)).toBe('never');
  });
  it('a blocked chapter is shown even though its date looks fresh', () => {
    expect(planNotice(check({ blocked: true }), NOW)).toBe('blocked');
  });
  it('says nothing when there is nothing to say (no serving chapters, old response, bad date)', () => {
    expect(planNotice(null, NOW)).toBeNull();
    expect(planNotice(undefined, NOW)).toBeNull();
    expect(planNotice(check({ checked_on: null }), NOW)).toBeNull();
    expect(planNotice(check({ checked_on: 'not a date' }), NOW)).toBeNull();
  });
});

describe('loadPlanCheck', () => {
  const q = (rows: any[]) => jest.fn(async () => ({ rows }));

  it('returns the oldest check, and the never/blocked flags', async () => {
    const query = q([{ chapters: '6', oldest: new Date('2026-09-24T05:01:43Z'), never: false, blocked: true }]);
    await expect(loadPlanCheck(query, 'wollongong')).resolves.toEqual({
      checked_on: '2026-09-24T05:01:43.000Z', never_checked: false, blocked: true,
    });
    expect(query).toHaveBeenCalledWith(PLAN_CONFIRMED_SQL, ['wollongong']);
  });
  it('a never-checked chapter comes through as never_checked, not as nothing', async () => {
    const r = await loadPlanCheck(q([{ chapters: '2', oldest: null, never: true, blocked: false }]), 'x');
    expect(r).toEqual({ checked_on: null, never_checked: true, blocked: false });
  });
  it('returns null with no council or no serving chapters', async () => {
    const query = q([]);
    await expect(loadPlanCheck(query, null)).resolves.toBeNull();
    expect(query).not.toHaveBeenCalled();
    await expect(loadPlanCheck(q([]), 'x')).resolves.toBeNull();
    await expect(loadPlanCheck(q([{ chapters: '0', oldest: null, never: null, blocked: null }]), 'x')).resolves.toBeNull();
  });
  it('only looks at chapters that serve rules, and at the LATEST monitor result', () => {
    expect(PLAN_CONFIRMED_SQL).toMatch(/is_active = TRUE/);
    expect(PLAN_CONFIRMED_SQL).toMatch(/p\.is_current = TRUE AND p\.v2_is_actionable = TRUE/);
    expect(PLAN_CONFIRMED_SQL).toMatch(/ORDER BY x\.checked_at DESC, x\.id DESC LIMIT 1/);
    expect(PLAN_CONFIRMED_SQL).toMatch(/= 'waf_blocked'/);
  });
});
