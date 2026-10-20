/**
 * The rules route serves the condition layer's 'greenweb' rows only when told the lot is on Greenweb.
 * prior-art-checked: mirrors precinct-layer-fail-closed.test.ts for the new condition value.
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

describe('greenweb site condition', () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it('asks the condition layer for greenweb rows when the page says the lot is on Greenweb', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req({ greenweb: 'true' }));
    expect(res.status).toBe(200);
    expect(conditionQueries().length).toBeGreaterThan(0);
    expect(conditionsAsked()).toContain('greenweb');
  });

  it('runs no condition-layer query at all when no condition is sent', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({}));
    expect(conditionQueries()).toEqual([]);
  });

  it('does not send greenweb for a lot that is not on it', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({ greenweb: 'false', riparian: 'true' }));
    expect(conditionsAsked()).toEqual(expect.arrayContaining(['riparian']));
    expect(conditionsAsked()).not.toContain('greenweb');
  });
});
