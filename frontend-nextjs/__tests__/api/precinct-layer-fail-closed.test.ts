/**
 * A precinct-layer rule reaches only the houses in its precinct. An address with no precinct
 * gets NOTHING from the precinct layer -- before 2026-10-15 it got every precinct rule whose
 * precinct was unknown (v2_precinct_id NULL): 2,827 rules (C-B 1,953, Ku-ring-gai 858), 24 of
 * the 49 wrong answers in the 300-rule address audit. Mirrors DQ-146 / _REACHES_NOBODY.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const calls: { sql: string; params: unknown[] }[] = [];
const client = {
  query: jest.fn(async (sql: string, params: unknown[] = []) => {
    calls.push({ sql, params });
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
  const qs = new URLSearchParams({ groupBy: 'toc', ...params });
  return new NextRequest(`http://x/api/provisions/for-property?${qs}`);
}

const precinctLayerQueries = () =>
  calls.filter((c) => /v2_dcp_layer = \$\d+/.test(c.sql) && c.params.includes('precinct'));

describe('precinct layer fails closed', () => {
  beforeEach(() => {
    calls.length = 0;
  });

  it('runs no precinct-layer query for an address without a precinct', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req({ former_council: 'canterbury_bankstown', zone: 'R2' }));
    expect(res.status).toBe(200);
    expect(calls.length).toBeGreaterThan(0); // the other layers were queried
    expect(precinctLayerQueries()).toEqual([]);
  });

  it('queries only the named precinct, never unkeyed rows, when one is given', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({ former_council: 'ashfield', zone: 'R2', precinct_id: 'Part 6' }));
    const q = precinctLayerQueries();
    expect(q).toHaveLength(1);
    expect(q[0].sql).toContain('v2_precinct_id = ANY(');
    expect(q[0].sql).not.toMatch(/v2_precinct_id IS NULL/);
  });
});
