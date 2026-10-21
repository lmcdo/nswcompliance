/**
 * The rules route serves the condition layer's state_road / classified_road rows only when told the lot fronts one.
 * prior-art-checked: mirrors rail-busy-road-condition.test.ts.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const calls: { sql: string; values: unknown[] }[] = [];
const client = {
  query: jest.fn(async (sql: string, params: unknown[] = []) => {
    calls.push({ sql, values: params });
    return { rows: [] };
  }),
  release: jest.fn(),
};
jest.mock('@/lib/db', () => ({ getPool: () => ({ connect: async () => client }) }));
jest.mock('@/lib/rate-limit', () => ({
  dataRateLimiter: {},
  getClientIdentifier: () => 'test',
  checkRateLimit: async () => ({ success: true }),
  createRateLimitHeaders: () => ({}),
}));
jest.mock('@/lib/posthog-server', () => ({ captureServerException: jest.fn() }));

function req(params: Record<string, string>) {
  const qs = new URLSearchParams({ groupBy: 'toc', former_council: 'canterbury_bankstown', zone: 'E4', ...params });
  return new NextRequest(`http://x/api/provisions/for-property?${qs}`);
}

const conditionsAsked = () =>
  calls
    .filter((c) => c.sql.includes('v2_site_condition_required = ANY('))
    .flatMap((c) => c.values.filter(Array.isArray) as string[][])
    .flat();

describe('state_road / classified_road site conditions', () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it('a lot on a State road asks for both conditions', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req({ state_road: 'true', classified_road: 'true' }));
    expect(res.status).toBe(200);
    expect(conditionsAsked()).toEqual(expect.arrayContaining(['state_road', 'classified_road']));
  });

  it('a lot on a classified Regional road asks for classified_road only', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({ classified_road: 'true' }));
    expect(conditionsAsked()).toContain('classified_road');
    expect(conditionsAsked()).not.toContain('state_road');
  });

  it('a lot on neither asks for neither', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({ state_road: 'false', classified_road: 'false', flood: 'true' }));
    expect(conditionsAsked()).toContain('flood');
    expect(conditionsAsked()).not.toContain('state_road');
    expect(conditionsAsked()).not.toContain('classified_road');
  });
});
