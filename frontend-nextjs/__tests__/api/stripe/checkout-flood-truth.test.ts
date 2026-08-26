/**
 * POST /api/stripe/checkout/flood-truth
 * @jest-environment node
 */

import { NextRequest } from 'next/server';

jest.mock('stripe', () => {
  const create = jest.fn();
  (globalThis as Record<string, unknown>).__stripeMockCreate = create;
  return {
    __esModule: true,
    default: jest.fn().mockImplementation(() => ({
      checkout: { sessions: { create } },
    })),
  };
});

import { POST } from '@/app/api/stripe/checkout/flood-truth/route';

const mockCreate = (globalThis as Record<string, unknown>).__stripeMockCreate as jest.Mock;

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/stripe/checkout/flood-truth', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

// The route now resolves its Stripe client lazily via getStripe(), which
// returns null (skipping the checkout entirely) when STRIPE_SECRET_KEY is
// unset. Next.js never loads .env.local under NODE_ENV=test, so this must be
// set explicitly for the mocked Stripe constructor to ever be reached.
beforeAll(() => {
  process.env.STRIPE_SECRET_KEY = 'test-stripe-key';
});

const VALID_REPORT_ID = 'flood-uuid-1234-5678-abcd';
const VALID_ADDRESS   = '23 Flood St Lismore NSW 2480';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_FLOOD_TRUTH_PRICE_ID = 'price_flood_test_123';
  process.env.NEXT_PUBLIC_SITE_URL = 'https://plotdetect.com.au';
  mockCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_flood' });
});

afterEach(() => {
  delete process.env.STRIPE_FLOOD_TRUTH_PRICE_ID;
});

describe('POST /api/stripe/checkout/flood-truth — input validation', () => {
  it('returns 400 on invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/flood-truth', {
      method: 'POST', body: 'not-json', headers: { 'Content-Type': 'application/json' },
    });
    expect((await POST(req)).status).toBe(400);
  });

  it('returns 400 when report_id is missing', async () => {
    const res = await POST(makeReq({ address: VALID_ADDRESS }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/report_id/i);
  });

  it('returns 400 when report_id is empty', async () => {
    expect((await POST(makeReq({ report_id: '  ', address: VALID_ADDRESS }))).status).toBe(400);
  });

  it('returns 400 when address is missing', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/address/i);
  });

  it('returns 500 when STRIPE_FLOOD_TRUTH_PRICE_ID not set', async () => {
    delete process.env.STRIPE_FLOOD_TRUTH_PRICE_ID;
    expect((await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }))).status).toBe(500);
  });
});

describe('POST /api/stripe/checkout/flood-truth — happy path (no email)', () => {
  it('returns 200 + checkout_url without email', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(200);
    expect((await res.json()).checkout_url).toBe('https://checkout.stripe.com/pay/cs_test_flood');
  });

  it('does NOT set customer_email when email omitted', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate.mock.calls[0][0]).not.toHaveProperty('customer_email');
  });

  it('sets metadata.product = flood-truth-report', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({ product: 'flood-truth-report' }),
    }));
  });

  it('sets report_id and address in metadata', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      metadata: expect.objectContaining({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }),
    }));
  });

  it('success_url contains payment=success, report_id, encoded address', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toContain('payment=success');
    expect(success_url).toContain(`report_id=${VALID_REPORT_ID}`);
    expect(success_url).toContain(encodeURIComponent(VALID_ADDRESS));
    expect(success_url).toContain('/reports/flood');
  });
});

describe('POST /api/stripe/checkout/flood-truth — with email', () => {
  it('sets customer_email when email provided', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, address: VALID_ADDRESS, email: 'test@example.com' }));
    expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      customer_email: 'test@example.com',
    }));
  });
});
