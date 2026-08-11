/**
 * Lot Search API route tests
 * @jest-environment node
 */
import { NextRequest } from 'next/server';
import { POST } from '@/app/api/lot-search/route';

jest.mock('../../lib/db', () => ({ query: jest.fn() }));
jest.mock('../../lib/rate-limit', () => ({
  searchRateLimiter: null,
  checkRateLimit: jest.fn().mockResolvedValue({
    success: true, limit: 20, remaining: 19, reset: Date.now() + 60000,
  }),
  getClientIdentifier: jest.fn().mockReturnValue('127.0.0.1'),
  createRateLimitHeaders: jest.fn().mockReturnValue({}),
}));

import { query } from '../../lib/db';
import { checkRateLimit } from '../../lib/rate-limit';
const mockQuery = query as jest.MockedFunction<typeof query>;
const mockCheckRateLimit = checkRateLimit as jest.MockedFunction<typeof checkRateLimit>;

function makeRequest(body: object, searchParams?: string): NextRequest {
  const url = `http://localhost/api/lot-search${searchParams ? `?${searchParams}` : ''}`;
  return new NextRequest(url, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const SAMPLE_LOT_ROW = {
  lotidstring: 'LOT1//DP123',
  lga_name: 'INNER WEST',
  zone_code: 'R3',
  lot_area_m2: 800,
  lep_height_m: 11,
  lep_fsr: 0.8,
  heritage: false,
  flood_prone: false,
  bushfire_prone: false,
  bushfire_category: null,
  ca_dev_type: 'multi_dwelling',
  ca_realistic_gfa_m2: 480,
  ca_realistic_dwellings: 3,
  ca_binding_constraint: 'lep_fsr',
  ca_confidence: 'high',
  ca_effective_height_m: 11,
  ca_effective_fsr: 0.8,
  ca_buildable_footprint_m2: 500,
  ca_setback_front_m: 6,
  ca_setback_rear_m: 6,
  ca_setback_side_m: 0.9,
  ca_gaps: null,
};

beforeEach(() => { jest.clearAllMocks(); });

// ---------------------------------------------------------------------------
// Search endpoint (default, no ?summary)
// ---------------------------------------------------------------------------

describe('POST /api/lot-search', () => {
  test('returns paginated results with empty filters', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any) // SET LOCAL
      .mockResolvedValueOnce({ rows: [{ count: '1' }] } as any) // COUNT
      .mockResolvedValueOnce({ rows: [SAMPLE_LOT_ROW] } as any); // SELECT

    const res = await POST(makeRequest({}));
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data.total_count).toBe(1);
    expect(data.lots).toHaveLength(1);
    expect(data.lots[0].lotidstring).toBe('LOT1//DP123');
    expect(data.lots[0].ca_dev_type).toBe('multi_dwelling');
    expect(data.lots[0].ca_realistic_gfa_m2).toBe(480);
  });

  test('passes LGA filter as uppercase', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ lga_name: 'inner west' }));

    // COUNT query should have INNER WEST as param
    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('lga_name = $1');
    expect(countCall[1]).toContain('INNER WEST');
  });

  test('builds zone_codes filter with ANY', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ zone_codes: ['R2', 'R3'] }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('zone_code = ANY($1)');
    expect(countCall[1]).toEqual([['R2', 'R3']]);
  });

  test('builds dev_types filter', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ dev_types: ['multi_dwelling', 'residential_flat_r3r4_inner'] }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('ca_dev_type = ANY($1)');
  });

  test('builds area range filter', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ min_area_m2: 400, max_area_m2: 1000 }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('lot_area_m2 >= $1');
    expect(countCall[0]).toContain('lot_area_m2 <= $2');
    expect(countCall[1]).toEqual([400, 1000]);
  });

  test('builds min_dwellings filter', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ min_dwellings: 3 }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('ca_realistic_dwellings >= $1');
    expect(countCall[1]).toEqual([3]);
  });

  test('heritage=false filters for non-heritage lots', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ heritage: false }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('heritage = $1');
    expect(countCall[1]).toEqual([false]);
  });

  test('min_confidence=medium includes medium and high', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ min_confidence: 'medium' }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('ca_confidence = ANY($1)');
    const confParam = countCall[1]![0] as string[];
    expect(confParam).toContain('medium');
    expect(confParam).toContain('high');
    expect(confParam).not.toContain('low');
  });

  test('min_confidence=high includes only high', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ min_confidence: 'high' }));

    const countCall = mockQuery.mock.calls[1];
    const confParam = countCall[1]![0] as string[];
    expect(confParam).toEqual(['high']);
  });

  test('bbox filter uses EXISTS with nsw_cadastre_lots JOIN', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ bbox: [151.1, -33.9, 151.2, -33.8] }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('nsw_cadastre_lots');
    expect(countCall[0]).toContain('ST_MakeEnvelope');
    expect(countCall[1]).toEqual([151.1, -33.9, 151.2, -33.8]);
  });

  test('multiple filters combine with AND', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({
      lga_name: 'INNER WEST',
      zone_codes: ['R3'],
      min_area_m2: 600,
      heritage: false,
    }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain(' AND ');
    // 4 conditions = 3 ANDs
    expect((countCall[0] as string).match(/ AND /g)?.length).toBe(3);
  });

  test('invalid order_by falls back to ca_realistic_gfa_m2', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ order_by: 'DROP TABLE users; --' }));

    const selectCall = mockQuery.mock.calls[2];
    expect(selectCall[0]).toContain('ORDER BY ca_realistic_gfa_m2');
    expect(selectCall[0]).not.toContain('DROP');
  });

  test('pagination passes limit and offset', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '100' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    const res = await POST(makeRequest({ limit: 10, offset: 50 }));
    const data = await res.json();

    expect(data.total_count).toBe(100);
    const selectCall = mockQuery.mock.calls[2];
    expect(selectCall[1]).toContain(10); // limit
    expect(selectCall[1]).toContain(50); // offset
  });

  test('returns 400 for invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/lot-search', {
      method: 'POST',
      body: 'not json',
      headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  test('returns 400 for validation failure', async () => {
    const res = await POST(makeRequest({ limit: 9999 }));
    expect(res.status).toBe(400);
    const data = await res.json();
    expect(data.error).toBe('Validation failed');
  });

  test('returns 400 for invalid order_dir', async () => {
    const res = await POST(makeRequest({ order_dir: 'DROP' }));
    expect(res.status).toBe(400);
  });

  test('returns 400 for invalid bbox length', async () => {
    const res = await POST(makeRequest({ bbox: [1.0, 2.0] }));
    expect(res.status).toBe(400);
  });

  test('returns 504 on statement timeout', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any) // SET LOCAL
      .mockRejectedValueOnce(new Error('canceling statement due to statement timeout'));

    const res = await POST(makeRequest({}));
    expect(res.status).toBe(504);
    const data = await res.json();
    expect(data.error).toContain('timed out');
  });

  test('returns 500 on generic DB error', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockRejectedValueOnce(new Error('connection refused'));

    const res = await POST(makeRequest({}));
    expect(res.status).toBe(500);
  });

  test('null heritage/flood/bushfire stay null — never coerced to false', async () => {
    const lotWithNulls = { ...SAMPLE_LOT_ROW, heritage: null, flood_prone: null, bushfire_prone: null };
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '1' }] } as any)
      .mockResolvedValueOnce({ rows: [lotWithNulls] } as any);

    const res = await POST(makeRequest({}));
    const data = await res.json();
    // A NULL overlay was never resolved for this lot. Served as `false` it
    // read as three clean hazard flags off a lookup that never happened. This
    // test asserted that coercion as intended behaviour until 2026-08-08.
    expect(data.lots[0].heritage).toBeNull();
    expect(data.lots[0].flood_prone).toBeNull();
    expect(data.lots[0].bushfire_prone).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Rate limiting
