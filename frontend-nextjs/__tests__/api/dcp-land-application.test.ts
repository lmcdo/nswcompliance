/**
 * DQ-120: a council DCP that does not cover its whole LGA is served only where
 * the property's Land Application Map (layerintersect layer 8) names its LEP.
 * Instrument names below are the live layer-8 answers measured 2026-10-03
 * (see lib/dcp-land-application.ts header for the addresses).
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import {
  decideLandApplication,
  decodeLandApplication,
  encodeLandApplication,
} from '@/lib/dcp-land-application';

const LEP_2012 = { name: 'Sydney Local Environmental Plan 2012', type: 'Included' };
const GSTC = { name: 'Sydney Local Environmental Plan (Green Square Town Centre) 2013', type: 'Included' };
const HAROLD_PARK = { name: 'Sydney Local Environmental Plan (Harold Park) 2011', type: 'Included' };
const SEPP_EHC = {
  name: 'State Environmental Planning Policy (Precincts—Eastern Harbour City) 2021',
  type: 'Subject Land',
};

describe('decideLandApplication', () => {
  it('serves City of Sydney where layer 8 names Sydney LEP 2012 only', () => {
    const d = decideLandApplication('city_of_sydney', [LEP_2012]);
    expect(d.status).toBe('covered');
    expect(d.withhold).toBe(false);
  });

  it('gates the portal display name and the short slug the same way', () => {
    expect(decideLandApplication('Sydney', [GSTC]).withhold).toBe(true);
    expect(decideLandApplication('sydney', [GSTC]).withhold).toBe(true);
  });

  it.each([
    ['Green Square Town Centre', GSTC],
    ['Harold Park', HAROLD_PARK],
    ['Redfern/Waterloo (SEPP)', SEPP_EHC],
  ])('withholds on %s and names the instrument that applies', (_label, instr) => {
    const d = decideLandApplication('city_of_sydney', [instr]);
    expect(d.status).toBe('excluded');
    expect(d.withhold).toBe(true);
    expect(d.other_instruments.map((i) => i.name)).toEqual([instr.name]);
    expect(d.required_lep).toBe(LEP_2012.name);
  });

  it('withholds as UNKNOWN when there is no layer-8 answer — never a pass', () => {
    for (const none of [null, undefined, []]) {
      const d = decideLandApplication('city_of_sydney', none);
      expect(d.status).toBe('unknown');
      expect(d.withhold).toBe(true);
    }
  });

  it('serves a straddling lot with a warning naming the other plan', () => {
    const d = decideLandApplication('city_of_sydney', [LEP_2012, GSTC]);
    expect(d.status).toBe('partial');
    expect(d.withhold).toBe(false);
    expect(d.other_instruments).toEqual([GSTC]);
  });

  it('does not treat the LEP named with a non-Included type as covered', () => {
    const d = decideLandApplication('city_of_sydney', [{ ...LEP_2012, type: 'Deferred matter' }]);
    expect(d.status).toBe('unknown');
    expect(d.withhold).toBe(true);
  });

  it('does not match a longer LEP name that merely contains the required one', () => {
    const d = decideLandApplication('city_of_sydney', [
      { name: 'Sydney Local Environmental Plan 2012 (Amendment No 99)', type: 'Included' },
    ]);
    expect(d.withhold).toBe(true);
  });

  it('matches across case and whitespace differences', () => {
    const d = decideLandApplication('city_of_sydney', [
      { name: '  sydney local  environmental plan 2012 ', type: 'INCLUDED' },
    ]);
    expect(d.status).toBe('covered');
  });

  it('leaves councils without a declared binding exactly as before', () => {
    const d = decideLandApplication('marrickville', null);
    expect(d.status).toBe('not_gated');
    expect(d.withhold).toBe(false);
    expect(decideLandApplication(undefined, null).withhold).toBe(false);
  });
});

describe('encode/decodeLandApplication', () => {
  it('round-trips', () => {
    const raw = encodeLandApplication([LEP_2012, SEPP_EHC]);
    expect(decodeLandApplication(raw)).toEqual([LEP_2012, SEPP_EHC]);
  });

  it('sends nothing for an empty or missing list', () => {
    expect(encodeLandApplication([])).toBeNull();
    expect(encodeLandApplication(null)).toBeNull();
    expect(encodeLandApplication(undefined)).toBeNull();
  });

  it.each([['not json'], ['{"name":"x"}'], ['[{"type":"Included"}]'], ['[{"name":""}]'], ['[null]'], ['[]']])(
    'reads malformed input %s as no answer',
    (raw) => {
      expect(decodeLandApplication(raw)).toBeNull();
    }
  );
});

// ── Route: the gate sits BEFORE any query ────────────────────────────────────
const mockConnect = jest.fn();
jest.mock('@/lib/db', () => ({ getPool: () => ({ connect: mockConnect }) }));
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

describe('GET /api/provisions/for-property land gate', () => {
  beforeEach(() => {
    mockConnect.mockReset();
    // Reaching the database is the observable "not withheld" outcome; the query
    // path itself is out of scope here, so the connection fails on purpose.
    mockConnect.mockRejectedValue(new Error('db reached'));
  });

  it('withholds Green Square without touching the database', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const res = await GET(req({
      former_council: 'city_of_sydney',
      land_application: encodeLandApplication([GSTC])!,
    }));
    const body = await res.json();
    expect(mockConnect).not.toHaveBeenCalled();
    expect(body.success).toBe(true);
    expect(body.data.summary.total_provisions).toBe(0);
    expect(body.data.by_layer.every((l: { count: number }) => l.count === 0)).toBe(true);
    expect(body.data.by_toc).toEqual({});
    expect(body.meta.land_application.status).toBe('excluded');
    expect(body.meta.land_application.other_instruments[0].name).toBe(GSTC.name);
  });

  it('withholds City of Sydney when the caller sends no layer-8 answer', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    const body = await (await GET(req({ former_council: 'city_of_sydney' }))).json();
    expect(mockConnect).not.toHaveBeenCalled();
    expect(body.meta.land_application.status).toBe('unknown');
  });

  it('goes on to query for a covered City of Sydney property', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({
      former_council: 'city_of_sydney',
      land_application: encodeLandApplication([LEP_2012])!,
    }));
    expect(mockConnect).toHaveBeenCalledTimes(1);
  });

  it('goes on to query for an ungated council with no layer-8 answer', async () => {
    const { GET } = await import('@/app/api/provisions/for-property/route');
    await GET(req({ former_council: 'marrickville' }));
    expect(mockConnect).toHaveBeenCalledTimes(1);
  });
});
