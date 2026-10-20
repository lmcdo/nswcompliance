/**
 * meta.may_apply: the areas whose rules may apply to the property's suburb, beside (never inside) its provisions.
 * Suburbs and areas come from shared/may-apply-areas.json, not from this file.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import mayApplyData from '@/shared/may-apply-areas.json';

const client = { query: jest.fn(), release: jest.fn() };
jest.mock('@/lib/db', () => ({ getPool: () => ({ connect: async () => client }) }));
jest.mock('@/lib/rate-limit', () => ({
  dataRateLimiter: {},
  getClientIdentifier: () => 'test',
  checkRateLimit: async () => ({ success: true }),
  createRateLimitHeaders: () => ({}),
}));
jest.mock('@/lib/posthog-server', () => ({ captureServerException: jest.fn() }));

const DATA = mayApplyData as Record<string, Record<string, Array<{ area_id: string; chapter_key: string }>>>;
const ROW = { id: 1, document_id: 1, provision_text: 'A withheld rule', v2_dcp_layer: 'generic', pdf_page: 5, source_council: 'x' };
const isMayApplySql = (sql: string) => sql.includes('rp.source_chapter_key = $2');

const req = (params: Record<string, string>) =>
  new NextRequest(`http://x/api/provisions/for-property?${new URLSearchParams({ groupBy: 'toc', ...params })}`);

// Northern Beaches is gated on the Land Application Map, so every request
// carries Warringah LEP land.
const council = 'northern_beaches';
const suburb = Object.keys(DATA[council])[0];
const areas = DATA[council][suburb];
const WARRINGAH = JSON.stringify([{ name: 'Warringah Local Environmental Plan 2011', type: 'Included' }]);

beforeEach(() => {
  client.query.mockReset();
  client.query.mockImplementation(async (sql: string) => ({ rows: isMayApplySql(sql) ? [ROW] : [] }));
});

describe('meta.may_apply', () => {
  it('returns the suburb areas with their rows, one parameterised select each', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: council, land_application: WARRINGAH, suburb: suburb.toLowerCase() + ' NSW 2000' }))).json();
    expect(body.meta.may_apply.map((a: { area_id: string }) => a.area_id)).toEqual(areas.map((a) => a.area_id));
    for (const a of body.meta.may_apply) {
      expect(a.provisions).toHaveLength(1);
      expect(a.provisions[0].provision_text).toBe('A withheld rule');
      expect(a.reason_text).toBeTruthy();
    }
    const calls = client.query.mock.calls.filter(([sql]: [string]) => isMayApplySql(sql));
    expect(calls).toHaveLength(areas.length);
    expect(calls[0][0]).toContain('LIMIT 401');
    // withheld rows only: a served row is already in the main list (no double listing)
    expect(calls[0][0]).toContain("(rp.v2_is_actionable = FALSE OR (rp.v2_dcp_layer = 'precinct' AND rp.v2_precinct_id IS NULL))");
    expect(calls[0][1][0]).toBe(council);
    // never merged into the property's own provisions
    expect(body.data.summary.total_provisions).toBe(0);
  });

  it('returns none for another suburb', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: council, land_application: WARRINGAH, suburb: 'NOWHERE IN PARTICULAR' }))).json();
    expect(body.meta.may_apply).toEqual([]);
  });

  it('returns none when no suburb is sent', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: council, land_application: WARRINGAH }))).json();
    expect(body.meta.may_apply).toEqual([]);
  });

  it('returns the area with provisions null when its lookup fails', async () => {
    client.query.mockImplementation(async (sql: string) => {
      if (isMayApplySql(sql)) throw new Error('boom');
      return { rows: [] };
    });
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: council, land_application: WARRINGAH, suburb }))).json();
    expect(body.success).toBe(true);
    expect(body.meta.may_apply).toHaveLength(areas.length);
    for (const a of body.meta.may_apply) expect(a.provisions).toBeNull();
  });

  it('leaves out an area with no withheld rows left', async () => {
    client.query.mockImplementation(async () => ({ rows: [] }));
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: council, land_application: WARRINGAH, suburb }))).json();
    expect(body.meta.may_apply).toEqual([]);
  });

  it('fails an area visibly when it has more rows than the cap', async () => {
    client.query.mockImplementation(async (sql: string) => ({
      rows: isMayApplySql(sql) ? Array.from({ length: 401 }, (_, i) => ({ ...ROW, id: i + 1 })) : [],
    }));
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: council, land_application: WARRINGAH, suburb }))).json();
    expect(body.meta.may_apply).toHaveLength(areas.length);
    for (const a of body.meta.may_apply) expect(a.provisions).toBeNull();
  });

  it('drops a chapter from the not-covered notice only when the block shows its rows', async () => {
    // A council that has both lists; the suburb and chapter come from the data files.
    const cb = 'canterbury_bankstown';
    const cbSuburb = Object.keys(DATA[cb]).find((s) => DATA[cb][s].length > 0)!;
    const shownKeys = new Set(DATA[cb][cbSuburb].map((a) => a.chapter_key));
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const shown = await (await GET(req({ former_council: cb, suburb: cbSuburb }))).json();
    const left = (shown.meta.not_covered?.chapters ?? []).map((c: { chapter_key: string }) => c.chapter_key);
    for (const k of shownKeys) expect(left).not.toContain(k);
    const all = await (await GET(req({ former_council: cb }))).json();
    const allKeys = all.meta.not_covered.chapters.map((c: { chapter_key: string }) => c.chapter_key);
    expect([...shownKeys].some((k) => allKeys.includes(k))).toBe(true);
    expect(left.length).toBe(allKeys.filter((k: string) => !shownKeys.has(k)).length);
    // Lookup failed: the chapter stays in the notice.
    client.query.mockImplementation(async (sql: string) => {
      if (isMayApplySql(sql)) throw new Error('boom');
      return { rows: [] };
    });
    const failed = await (await GET(req({ former_council: cb, suburb: cbSuburb }))).json();
    expect(failed.meta.not_covered.chapters.map((c: { chapter_key: string }) => c.chapter_key)).toEqual(allKeys);
  });

  it('offers Northern Beaches areas only to land under Warringah LEP 2011', async () => {
    const nbSuburb = Object.keys(DATA.northern_beaches)[0];
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const warringah = JSON.stringify([{ name: 'Warringah Local Environmental Plan 2011', type: 'Included' }]);
    const manly = JSON.stringify([{ name: 'Manly Local Environmental Plan 2013', type: 'Included' }]);
    const yes = await (await GET(req({ former_council: 'northern_beaches', suburb: nbSuburb, land_application: warringah }))).json();
    expect(yes.meta.may_apply.length).toBeGreaterThan(0);
    // Manly land is withheld before any query: no may_apply at all.
    const no = await (await GET(req({ former_council: 'northern_beaches', suburb: nbSuburb, land_application: manly }))).json();
    expect(no.meta.may_apply ?? []).toEqual([]);
  });
});
