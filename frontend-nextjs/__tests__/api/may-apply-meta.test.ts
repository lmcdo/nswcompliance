/**
 * meta.may_apply: the areas whose rules may apply to the property's suburb, beside (never inside) its provisions.
 * Suburbs and areas come from shared/may-apply-areas.json, not from this file.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import mayApplyData from '@/shared/may-apply-areas.json';
import notCoveredData from '@/shared/not-covered-councils.json';
import { areasInChapter } from '@/lib/may-apply-query';
import { reasonText } from '@/lib/may-apply-reasons';

// The per-area cap in lib/may-apply-query.ts.
const MAX_ROWS = 400;

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
// a DCP rule (the select is per chapter) whose words are proven in the council's plan (lib/council-quote.ts)
const ROW = { id: 1, document_id: 1, provision_text: 'A withheld rule', v2_dcp_layer: 'generic', pdf_page: 5, source_council: 'x',
  source_chapter_key: 'c1', quote_status: 'exact', council_quote: 'A withheld rule', quote_page: 5 };
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
    expect(calls[0][0]).toContain('rp.v2_is_actionable = FALSE AND rp.v2_precinct_id IS NULL');
    // a keyed row is offered only if it is live (switched-off keyed rows were left out on purpose)
    expect(calls[0][0]).toContain('rp.v2_precinct_id IS NOT NULL AND rp.v2_is_actionable = TRUE');
    expect(calls[0][0]).toContain("OR (rp.v2_dcp_layer = 'precinct' AND rp.v2_precinct_id IS NULL)");
    // ... or keyed to an outline this property is not inside ($6 = its precinct ids)
    expect(calls[0][0]).toContain("AND NOT (rp.v2_precinct_id = ANY($6::text[]))");
    expect(calls[0][1][0]).toBe(council);
    expect(calls[0][1][5]).toEqual([]); // no precinct sent = empty list, never undefined
    // never merged into the property's own provisions
    expect(body.data.summary.total_provisions).toBe(0);
  });

  describe('an area whose rules are keyed to an outline (Marrickville 2.26)', () => {
    const mk = 'marrickville';
    const area = (DATA[mk]?.ENMORE ?? []).find((a) => a.area_id === 'marrickville-2-26-sound-category-areas')!;
    const SEP = 'Marrickville 2.26 entertainment precinct';
    // The database's answer for a row keyed to SEP: withheld from this property unless SEP is one of its precincts.
    const KEYED = { ...ROW, v2_dcp_layer: 'precinct', v2_precinct_id: SEP };
    beforeEach(() => {
      client.query.mockImplementation(async (sql: string, params: unknown[]) => ({
        rows: isMayApplySql(sql) && !(params[5] as string[]).includes(SEP) ? [KEYED] : [],
      }));
    });
    const mayApplyFor = async (extra: Record<string, string>) => {
      const { GET } = await import('@/app/api/provisions/for-property/route');
      const body = await (await GET(req({ former_council: mk, suburb: 'Enmore', ...extra }))).json();
      return body.meta.may_apply.filter((a: { area_id: string }) => a.area_id === area.area_id);
    };

    it('is listed for Enmore', () => expect(area).toBeTruthy());

    it('shows the rows to a house outside the outline', async () => {
      const got = await mayApplyFor({ precinct_id: '8_' });
      expect(got).toHaveLength(1);
      expect(got[0].provisions).toHaveLength(1);
    });

    it('does not repeat them for a lot inside the outline (served in the main list instead)', async () => {
      expect(await mayApplyFor({ precinct_id: `8_,${SEP}` })).toEqual([]);
      const call = client.query.mock.calls.find(([sql]: [string]) => isMayApplySql(sql))!;
      expect(call[1][5]).toEqual(['8_', SEP]);
    });
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

  it('drops a chapter from the not-covered notice only when its one area is shown in full', async () => {
    // Suburbs, chapters and counts come from the data files, not from this test.
    const cb = 'canterbury_bankstown';
    const NC = notCoveredData as Record<string, Array<{ chapter_key: string; count_hint?: number }>>;
    const areaCount = (key: string) => areasInChapter(cb, key);
    const single = NC[cb].find((c) => typeof c.count_hint === 'number' && areaCount(c.chapter_key) === 1)!;
    const split = NC[cb].find((c) => areaCount(c.chapter_key) > 1)!;
    const subOf = (key: string) => Object.keys(DATA[cb]).find((s) => DATA[cb][s].some((a) => a.chapter_key === key))!;
    const rowsN = (n: number) => async (sql: string) => ({
      rows: isMayApplySql(sql) ? Array.from({ length: n }, (_, k) => ({ ...ROW, id: k + 1 })) : [],
    });
    const keysFor = async (suburb: string) => {
      const { GET } = await import('@/app/api/provisions/for-property/route');
      const body = await (await GET(req({ former_council: cb, suburb }))).json();
      return (body.meta.not_covered?.chapters ?? []).map((c: { chapter_key: string }) => c.chapter_key);
    };
    // Whole chapter loaded: dropped.
    client.query.mockImplementation(rowsN(single.count_hint!));
    expect(await keysFor(subOf(single.chapter_key))).not.toContain(single.chapter_key);
    // Fewer rows than the chapter holds: kept.
    client.query.mockImplementation(rowsN(single.count_hint! - 1));
    expect(await keysFor(subOf(single.chapter_key))).toContain(single.chapter_key);
    // A chapter split over several areas: kept, however many rows one area shows.
    client.query.mockImplementation(rowsN(MAX_ROWS));
    expect(await keysFor(subOf(split.chapter_key))).toContain(split.chapter_key);
    // Lookup failed: kept.
    client.query.mockImplementation(async (sql: string) => {
      if (isMayApplySql(sql)) throw new Error('boom');
      return { rows: [] };
    });
    expect(await keysFor(subOf(single.chapter_key))).toContain(single.chapter_key);
  });

  it('every area in the data has a usable row selector and a known reason', () => {
    for (const subs of Object.values(DATA)) {
      for (const list of Object.values(subs)) {
        for (const a of list as Array<{ area_id: string; reason_code: string; row_selector?: { pdf_page_from?: number; pdf_page_to?: number; ids?: number[] } }>) {
          const sel = a.row_selector ?? {};
          const range = Number.isInteger(sel.pdf_page_from) && Number.isInteger(sel.pdf_page_to) && sel.pdf_page_from! <= sel.pdf_page_to!;
          expect([a.area_id, range || (sel.ids ?? []).length > 0]).toEqual([a.area_id, true]);
          expect([a.area_id, reasonText(a.reason_code)]).not.toEqual([a.area_id, null]);
        }
      }
    }
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
