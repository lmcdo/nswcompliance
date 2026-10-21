/**
 * /api/property: every fact comes from a source that answered, or says "Not checked". Nothing is filled in.
 *
 * (a) Every outside call and the database fail -> the reply holds no definite value; every check that did
 *     not answer is named in `uncheckedHazards` / `notChecked`. A failure never reads as "No" or "not found".
 * (b) The same recorded replies twice -> the same reply (minus the timestamp).
 *
 * Fixture: real replies recorded 2026-10-22 for 8 Hollands Ave, Marrickville (propId 1953940).
 * prior-art-checked: __tests__/lib/hazard-lookup-unknown.test.ts covers the hazard maps only and stubs
 * planning layers and TOD as [] (failure = empty); this file drives the whole route.
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import recorded from '../fixtures/property-lookup/8-hollands-ave-marrickville.json';
import { ALL_HAZARDS } from '@/lib/hazard-unchecked';
import { LOOKUP_CHECKS, LOOKUP_BUDGET_MS } from '@/lib/lookup-not-checked';

const dbDown = () => Promise.reject(new Error('database unreachable'));
const mockDb = { query: jest.fn(), connect: jest.fn() };
jest.mock('@/lib/db', () => ({ query: (...a: unknown[]) => mockDb.query(...a), getPool: () => mockDb }));
const mockClauses = { override: null as string[] | null };
jest.mock('@/lib/site-specific-part6-mapping', () => {
  const actual = jest.requireActual('@/lib/site-specific-part6-mapping');
  return { ...actual, getSiteSpecificClauses: (...a: any[]) => mockClauses.override ?? actual.getSiteSpecificClauses(...a) };
});

const ADDRESS = recorded.address;
const replies = recorded.replies as Record<string, { status: number; body: string }>;
const key = (url: string, init: any = {}) =>
  `${init?.method ?? 'GET'} ${url}${init?.body ? ' BODY ' + String(init.body) : ''}`;
const isSearch = (u: string) => u.includes('/ePlanningApi/address?');
const isValuation = (u: string) => u.includes('/Valuation/MapServer/5/query');

function replay(url: string, init: any) {
  const r = replies[key(url, init)];
  if (!r) return Promise.reject(new Error(`no recorded reply for ${key(url, init).slice(0, 160)}`));
  return Promise.resolve(new Response(r.body, { status: r.status }));
}

/** Search and valuation answer from the recording; `rest` decides every other call. */
function fetchWith(rest: (url: string, init: any) => Promise<Response>) {
  return jest.fn((input: any, init: any = {}) => {
    const url = String(input);
    return isSearch(url) || isValuation(url) ? replay(url, init) : rest(url, init);
  }) as any;
}
const fails = () => Promise.reject(new Error('ECONNRESET'));

async function lookup() {
  const { GET } = await import('@/app/api/property/route');
  const res = await GET(new NextRequest(`http://x/api/property?address=${encodeURIComponent(ADDRESS)}`));
  return { status: res.status, body: await res.json() };
}

/** Facts read straight from the two sources that answered (address search, valuation). */
const ANSWERED = /^(propId|address|landValue|valuationDate|propertyArea|zoneDescription|urbanity|geometry\.[xy]|coordinates\.(lat|lon))$/;
/** Words that say a fact is not known. */
const NOT_KNOWN = /not checked|could not|couldn't|can't tell|did not answer|unavailable|unknown|not known|not found|failed/i;
/** The lists that NAME the checks that did not answer. */
const NAMING_LISTS = /^(constraints|environmental)\.(uncheckedHazards|notChecked)\.\d+$/;

/** Every leaf that states something definite although its source did not answer. */
function fillIns(value: unknown, path = ''): string[] {
  if (value === null || value === undefined) return [];
  if (Array.isArray(value)) return value.flatMap((v, i) => fillIns(v, `${path}.${i}`));
  if (typeof value === 'object') {
    return Object.entries(value as object).flatMap(([k, v]) => fillIns(v, path ? `${path}.${k}` : k));
  }
  if (ANSWERED.test(path) || NAMING_LISTS.test(path)) return [];
  if (typeof value === 'string' && (value === '' || NOT_KNOWN.test(value))) return [];
  return [`${path} = ${JSON.stringify(value)}`];
}

