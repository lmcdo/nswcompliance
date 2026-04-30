/**
 * POST /api/stripe/checkout/solar-yield
 * @jest-environment node
 *
 * Tests: input validation, optional email, metadata shape, success_url, price ID guard.
 */

import { NextRequest } from 'next/server';

const mockCreate = jest.fn();

jest.mock('stripe', () => {
  return jest.fn().mockImplementation(() => ({
    checkout: { sessions: { create: mockCreate } },
  }));
});

import { POST } from '@/app/api/stripe/checkout/solar-yield/route';

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/stripe/checkout/solar-yield', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const VALID_REPORT_ID = 'sol-uuid-1234-5678-abcd';
const VALID_ADDRESS   = '5 Commercial Rd Haberfield NSW 2045';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_SOLAR_YIELD_PRICE_ID = 'price_sol_test_123';
  process.env.NEXT_PUBLIC_APP_URL = 'https://canibuildit.com.au';
  mockCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_sol' });
});

afterEach(() => {
  delete process.env.STRIPE_SOLAR_YIELD_PRICE_ID;
});

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

describe('POST /api/stripe/checkout/solar-yield — input validation', () => {
  it('returns 400 when body is invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/solar-yield', {
      method: 'POST', body: 'not-json', headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it('returns 400 when report_id is missing', async () => {
    const res = await POST(makeReq({ address: VALID_ADDRESS }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/report_id/i);
  });

  it('returns 400 when report_id is empty string', async () => {
    const res = await POST(makeReq({ report_id: '   ', address: VALID_ADDRESS }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when address is missing', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/address/i);
  });

  it('returns 500 when STRIPE_SOLAR_YIELD_PRICE_ID is not set', async () => {
    delete process.env.STRIPE_SOLAR_YIELD_PRICE_ID;
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(500);
    expect((await res.json()).error).toMatch(/not configured/i);
  });

  it('rejects body with only email (old shape)', async () => {
    const res = await POST(makeReq({ email: 'a@b.com' }));
    expect(res.status).toBe(400);
  });
});

// ---------------------------------------------------------------------------
// Happy path — no email
// ---------------------------------------------------------------------------

describe('POST /api/stripe/checkout/solar-yield — happy path (no email)', () => {
  it('returns 200 + checkout_url without email', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(200);
    expect((await res.json()).checkout_url).toBe('https://checkout.stripe.com/pay/cs_test_sol');
  });

  it('does NOT set customer_email when email omitted', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    const call = mockCreate.mock.calls[0][0] as Record<string, unknown>;
    expect(call).not.toHaveProperty('customer_email');
  });

  it('sets product metadata to solar-yield-report', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({ product: 'solar-yield-report' }),
    }));
  });

  it('sets report_id and address in metadata', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({
        report_id: VALID_REPORT_ID,
        address: VALID_ADDRESS,
      }),
    }));
  });

  it('success_url contains payment=success, report_id, and encoded address', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toContain('payment=success');
    expect(success_url).toContain(`report_id=${VALID_REPORT_ID}`);
    expect(success_url).toContain(encodeURIComponent(VALID_ADDRESS));
  });

  it('success_url points to /reports/solar-yield', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toContain('/reports/solar-yield');
  });
});

// ---------------------------------------------------------------------------
// Happy path — with email
// ---------------------------------------------------------------------------

describe('POST /api/stripe/checkout/solar-yield — with email', () => {
  it('returns 200 + checkout_url with email', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS, email: 'buyer@example.com' }));
    expect(res.status).toBe(200);
  });

  it('sets customer_email when email provided', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS, email: 'buyer@example.com' }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      customer_email: 'buyer@example.com',
    }));
  });
});
