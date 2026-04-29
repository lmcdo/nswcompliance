/**
 * POST /api/reports/granny-flat/generate
 * @jest-environment node
 *
 * Tests: input validation, DB not-found, incomplete report guard, happy path.
 * @react-pdf/renderer is mocked — we verify the route wiring, not the PDF layout.
 */

import { NextRequest } from 'next/server';

// ---------------------------------------------------------------------------
// Mock @react-pdf/renderer before importing the route
// ---------------------------------------------------------------------------

jest.mock('@react-pdf/renderer', () => ({
  renderToBuffer: jest.fn(),
}));

// ---------------------------------------------------------------------------
// Mock Supabase service role client (@supabase/supabase-js)
// Route uses createServiceClient directly, not @/lib/supabase/server
// ---------------------------------------------------------------------------

jest.mock('@supabase/supabase-js', () => {
  const mockSingle = jest.fn();
  const mockEq = jest.fn(() => ({ single: mockSingle }));
  const mockSelect = jest.fn(() => ({ eq: mockEq }));
  const mockFrom = jest.fn(() => ({ select: mockSelect }));
  return {
    createClient: jest.fn(() => ({ from: mockFrom })),
    __mocks: { mockSingle, mockEq, mockFrom },
  };
});

jest.mock('@/lib/supabase/server', () => ({
  createClient: jest.fn(async () => ({ from: jest.fn() })),
}));

// ---------------------------------------------------------------------------
// Mock aerial-tile and logo (server-side fetches not needed in tests)
// ---------------------------------------------------------------------------

jest.mock('@/lib/pdf/aerial-tile', () => ({
  fetchAerialTileBase64: jest.fn().mockResolvedValue(null),
}));

jest.mock('@/lib/pdf/logo', () => ({
  getLogoBase64: jest.fn().mockReturnValue('mock-logo-b64'),
}));

// ---------------------------------------------------------------------------
// Mock the PDF document component (renderToBuffer receives it, we don't care)
// ---------------------------------------------------------------------------

jest.mock('@/lib/pdf/granny-flat-report', () => ({
  GrannyFlatReportDocument: () => null,
}));

import { POST } from '@/app/api/reports/granny-flat/generate/route';
import { renderToBuffer } from '@react-pdf/renderer';
import * as supabasePkg from '@supabase/supabase-js';

const mockRender = renderToBuffer as jest.MockedFunction<typeof renderToBuffer>;

/* eslint-disable @typescript-eslint/no-explicit-any */
const { mockSingle, mockEq, mockFrom } = (supabasePkg as any).__mocks as {
  mockSingle: jest.Mock;
  mockEq: jest.Mock;
  mockFrom: jest.Mock;
};
/* eslint-enable @typescript-eslint/no-explicit-any */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const VALID_UUID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/reports/granny-flat/generate', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const COMPLETE_ROW = {
  address: '5 Commercial Rd Haberfield NSW 2045',
  run_date: '2026-04-25',
  inputs: {
    lot_area_m2: 600,
    main_dwelling_area_m2: 180,
    confirmed_structure_count: 2,
    postcode: '2045',
    existing_secondary_dwelling: false,
  },
  outputs: {
    granny_flat_buildable: true,
    max_floor_area_m2: 60,
    estimated_weekly_rent_aud: 450,
    rental_yield_annual_pct: 8.2,
    assumed_build_cost_aud: 150000,
    confidence: 'high',
    confidence_reason: 'Lot area confirmed, zone verified',
    warnings: [],
    data_sources: ['NSW Planning Portal', 'SAMGeo structure detection'],
  },
  confidence: 'high',
};

beforeEach(() => {
  jest.clearAllMocks();
  mockRender.mockResolvedValue(Buffer.from('%PDF-mock') as any);
});

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

describe('POST /api/reports/granny-flat/generate — input validation', () => {
  it('returns 400 when report_id is missing', async () => {
    const res = await POST(makeReq({}));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/report_id/i);
  });

  it('returns 400 when report_id is empty string', async () => {
    const res = await POST(makeReq({ report_id: '   ' }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when body is not valid JSON', async () => {
    const req = new NextRequest('http://localhost/api/reports/granny-flat/generate', {
      method: 'POST',
      body: 'not-json',
      headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});

// ---------------------------------------------------------------------------
// DB not-found
// ---------------------------------------------------------------------------

describe('POST /api/reports/granny-flat/generate — DB not found', () => {
  it('returns 404 when report_id does not exist', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: { message: 'Not found' } });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(404);
    const body = await res.json();
    expect(body.error).toMatch(/not found/i);
  });

  it('returns 404 when supabase returns null data with no error', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: null });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// Incomplete report guard
// ---------------------------------------------------------------------------

describe('POST /api/reports/granny-flat/generate — incomplete report', () => {
  it('returns 422 when outputs is null', async () => {
    mockSingle.mockResolvedValueOnce({
      data: { ...COMPLETE_ROW, outputs: null },
      error: null,
    });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(422);
    const body = await res.json();
    expect(body.error).toMatch(/not yet complete/i);
  });

  it('returns 422 when granny_flat_buildable is missing from outputs', async () => {
    mockSingle.mockResolvedValueOnce({
      data: {
        ...COMPLETE_ROW,
        outputs: { confidence: 'pending' }, // no granny_flat_buildable
      },
      error: null,
    });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(422);
  });
});

// ---------------------------------------------------------------------------
// Happy path
// ---------------------------------------------------------------------------

describe('POST /api/reports/granny-flat/generate — happy path', () => {
  it('returns 200 with application/pdf content-type', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/pdf');
  });

  it('sets Content-Disposition attachment with report_id prefix', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    const disposition = res.headers.get('Content-Disposition');
    expect(disposition).toMatch(/attachment/);
    expect(disposition).toMatch(/a1b2c3d4/); // first 8 chars of VALID_UUID
  });

  it('queries granny_flat_reports with the correct report_id', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    await POST(makeReq({ report_id: VALID_UUID }));
    expect(mockFrom).toHaveBeenCalledWith('granny_flat_reports');
    expect(mockEq).toHaveBeenCalledWith('id', VALID_UUID);
  });

  it('calls renderToBuffer once', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    await POST(makeReq({ report_id: VALID_UUID }));
    expect(mockRender).toHaveBeenCalledTimes(1);
  });

  it('trims whitespace from report_id before querying', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    await POST(makeReq({ report_id: `  ${VALID_UUID}  ` }));
    expect(mockEq).toHaveBeenCalledWith('id', VALID_UUID);
  });
});

// ---------------------------------------------------------------------------
// PDF render failure
// ---------------------------------------------------------------------------

describe('POST /api/reports/granny-flat/generate — render failure', () => {
  it('returns 500 when renderToBuffer throws', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    mockRender.mockRejectedValueOnce(new Error('Font load failure'));
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/PDF generation failed/i);
  });
});
