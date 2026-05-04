/**
 * POST /api/stripe/checkout/shadow
 * @jest-environment node
 */

import { NextRequest } from 'next/server';

const mockCreate = jest.fn();

jest.mock('stripe', () => {
  return jest.fn().mockImplementation(() => ({
    checkout: { sessions: { create: mockCreate } },
  }));
});

import { POST } from '@/app/api/stripe/checkout/shadow/route';

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/stripe/checkout/shadow', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const VALID_REPORT_ID = 'shadow-uuid-1234-5678-abcd';
const VALID_ADDRESS   = '5 Elm St Haberfield NSW 2045';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_SHADOW_PRICE_ID = 'price_shadow_test_123';
  process.env.NEXT_PUBLIC_SITE_URL = 'https://canibuildit.com.au';
  mockCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_shadow' });
});

afterEach(() => {
  delete process.env.STRIPE_SHADOW_PRICE_ID;
});

describe('POST /api/stripe/checkout/shadow — input validation', () => {
  it('returns 400 on invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/shadow', {
      method: 'POST', body: 'not-json', headers: { 'Content-Type': 'application/json' },
    });
    expect((await POST(req)).status).toBe(400);
  });

  it('returns 400 when report_id missing', async () => {
    const res = await POST(makeReq({ address: VALID_ADDRESS }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/report_id/i);
  });

  it('returns 400 when report_id is empty', async () => {
    expect((await POST(makeReq({ report_id: '  ', address: VALID_ADDRESS }))).status).toBe(400);
  });

  it('returns 400 when address missing', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/address/i);
  });

  it('returns 500 when STRIPE_SHADOW_PRICE_ID not set', async () => {
    delete process.env.STRIPE_SHADOW_PRICE_ID;
    expect((await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }))).status).toBe(500);
  });
});

describe('POST /api/stripe/checkout/shadow — happy path (no email)', () => {
  it('returns 200 + checkout_url', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(200);
    expect((await res.json()).checkout_url).toBe('https://checkout.stripe.com/pay/cs_test_shadow');
  });

  it('does NOT set customer_email when email omitted', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate.mock.calls[0][0]).not.toHaveProperty('customer_email');
  });

  it('metadata.product = shadow-report', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({ product: 'shadow-report' }),
    }));
  });

  it('sets report_id and address in metadata', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }),
    }));
  });

  it('success_url contains payment=success, report_id, encoded address, /reports/shadow', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toContain('payment=success');
    expect(success_url).toContain(`report_id=${VALID_REPORT_ID}`);
    expect(success_url).toContain(encodeURIComponent(VALID_ADDRESS));
    expect(success_url).toContain('/reports/shadow');
  });
});

describe('POST /api/stripe/checkout/shadow — with email', () => {
  it('sets customer_email when provided', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS, email: 'test@test.com' }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({ customer_email: 'test@test.com' }));
  });
});
