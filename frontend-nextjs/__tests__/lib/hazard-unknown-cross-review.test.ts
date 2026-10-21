/**
 * @jest-environment node
 *
 * Cross-review findings on the hazard-unknown branch (2026-10-21): three more places where a
 * hazard map that did not answer (or was never asked) could still read as clear.
 */
jest.mock('@/lib/database/compliance-client', () => {
  const getComplianceData = jest.fn().mockResolvedValue({ summary: {}, constraints: [] });
  return { ComplianceDataClient: jest.fn().mockImplementation(() => ({ getComplianceData })), __get: getComplianceData };
});

import { uncheckedExclusions } from '@/lib/pattern-book-eligibility/check-exclusions';
import { bushfireFromPayload } from '@/lib/hazard-unchecked';
import { GET } from '@/app/api/compliance/dashboard/route';

describe('(1) pattern-book exclusions: an ANEF map that did not answer is not clear', () => {
  it('lists aircraft_noise as not checked when ANEF timed out, so the result cannot be ELIGIBLE', () => {
    const out = uncheckedExclusions({
      environmental: { floodProne: false, bushfireProne: false, uncheckedHazards: ['anef'] },
    });
    expect(out).toContain('aircraft_noise');
  });
  it('lists nothing when every map answered', () => {
    expect(uncheckedExclusions({ environmental: { floodProne: false, bushfireProne: false, uncheckedHazards: [] } })).toEqual([]);
  });
});

describe('(2) property card: a fresh null bush fire answer is kept', () => {
  it('does not replace constraints.bushfireProne === null with an older environmental boolean', () => {
    expect(bushfireFromPayload({ bushfireProne: null }, { bushfireProne: false })).toBeNull();
  });
  it('falls back to environmental only when constraints lacks the field', () => {
    expect(bushfireFromPayload({}, { bushfireProne: true })).toBe(true);
  });
});

describe('(3) compliance dashboard route: hazards it never queries are unknown', () => {
  it('passes every map-backed hazard as unchecked', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {}); // the stub returns no full ComplianceData
    const { __get } = jest.requireMock('@/lib/database/compliance-client');
    await GET({ nextUrl: new URL('http://localhost/api/compliance/dashboard?zone=R2') } as any);
    const constraints = __get.mock.calls[0].at(-1);
    expect(constraints.uncheckedHazards).toEqual(expect.arrayContaining(
      ['bushfire', 'mine_subsidence', 'contaminated_land', 'drinking_water', 'coastal', 'anef']));
  });
});