describe('/api/property when its sources fail', () => {
  const realFetch = global.fetch;
  beforeEach(() => {
    mockDb.query.mockImplementation(dbDown);
    mockDb.connect.mockImplementation(dbDown);
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
  });
  afterEach(() => {
    global.fetch = realFetch;
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('address search down: the reply says the service is unavailable, never "no such property"', async () => {
    global.fetch = jest.fn(fails) as any;
    const { status, body } = await lookup();
    expect(status).not.toBe(200);
    expect(body.notFound).toBeUndefined();
    expect(body.data).toBeUndefined();
  });

  it('valuation down: the reply says the service is unavailable, never "no such property"', async () => {
    global.fetch = jest.fn((input: any, init: any) => (isSearch(String(input)) ? replay(String(input), init) : fails())) as any;
    const { status, body } = await lookup();
    expect(status).not.toBe(200);
    expect(body.notFound).toBeUndefined();
    expect(body.data).toBeUndefined();
  });

  it('valuation with no location: the lookup stops, it never checks the maps at 0, 0', async () => {
    const noGeometry = (url: string, init: any) => {
      if (!isValuation(url)) return replay(url, init);
      const v = JSON.parse(replies[key(url, init)].body);
      delete v.features[0].geometry;
      return Promise.resolve(new Response(JSON.stringify(v), { status: 200 }));
    };
    const asked: string[] = [];
    global.fetch = jest.fn((input: any, init: any = {}) => {
      const url = String(input);
      asked.push(url);
      return isSearch(url) || isValuation(url) ? noGeometry(url, init) : fails();
    }) as any;
    const { status, body } = await lookup();
    expect(status).not.toBe(200);
    expect(body.data).toBeUndefined();
    expect(asked.filter((u) => /geometry=0,0|"x":0,"y":0/.test(u))).toEqual([]);
  });

  it('(a) every other call and the database fail: no definite value, every check named "not checked"', async () => {
    global.fetch = fetchWith(fails);
    const { status, body } = await lookup();
    expect(status).toBe(200);
    expect(fillIns(body.data)).toEqual([]);
    expect([...body.data.constraints.uncheckedHazards].sort()).toEqual([...ALL_HAZARDS].sort());
    expect([...body.data.constraints.notChecked].sort()).toEqual([...LOOKUP_CHECKS].sort());
  });

  it('(a) every other call stalls (headers sent, body never comes): the reply still comes inside the budget', async () => {
    jest.useFakeTimers();
    const stallBody = (_url: string, init: any) => {
      const signal: AbortSignal | undefined = init?.signal;
      const never = () => new Promise<never>((_, reject) => {
        signal?.addEventListener('abort', () => reject(Object.assign(new Error('aborted'), { name: 'AbortError' })));
      });
      return Promise.resolve({ ok: true, status: 200, json: never, text: never } as unknown as Response);
    };
    global.fetch = fetchWith(stallBody);
    let done: { status: number; body: any } | null = null;
    const pending = lookup().then((r) => (done = r));
    await jest.advanceTimersByTimeAsync(LOOKUP_BUDGET_MS + 100);
    expect(done).not.toBeNull();
    const { status, body } = await pending;
    expect(status).toBe(200);
    expect(fillIns(body.data)).toEqual([]);
    expect([...body.data.constraints.uncheckedHazards].sort()).toEqual([...ALL_HAZARDS].sort());
    expect([...body.data.constraints.notChecked].sort()).toEqual([...LOOKUP_CHECKS].sort());
  });
});

describe('/api/property when the database never answers', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it('(a) the overlay and lot queries hang: the reply still comes inside the budget, those checks "not checked"', async () => {
    jest.useFakeTimers();
    mockDb.query.mockImplementation(() => new Promise(() => {}));
    mockDb.connect.mockImplementation(() => new Promise(() => {}));
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
    global.fetch = jest.fn((input: any, init: any) => replay(String(input), init)) as any;
    let done: { status: number; body: any } | null = null;
    const pending = lookup().then((r) => (done = r));
    await jest.advanceTimersByTimeAsync(LOOKUP_BUDGET_MS + 2100);
    expect(done).not.toBeNull();
    const { status, body } = await pending;
    expect(status).toBe(200);
    expect(body.data.constraints.notChecked).toEqual(expect.arrayContaining(['spatial_overlays', 'classified_road']));
  });

  it('work that ignores the time limit is still cut off: the lookup stops with "ran out of time", never hangs', async () => {
    jest.useFakeTimers();
    const { withLookupBudget, LOOKUP_OUT_OF_TIME, LOOKUP_GRACE_MS } = await import('@/lib/fetch-timeout');
    let outcome = 'pending';
    withLookupBudget(1000, () => new Promise(() => {})).then(() => (outcome = 'answered'), (e) => (outcome = String(e)));
    await jest.advanceTimersByTimeAsync(1000 + LOOKUP_GRACE_MS + 50);
    expect(outcome).toContain(LOOKUP_OUT_OF_TIME);
  });
});

describe('/api/property when only the lot shape also answers', () => {
  const realFetch = global.fetch;
  beforeEach(() => {
    mockDb.query.mockImplementation(dbDown);
    mockDb.connect.mockImplementation(dbDown);
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
  });
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it('(a) the road map failing leaves corner lot and frontage unknown, never "not a corner lot"', async () => {
    global.fetch = fetchWith((url, init) => (url.includes('/ePlanningApi/lot?') ? replay(url, init) : fails()));
    const { status, body } = await lookup();
    expect(status).toBe(200);
    // the lot answered, so its shape, size and strata status are real answers
    const fromLot = /^(lotDetails|lotDimensions)\.|^strataInfo\./;
    expect(fillIns(body.data).filter((f) => !fromLot.test(f))).toEqual([]);
    expect(body.data.cornerLot.isCornerLot).toBeNull();
    expect([...body.data.constraints.notChecked].sort()).toEqual(LOOKUP_CHECKS.filter((c) => c !== 'lot_shape').sort());
  });
});

describe('strata status', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it('a lot service that answers with no lot records leaves strata unknown, not "No"', async () => {
    mockDb.query.mockResolvedValue({ rows: [] });
    mockDb.connect.mockResolvedValue({ query: async () => ({ rows: [] }), release() {} });
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
    global.fetch = jest.fn((input: any, init: any) => (String(input).includes('/ePlanningApi/lot?')
      ? Promise.resolve(new Response('[]', { status: 200 }))
      : replay(String(input), init))) as any;
    const { body } = await lookup();
    expect(body.data.strataInfo.isStrata).toBeNull();
  });
});

