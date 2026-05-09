/**
 * POST /api/reports/pre-da-history/generate
 * @jest-environment node
 *
 * Tests: input validation, DB not-found, incomplete report guard,
 * Path A is_paid=true, Path B (direct data) is_paid=false,
 * happy path, render failure.
 */

import { NextRequest } from 'next/server';

jest.mock('@react-pdf/renderer', () => ({
  renderToBuffer: jest.fn(),
}));

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

jest.mock('@/lib/pdf/logo', () => ({
  getLogoBase64: jest.fn().mockReturnValue('mock-logo-b64'),
}));

jest.mock('@/lib/pdf/pre-da-history-report', () => ({
  PreDAHistoryReportDocument: () => null,
}));

import { POST } from '@/app/api/reports/pre-da-history/generate/route';
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

const VALID_UUID = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890';

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/reports/pre-da-history/generate', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const COMPLETE_ROW = {
  address: '42 George St Newtown NSW 2042',
  run_date: '2026-05-01',
  report_json: {
    address: '42 George St Newtown NSW 2042',
    run_date: '2026-05-01',
    lat: -33.8975,
    lon: 151.1785,
    council: 'Inner West Council',
    heritage_flag: false,
    heritage_note: null,
    timeline: [
      { year: 2020, level: 'stable', label: 'Stable', similarity: 0.94 },
      { year: 2021, level: 'major', label: 'Major change', similarity: 0.52 },
    ],
    wayback_ssim: { '2020-2021': 0.58 },
    data_quality_note: '',
  },
};

const DIRECT_DATA = {
  address: '42 George St Newtown NSW 2042',
  lat: -33.8975,
  lon: 151.1785,
  council: 'Inner West Council',
  heritage_flag: false,
  timeline: [
    { year: 2020, level: 'stable', label: 'Stable' },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
  mockRender.mockResolvedValue(Buffer.from('%PDF-mock') as any);
});

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

describe('POST /api/reports/pre-da-history/generate — input validation', () => {
  it('returns 400 when body is not valid JSON', async () => {
    const req = new NextRequest('http://localhost/api/reports/pre-da-history/generate', {
      method: 'POST', body: 'not-json', headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it('returns 400 when neither report_id nor data is provided', async () => {
    const res = await POST(makeReq({}));
    expect(res.status).toBe(400);
  });

  it('returns 400 when data is provided but address is missing', async () => {
    const res = await POST(makeReq({ data: { lat: -33.89, lon: 151.17 } }));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/address/i);
  });
});

// ---------------------------------------------------------------------------
// Path A: DB (production)
// ---------------------------------------------------------------------------

describe('POST /api/reports/pre-da-history/generate — Path A (DB)', () => {
  it('returns 404 when report_id does not exist', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: { message: 'Not found' } });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(404);
  });

  it('returns 422 when report_json has no timeline', async () => {
    mockSingle.mockResolvedValueOnce({
      data: { ...COMPLETE_ROW, report_json: { address: 'Test' } },
      error: null,
    });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(422);
  });

  it('queries pre_da_history_reports with the correct report_id', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    await POST(makeReq({ report_id: VALID_UUID }));
    expect(mockFrom).toHaveBeenCalledWith('pre_da_history_reports');
    expect(mockEq).toHaveBeenCalledWith('id', VALID_UUID);
  });

  it('returns 200 with application/pdf', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/pdf');
  });

  it('passes is_paid: true for DB-fetched reports', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    await POST(makeReq({ report_id: VALID_UUID }));
    const renderedProps = (mockRender.mock.calls[0][0] as any).props?.data as Record<string, unknown>;
    expect(renderedProps.is_paid).toBe(true);
  });

  it('sets Content-Disposition with report_id prefix', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    const disposition = res.headers.get('Content-Disposition');
    expect(disposition).toMatch(/attachment/);
    expect(disposition).toMatch(/a1b2c3d4/);
  });
});

// ---------------------------------------------------------------------------
// Path B: Direct data (testing / preview)
// ---------------------------------------------------------------------------

describe('POST /api/reports/pre-da-history/generate — Path B (direct data)', () => {
  it('returns 200 with application/pdf', async () => {
    const res = await POST(makeReq({ data: DIRECT_DATA }));
    expect(res.status).toBe(200);
    expect(res.headers.get('Content-Type')).toBe('application/pdf');
  });

  it('passes is_paid: false for direct data path', async () => {
    await POST(makeReq({ data: DIRECT_DATA }));
    const renderedProps = (mockRender.mock.calls[0][0] as any).props?.data as Record<string, unknown>;
    expect(renderedProps.is_paid).toBe(false);
  });

  it('sets Content-Disposition with address slug', async () => {
    const res = await POST(makeReq({ data: DIRECT_DATA }));
    const disposition = res.headers.get('Content-Disposition');
    expect(disposition).toMatch(/attachment/);
    expect(disposition).toMatch(/42-george-st-newtown/i);
  });
});

// ---------------------------------------------------------------------------
// Render failure
// ---------------------------------------------------------------------------

describe('POST /api/reports/pre-da-history/generate — render failure', () => {
  it('returns 500 when renderToBuffer throws', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    mockRender.mockRejectedValueOnce(new Error('Font load failure'));
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/PDF generation failed/i);
  });
});
