/**
 * POST /api/reports/flood/generate
 * @jest-environment node
 *
 * Tests: input validation, DB not-found, Path A is_paid=true, Path B HMAC rejection,
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

jest.mock('@/lib/pdf/aerial-tile', () => ({
  fetchAerialTileBase64: jest.fn().mockResolvedValue(null),
}));

jest.mock('@/lib/pdf/logo', () => ({
  getLogoBase64: jest.fn().mockReturnValue('mock-logo-b64'),
}));

jest.mock('@/lib/report-token', () => ({
  verifyReport: jest.fn().mockReturnValue(false),
}));

jest.mock('@/lib/pdf/flood-truth-report', () => ({
  FloodTruthReportDocument: () => null,
}));

import { POST } from '@/app/api/reports/flood/generate/route';
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
  return new NextRequest('http://localhost/api/reports/flood/generate', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const COMPLETE_ROW = {
  address: '22 River Rd Windsor NSW 2756',
  lat: -33.61,
  lng: 150.81,
  run_date: '2026-05-01',
  confidence: 'high',
  data_sources: ['Sentinel-1', 'EPI Flood'],
  outputs: {
    flood_signal: 'high',
    in_100yr_flood_zone: true,
    epi_flood_class: 'flood_planning',
  },
};

beforeEach(() => {
  jest.clearAllMocks();
  mockRender.mockResolvedValue(Buffer.from('%PDF-mock') as any);
});

describe('POST /api/reports/flood/generate — input validation', () => {
  it('returns 400 when body is not valid JSON', async () => {
    const req = new NextRequest('http://localhost/api/reports/flood/generate', {
      method: 'POST', body: 'not-json', headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it('returns 400 when neither report_id nor data is provided', async () => {
    const res = await POST(makeReq({}));
    expect(res.status).toBe(400);
  });
});

describe('POST /api/reports/flood/generate — Path A (DB)', () => {
  it('returns 404 when report_id does not exist', async () => {
    mockSingle.mockResolvedValueOnce({ data: null, error: { message: 'Not found' } });
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(404);
  });

  it('queries property_reports with the correct report_id', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    await POST(makeReq({ report_id: VALID_UUID }));
    expect(mockFrom).toHaveBeenCalledWith('property_reports');
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
});

describe('POST /api/reports/flood/generate — Path B (HMAC)', () => {
  it('returns 403 when HMAC token is invalid', async () => {
    const res = await POST(makeReq({
      data: { address: '1 Test St', lat: -33.61, lng: 150.81, run_date: '2026-05-01' },
      report_token: 'bad-token',
    }));
    expect(res.status).toBe(403);
  });
});

describe('POST /api/reports/flood/generate — render failure', () => {
  it('returns 500 when renderToBuffer throws', async () => {
    mockSingle.mockResolvedValueOnce({ data: COMPLETE_ROW, error: null });
    mockRender.mockRejectedValueOnce(new Error('Font load failure'));
    const res = await POST(makeReq({ report_id: VALID_UUID }));
    expect(res.status).toBe(500);
  });
});