describe('lot shape', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it('a lot record with no shape names lot_shape "not checked"', async () => {
    mockDb.query.mockResolvedValue({ rows: [] });
    mockDb.connect.mockResolvedValue({ query: async () => ({ rows: [] }), release() {} });
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
    global.fetch = jest.fn((input: any, init: any) => (String(input).includes('/ePlanningApi/lot?')
      ? Promise.resolve(new Response(JSON.stringify([{ geometry: null, attributes: { LotDescription: '1//DP1' } }]), { status: 200 }))
      : replay(String(input), init))) as any;
    const { body } = await lookup();
    expect(body.data.constraints.notChecked).toContain('lot_shape');
    expect(body.data.lotDimensions).toBeNull();
  });
});

describe('site-specific LEP clauses', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it('carry the plan name and link the zoning layer gives, never a guessed year or the heritage link', async () => {
    mockDb.query.mockResolvedValue({ rows: [] });
    mockDb.connect.mockResolvedValue({ query: async () => ({ rows: [] }), release() {} });
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
    mockClauses.override = ['6.20'];
    // Mark the zoning layer's plan name and link, so a guessed name or a borrowed link cannot pass.
    const marked = (url: string, init: any) => {
      if (!url.includes('/layerintersect?')) return replay(url, init);
      const layers = JSON.parse(replies[key(url, init)].body);
      for (const l of layers) {
        if (l.layerName !== 'Land Zoning Map') continue;
        for (const r of l.results) Object.assign(r, { 'EPI Name': 'MARKER Plan 1999', legislationUrl: 'https://marker.invalid/plan' });
      }
      return Promise.resolve(new Response(JSON.stringify(layers), { status: 200 }));
    };
    global.fetch = jest.fn((input: any, init: any) => marked(String(input), init)) as any;
    const { body } = await lookup();
    mockClauses.override = null;
    const zoning = body.data.planningLayers.find((l: any) => l.layerName === 'Land Zoning Map').results[0];
    const clause = body.data.constraints.localProvisions.find((p: any) => p.mapType === 'Site-Specific');
    expect(clause.epiName).toBe(zoning['EPI Name']);
    expect(clause.legislationUrl).toBe(zoning.legislationUrl);
  });
});

