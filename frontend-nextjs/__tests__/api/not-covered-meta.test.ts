/**
 * meta.not_covered is the council's withheld-area-rule list, or null (OC-21).
 * @jest-environment node
 */
import { NextRequest } from 'next/server';

const client = {
  query: jest.fn(async () => ({ rows: [] })),
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

const req = (params: Record<string, string>) =>
  new NextRequest(`http://x/api/provisions/for-property?${new URLSearchParams({ groupBy: 'toc', ...params })}`);

describe('meta.not_covered', () => {
  it('lists the withheld chapters for a council with entries', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: 'Leichhardt', zone: 'R2' }))).json();
    expect(body.meta.not_covered.council).toBe('leichhardt');
    const keys = body.meta.not_covered.chapters.map((c: { chapter_key: string }) => c.chapter_key);
    expect(keys).toEqual(expect.arrayContaining(['amendment-1-george-upward-streets', 'part-g-s1-site-specific']));
    expect(body.meta.not_covered.chapters[0].reason).toBeTruthy();
  });

  it('is null for a council with no entry', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: 'hornsby', zone: 'R2' }))).json();
    expect(body.meta.not_covered).toBeNull();
  });

  it('refuses the request when no council is given', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req({ zone: 'R2' }));
    expect(res.status).toBe(400);
  });
});
