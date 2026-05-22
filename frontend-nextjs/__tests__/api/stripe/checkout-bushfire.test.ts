/**
 * POST /api/stripe/checkout/bushfire
 * @jest-environment node
 *
 * Tests: input validation, metadata shape, success_url, price ID guard.
 */

import { NextRequest } from 'next/server';

// jest.mock is hoisted above ALL declarations, so we create the mock fn
// inside the factory and stash it on a global the test can reach.
jest.mock('stripe', () => {
  const create = jest.fn();
  // Expose via globalThis so tests can access it after import
  (globalThis as Record<string, unknown>).__stripeMockCreate = create;
  return {
    __esModule: true,
    default: jest.fn().mockImplementation(() => ({
      checkout: { sessions: { create } },
    })),
  };
});

import { POST } from '@/app/api/stripe/checkout/bushfire/route';

// Retrieve the mock function that was created inside the jest.mock factory
const mockCreate = (globalThis as Record<string, unknown>).__stripeMockCreate as jest.Mock;

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/stripe/checkout/bushfire', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const VALID_REPORT_ID = 'bush-uuid-1234-5678-abcd';
const VALID_ADDRESS   = '15 Mountain Rd Springwood NSW 2777';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_BUSHFIRE_PRICE_ID = 'price_bush_test_123';
  process.env.NEXT_PUBLIC_SITE_URL = 'https://plotdetect.com.au';
  mockCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_bush' });
});

afterEach(() => {
  delete process.env.STRIPE_BUSHFIRE_PRICE_ID;
});

describe('POST /api/stripe/checkout/bushfire — input validation', () => {
  it('returns 400 when body is invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/bushfire', {
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

  it('returns 400 when address is missing', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/address/i);
  });

  it('returns 500 when STRIPE_BUSHFIRE_PRICE_ID is not set', async () => {
    delete process.env.STRIPE_BUSHFIRE_PRICE_ID;
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(500);
    expect((await res.json()).error).toMatch(/not configured/i);
  });
});

describe('POST /api/stripe/checkout/bushfire — happy path', () => {
  it('returns 200 + checkout_url', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(200);
    expect((await res.json()).checkout_url).toBe('https://checkout.stripe.com/pay/cs_test_bush');
  });

  it('sets product metadata to bushfire-report', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({ product: 'bushfire-report' }),
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

  it('success_url points to /reports/bushfire with payment=success', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toContain('/reports/bushfire');
    expect(success_url).toContain('payment=success');
    expect(success_url).toContain(`report_id=${VALID_REPORT_ID}`);
  });
});

describe('POST /api/stripe/checkout/bushfire — with email', () => {
  it('sets customer_email when email provided', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS, email: 'buyer@example.com' }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      customer_email: 'buyer@example.com',
    }));
  });
});