describe('pattern-book exclusions (lib/pattern-book-eligibility/check-exclusions.ts)', () => {
  it('no environmental answers, unknown heritage, or no planning layers: those exclusions are not checked, not clear', async () => {
    const { uncheckedExclusions } = await import('@/lib/pattern-book-eligibility/check-exclusions');
    expect(uncheckedExclusions({}).sort()).toEqual(['bushfire_prone', 'flood_planning_area', 'heritage']);
    expect(uncheckedExclusions({
      heritage: { isHeritage: null },
      environmental: { floodProne: false, bushfireProne: false, uncheckedHazards: [] },
      notChecked: ['planning_layers'],
    }).sort()).toEqual(['acid_sulfate_soils', 'heritage']);
  });
});

describe('fetchWithTimeout (lib/fetch-timeout.ts)', () => {
  const realFetch = global.fetch;
  afterEach(() => {
    global.fetch = realFetch;
    jest.useRealTimers();
  });

  it('cuts off a reply that sent its headers and then stalled, at the call limit', async () => {
    jest.useFakeTimers();
    global.fetch = jest.fn((_u: any, init: any) => Promise.resolve({
      ok: true,
      status: 200,
      text: () => new Promise((_, reject) => init?.signal?.addEventListener('abort', () => reject(new Error('aborted')))),
    } as unknown as Response)) as any;
    const { fetchWithTimeout } = await import('@/lib/fetch-timeout');
    let outcome = 'pending';
    fetchWithTimeout('https://example.invalid/q', {}, 1000).then(() => (outcome = 'answered'), () => (outcome = 'rejected'));
    await jest.advanceTimersByTimeAsync(1100);
    expect(outcome).toBe('rejected');
  });
});

describe('/api/property is repeatable', () => {
  const realFetch = global.fetch;
  beforeEach(() => {
    mockDb.query.mockResolvedValue({ rows: [] });
    mockDb.connect.mockResolvedValue({ query: async () => ({ rows: [] }), release() {} });
    for (const m of ['log', 'warn', 'error'] as const) jest.spyOn(console, m).mockImplementation(() => {});
  });
  afterEach(() => {
    global.fetch = realFetch;
    jest.restoreAllMocks();
  });

  it('(b) the same recorded replies twice give the same reply, minus the timestamp', async () => {
    global.fetch = jest.fn((input: any, init: any) => replay(String(input), init)) as any;
    const first = await lookup();
    const second = await lookup();
    expect(first.status).toBe(200);
    expect(first.body.data.constraints.zone).toBeTruthy(); // the recording answered: a real lookup, not an empty one
    delete first.body.metadata.timestamp;
    delete second.body.metadata.timestamp;
    expect(second).toEqual(first);
  });
});
