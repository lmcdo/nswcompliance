/**
 * GET /api/housing-sepp/area-check — the proxy passes the answer through and turns every failure into an error, never into an answer.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { GET } from '@/app/api/housing-sepp/area-check/route';

const req = (qs: string) => new NextRequest(`http://localhost/api/housing-sepp/area-check${qs}`);
const realFetch = global.fetch;
afterEach(() => { global.fetch = realFetch; });

describe('area-check proxy', () => {
  it('rejects missing or non-numeric coordinates with 400 and calls nothing', async () => {
    const f = jest.fn(); global.fetch = f as never;
    for (const qs of ['', '?lat=1', '?lat=a&lng=b', '?lat=&lng=151']) expect((await GET(req(qs))).status).toBe(400);
    expect(f).not.toHaveBeenCalled();
  });

  it('asks the Python service for the same point and returns its answer untouched', async () => {
    const body = { pathway: 'lmr', headline: 'x', lmr: { answer: 'yes' } };
    const f = jest.fn().mockResolvedValue({ ok: true, json: async () => body }); global.fetch = f as never;
    const res = await GET(req('?lat=-33.889&lng=151.126'));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual(body);
    expect(String(f.mock.calls[0][0])).toMatch(/\/pipeline\/housing-sepp\/area-check\?lat=-33\.889&lng=151\.126$/);
  });

  it('never lets Next cache the Python answer (a cached copy kept serving old law text after the text changed)', async () => {
    const f = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) }); global.fetch = f as never;
    await GET(req('?lat=-33.889&lng=151.126'));
    expect(f.mock.calls[0][1]).toMatchObject({ cache: 'no-store' });
  });

  it('a service error or an unreachable service is a 502 error, not a yes or a no', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false, status: 500, text: async () => 'boom' }) as never;
    const a = await GET(req('?lat=-33.889&lng=151.126'));
    expect(a.status).toBe(502);
    expect(await a.json()).toEqual({ error: 'boom' });
    global.fetch = jest.fn().mockRejectedValue(new Error('connect ECONNREFUSED')) as never;
    const b = await GET(req('?lat=-33.889&lng=151.126'));
    expect(b.status).toBe(502);
    expect((await b.json()).error).toMatch(/Area check failed/);
  });
});
