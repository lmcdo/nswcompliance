/**
 * GET /api/reports/granny-flat/nearby
 * @jest-environment node
 *
 * Covers: param validation, bounding box query, buildable filter,
 * max results cap, field projection, empty result, Supabase error.
 */

import { NextRequest } from 'next/server';

// ---------------------------------------------------------------------------
// Mock Supabase
// ---------------------------------------------------------------------------

const mockLimit = jest.fn();
const mockOrder = jest.fn(() => ({ limit: mockLimit }));
const mockLteByField: Record<string, jest.Mock> = {};
const mockGteByField: Record<string, jest.Mock> = {};

// Chain: .gte(field, val).lte(field, val).gte(field, val).lte(field, val).order().limit()
// Build a chainable mock that records calls
const mockLte2 = jest.fn(() => ({ order: mockOrder }));
const mockGte2 = jest.fn(() => ({ lte: mockLte2 }));
const mockLte1 = jest.fn(() => ({ gte: mockGte2 }));
const mockGte1 = jest.fn(() => ({ lte: mockLte1 }));
const mockEq = jest.fn(() => ({ gte: mockGte1 }));
const mockSelect = jest.fn(() => ({ eq: mockEq }));
const mockFrom = jest.fn(() => ({ select: mockSelect }));

jest.mock('@/lib/supabase/server', () => ({
  createClient: jest.fn(async () => ({ from: mockFrom })),
}));

import { GET } from '@/app/api/reports/granny-flat/nearby/route';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const LAT = -33.8688;
const LNG = 151.2093;

function makeReq(params: Record<string, string>): NextRequest {
  const url = new URL('http://localhost/api/reports/granny-flat/nearby');
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  return new NextRequest(url.toString());
}

const ELIGIBLE_ROW = {
  address: '5 Smith St Marrickville NSW 2204',
  run_date: '2026-04-25',
  outputs: {
    granny_flat_buildable: true,
    max_floor_area_m2: 60,
    estimated_weekly_rent_aud: 450,
  },
};

const INELIGIBLE_ROW = {
  address: '3 Jones Ave Marrickville NSW 2204',
  run_date: '2026-04-24',
  outputs: {
    granny_flat_buildable: false,
    max_floor_area_m2: 0,
    estimated_weekly_rent_aud: null,
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  mockLimit.mockResolvedValue({ data: [], error: null });
});

// ---------------------------------------------------------------------------
// Param validation
// ---------------------------------------------------------------------------

describe('GET /api/reports/granny-flat/nearby — param validation', () => {
  it('returns 400 when lat is missing', async () => {
    const res = await GET(makeReq({ lng: String(LNG) }));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/lat/i);
  });

  it('returns 400 when lng is missing', async () => {
    const res = await GET(makeReq({ lat: String(LAT) }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when lat is out of range', async () => {
    const res = await GET(makeReq({ lat: '200', lng: String(LNG) }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when lat is not a number', async () => {
    const res = await GET(makeReq({ lat: 'abc', lng: String(LNG) }));
    expect(res.status).toBe(400);
  });
});

// ---------------------------------------------------------------------------
// Happy path
// ---------------------------------------------------------------------------

describe('GET /api/reports/granny-flat/nearby — happy path', () => {
  it('returns 200 with eligible results array', async () => {
    mockLimit.mockResolvedValueOnce({ data: [ELIGIBLE_ROW], error: null });
    const res = await GET(makeReq({ lat: String(LAT), lng: String(LNG) }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(Array.isArray(body.results)).toBe(true);
    expect(body.results).toHaveLength(1);
  });

  it('filters out ineligible rows', async () => {
    mockLimit.mockResolvedValueOnce({ data: [ELIGIBLE_ROW, INELIGIBLE_ROW], error: null });
    const res = await GET(makeReq({ lat: String(LAT), lng: String(LNG) }));
    const body = await res.json();
    expect(body.results).toHaveLength(1);
    expect(body.results[0].address).toBe(ELIGIBLE_ROW.address);
  });

  it('returns projected fields only — no raw outputs blob', async () => {
    mockLimit.mockResolvedValueOnce({ data: [ELIGIBLE_ROW], error: null });
    const res = await GET(makeReq({ lat: String(LAT), lng: String(LNG) }));
    const body = await res.json();
    const row = body.results[0];
    expect(row).toHaveProperty('address');
    expect(row).toHaveProperty('run_date');
    expect(row).toHaveProperty('max_floor_area_m2');
    expect(row).toHaveProperty('estimated_weekly_rent_aud');
    expect(row).not.toHaveProperty('outputs');
  });

  it('caps results at 5 even when DB returns more', async () => {
    const manyRows = Array.from({ length: 10 }, (_, i) => ({
      ...ELIGIBLE_ROW,
      address: `${i} Test St NSW 2000`,
    }));
    mockLimit.mockResolvedValueOnce({ data: manyRows, error: null });
    const res = await GET(makeReq({ lat: String(LAT), lng: String(LNG) }));
    const body = await res.json();
    expect(body.results.length).toBeLessThanOrEqual(5);
  });

  it('returns empty results array when no eligible properties nearby', async () => {
    mockLimit.mockResolvedValueOnce({ data: [], error: null });
    const res = await GET(makeReq({ lat: String(LAT), lng: String(LNG) }));
    const body = await res.json();
    expect(body.results).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Supabase error
// ---------------------------------------------------------------------------

describe('GET /api/reports/granny-flat/nearby — Supabase error', () => {
  it('returns 500 when Supabase returns an error', async () => {
    mockLimit.mockResolvedValueOnce({ data: null, error: { message: 'DB timeout' } });
    const res = await GET(makeReq({ lat: String(LAT), lng: String(LNG) }));
    expect(res.status).toBe(500);
  });
});
