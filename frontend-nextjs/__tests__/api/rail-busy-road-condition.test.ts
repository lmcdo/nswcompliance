/**
 * The rules route serves the condition layer's rail_or_busy_road rows only when told the lot adjoins one.
 * prior-art-checked: mirrors greenweb-condition.test.ts.
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
  const qs = new URLSearchParams({ groupBy: 'toc', former_council: 'ku_ring_gai', zone: 'R2', ...params });
  return new NextRequest(`http://x/api/provisions/for-property?${qs}`);
}

const conditionQueries = () =>
  calls.filter((c) => c.sql.includes('v2_site_condition_required = ANY('));
const conditionsAsked = () =>
  conditionQueries().flatMap((c) => c.values.filter(Array.isArray) as string[][]).flat();

describe('rail_or_busy_road site condition', () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it('asks the condition layer for rail_or_busy_road rows when the page says the lot adjoins the rail line or a busy road', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req({ rail_or_busy_road: 'true' }));
    expect(res.status).toBe(200);
    expect(conditionQueries().length).toBeGreaterThan(0);
    expect(conditionsAsked()).toContain('rail_or_busy_road');
  });

  it('runs no condition-layer query at all when no condition is sent', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({}));
    expect(conditionQueries()).toEqual([]);
  });

  it('does not send rail_or_busy_road for a lot that adjoins neither', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({ rail_or_busy_road: 'false', riparian: 'true' }));
    expect(conditionsAsked()).toEqual(expect.arrayContaining(['riparian']));
    expect(conditionsAsked()).not.toContain('rail_or_busy_road');
  });
});
