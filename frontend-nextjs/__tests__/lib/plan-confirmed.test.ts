/** @jest-environment node */
/**
 * DQ-153: the date we last looked at a council's plan, and when the page says so.
 */
import { loadPlanConfirmed, planCheckIsOld, PLAN_CONFIRMED_SQL } from '@/lib/plan-confirmed';

const NOW = new Date('2026-11-10T00:00:00Z');

describe('planCheckIsOld', () => {
  it('is old after 30 days (waverley, last checked 2026-06-29)', () => {
    expect(planCheckIsOld('2026-06-29T02:03:55Z', NOW)).toBe(true);
  });
  it('is not old when checked today (blacktown)', () => {
    expect(planCheckIsOld('2026-11-10T02:00:26Z', NOW)).toBe(false);
  });
  it('is exactly at the line: 30 days is not old, 31 is', () => {
    expect(planCheckIsOld('2026-10-11T00:00:00Z', NOW)).toBe(false);
    expect(planCheckIsOld('2026-10-10T00:00:00Z', NOW)).toBe(true);
  });
  it('says nothing when there is no date (no claim without a date)', () => {
    expect(planCheckIsOld(null, NOW)).toBe(false);
    expect(planCheckIsOld(undefined, NOW)).toBe(false);
    expect(planCheckIsOld('not a date', NOW)).toBe(false);
  });
});

describe('loadPlanConfirmed', () => {
  const q = (rows: any[]) => jest.fn(async () => ({ rows }));

  it('returns the oldest check as an ISO date', async () => {
    const query = q([{ oldest: new Date('2026-09-24T05:01:43Z'), never: false }]);
    await expect(loadPlanConfirmed(query, 'wollongong')).resolves.toBe('2026-09-24T05:01:43.000Z');
    expect(query).toHaveBeenCalledWith(PLAN_CONFIRMED_SQL, ['wollongong']);
  });
  it('returns null with no council, no chapters, or a chapter never checked', async () => {
    const query = q([]);
    await expect(loadPlanConfirmed(query, null)).resolves.toBeNull();
    expect(query).not.toHaveBeenCalled();
    await expect(loadPlanConfirmed(q([]), 'x')).resolves.toBeNull();
    await expect(loadPlanConfirmed(q([{ oldest: null, never: null }]), 'x')).resolves.toBeNull();
    await expect(loadPlanConfirmed(q([{ oldest: new Date('2026-09-24'), never: true }]), 'x')).resolves.toBeNull();
  });
  it('only looks at chapters that serve rules (so a dead unused chapter cannot make the date old)', () => {
    expect(PLAN_CONFIRMED_SQL).toMatch(/is_active = TRUE/);
    expect(PLAN_CONFIRMED_SQL).toMatch(/p\.is_current = TRUE AND p\.v2_is_actionable = TRUE/);
  });
});