// ---------------------------------------------------------------------------

describe('Rate limiting', () => {
  test('returns 429 when rate limit exceeded', async () => {
    mockCheckRateLimit.mockResolvedValueOnce({
      success: false, limit: 20, remaining: 0, reset: Date.now() + 60000,
    });

    const res = await POST(makeRequest({}));
    expect(res.status).toBe(429);
    const data = await res.json();
    expect(data.error).toContain('Rate limit');
  });
});

// ---------------------------------------------------------------------------
// Summary endpoint (?summary=true)
// ---------------------------------------------------------------------------

describe('POST /api/lot-search?summary=true', () => {
  test('returns aggregate stats', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any) // SET LOCAL
      .mockResolvedValueOnce({
        rows: [{
          total_lots: '100', lots_with_ca: '80',
          avg_area_m2: 550.123, avg_gfa_m2: 250.456,
          median_gfa_m2: 230.0, p25_gfa_m2: 180.0, p75_gfa_m2: 300.0,
          avg_dwellings: 1.23,
          heritage_count: '10', flood_count: '5', bushfire_count: '3',
          confidence_high: '40', confidence_medium: '30', confidence_low: '10',
        }],
      } as any)
      .mockResolvedValueOnce({ rows: [{ zone_code: 'R3', count: 60 }, { zone_code: 'R2', count: 40 }] } as any)
      .mockResolvedValueOnce({ rows: [{ ca_binding_constraint: 'lep_fsr', count: 50 }] } as any)
      .mockResolvedValueOnce({ rows: [{ ca_dev_type: 'multi_dwelling', count: 45 }] } as any);

    const res = await POST(makeRequest({ lga_name: 'INNER WEST' }, 'summary=true'));
    const data = await res.json();

    expect(res.status).toBe(200);
    expect(data.total_lots).toBe(100);
    expect(data.lots_with_ca).toBe(80);
    expect(data.avg_area_m2).toBe(550.1);
    expect(data.avg_gfa_m2).toBe(250.5);
    expect(data.median_gfa_m2).toBe(230.0);
    expect(data.heritage_count).toBe(10);
    expect(data.confidence_high).toBe(40);
    expect(data.zone_distribution).toHaveLength(2);
    expect(data.zone_distribution[0].zone_code).toBe('R3');
    expect(data.binding_distribution).toHaveLength(1);
    expect(data.dev_type_distribution).toHaveLength(1);
    expect(data.dev_type_distribution[0].ca_dev_type).toBe('multi_dwelling');
  });

  test('returns nulls for empty dataset', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({
        rows: [{
          total_lots: '0', lots_with_ca: '0',
          avg_area_m2: null, avg_gfa_m2: null,
          median_gfa_m2: null, p25_gfa_m2: null, p75_gfa_m2: null,
          avg_dwellings: null,
          heritage_count: '0', flood_count: '0', bushfire_count: '0',
          confidence_high: '0', confidence_medium: '0', confidence_low: '0',
        }],
      } as any)
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    const res = await POST(makeRequest({}, 'summary=true'));
    const data = await res.json();

    expect(data.total_lots).toBe(0);
    expect(data.avg_gfa_m2).toBeNull();
    expect(data.zone_distribution).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Binding constraint filter
// ---------------------------------------------------------------------------

describe('Binding constraint filter', () => {
  test('filters by binding constraint array', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ binding_constraint: ['lep_fsr', 'dcp_setbacks'] }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('ca_binding_constraint = ANY($1)');
    expect(countCall[1]).toEqual([['lep_fsr', 'dcp_setbacks']]);
  });
});

// ---------------------------------------------------------------------------
// Flood/bushfire boolean filters
// ---------------------------------------------------------------------------

describe('Boolean flag filters', () => {
  test('flood_prone=false excludes flood lots', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ flood_prone: false }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('flood_prone = $1');
    expect(countCall[1]).toEqual([false]);
  });

  test('bushfire_prone=true shows only bushfire lots', async () => {
    mockQuery
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ count: '0' }] } as any)
      .mockResolvedValueOnce({ rows: [] } as any);

    await POST(makeRequest({ bushfire_prone: true }));

    const countCall = mockQuery.mock.calls[1];
    expect(countCall[0]).toContain('bushfire_prone = $1');
    expect(countCall[1]).toEqual([true]);
  });
});
