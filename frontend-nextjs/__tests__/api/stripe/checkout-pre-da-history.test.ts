/**
 * POST /api/stripe/checkout/pre-da-history
 * @jest-environment node
 *
 * Tests: input validation, metadata shape, success_url, price ID guard, and
 * the Origin-header trust fix (Sol cross-review, 2026-09-01).
 */

import { NextRequest } from 'next/server';

// jest.mock is hoisted above ALL declarations, so we create the mock fn
// inside the factory and stash it on a global the test can reach.
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

import { POST } from '@/app/api/stripe/checkout/pre-da-history/route';

const mockCreate = (globalThis as Record<string, unknown>).__stripeMockCreate as jest.Mock;

function makeReq(body: unknown, extraHeaders?: Record<string, string>): NextRequest {
  return new NextRequest('http://localhost/api/stripe/checkout/pre-da-history', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  });
}

beforeAll(() => {
  process.env.STRIPE_SECRET_KEY = 'test-stripe-key';
});

const VALID_REPORT_ID = 'preda-uuid-1234-5678-abcd';
const VALID_EMAIL = 'buyer@example.com';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_PRE_DA_HISTORY_PRICE_ID = 'price_preda_test_123';
  process.env.NEXT_PUBLIC_SITE_URL = 'https://verify.plotdetect.com.au';
  mockCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_preda' });
});

afterEach(() => {
  delete process.env.STRIPE_PRE_DA_HISTORY_PRICE_ID;
});

describe('POST /api/stripe/checkout/pre-da-history — input validation', () => {
  it('returns 400 when body is invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/pre-da-history', {
      method: 'POST', body: 'not-json', headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it('returns 400 when report_id is missing', async () => {
    const res = await POST(makeReq({ email: VALID_EMAIL }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/report_id/i);
  });

  it('returns 400 when email is missing', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/email/i);
  });

  it('returns 500 when STRIPE_PRE_DA_HISTORY_PRICE_ID is not set', async () => {
    delete process.env.STRIPE_PRE_DA_HISTORY_PRICE_ID;
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, email: VALID_EMAIL }));
    expect(res.status).toBe(500);
    expect((await res.json()).error).toMatch(/not configured/i);
  });
});

describe('POST /api/stripe/checkout/pre-da-history — happy path', () => {
  it('returns 200 + checkout_url', async () => {
    const res = await POST(makeReq({ report_id: VALID_REPORT_ID, email: VALID_EMAIL }));
    expect(res.status).toBe(200);
    expect((await res.json()).checkout_url).toBe('https://checkout.stripe.com/pay/cs_test_preda');
  });

  it('success_url points to /reports/pre-da-history with payment=success', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, email: VALID_EMAIL }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toContain('/reports/pre-da-history');
    expect(success_url).toContain('payment=success');
    expect(success_url).toContain(`report_id=${VALID_REPORT_ID}`);
  });
});

describe('POST /api/stripe/checkout/pre-da-history — origin resolution (security)', () => {
  // The defect: this route used to build success_url/cancel_url from the raw
  // request Origin header, which is attacker-controlled -- any page can POST
  // here and the browser truthfully reports THAT page's own origin. A
  // customer paying via an attacker-hosted page would be redirected back to
  // the attacker's site, not ours, after a real payment. Fixed 2026-09-01 to
  // read only the server-side env var, matching every sibling checkout route.
  it('ignores an attacker-controlled Origin header entirely', async () => {
    await POST(makeReq(
      { report_id: VALID_REPORT_ID, email: VALID_EMAIL },
      { Origin: 'https://attacker.example' }
    ));
    const { success_url, cancel_url } = mockCreate.mock.calls[0][0] as {
      success_url: string; cancel_url: string;
    };
    expect(success_url).not.toContain('attacker.example');
    expect(cancel_url).not.toContain('attacker.example');
    expect(success_url).toMatch(/^https:\/\/verify\.plotdetect\.com\.au\//);
    expect(cancel_url).toMatch(/^https:\/\/verify\.plotdetect\.com\.au\//);
  });

  it('uses NEXT_PUBLIC_SITE_URL when no Origin header is present at all', async () => {
    await POST(makeReq({ report_id: VALID_REPORT_ID, email: VALID_EMAIL }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toMatch(/^https:\/\/verify\.plotdetect\.com\.au\//);
  });

  it('falls back to the verify subdomain, never the dead bare apex, when the env var is unset', async () => {
    delete process.env.NEXT_PUBLIC_SITE_URL;
    await POST(makeReq({ report_id: VALID_REPORT_ID, email: VALID_EMAIL }));
    const { success_url } = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(success_url).toMatch(/^https:\/\/verify\.plotdetect\.com\.au\//);
  });
});
