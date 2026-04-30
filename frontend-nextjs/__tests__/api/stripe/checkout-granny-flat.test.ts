/**
 * POST /api/stripe/checkout/granny-flat
 * @jest-environment node
 *
 * Tests: input validation, missing price ID, happy path with job_id + address.
 */

import { NextRequest } from 'next/server';

// ---------------------------------------------------------------------------
// Mock Stripe before importing route
// ---------------------------------------------------------------------------

const mockCreate = jest.fn();

jest.mock('stripe', () => {
  return jest.fn().mockImplementation(() => ({
    checkout: {
      sessions: {
        create: mockCreate,
      },
    },
  }));
});

import { POST } from '@/app/api/stripe/checkout/granny-flat/route';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/stripe/checkout/granny-flat', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

const VALID_JOB_ID = 'job-uuid-1234-5678-abcd';
const VALID_ADDRESS = '5 Commercial Rd Haberfield NSW 2045';

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_GRANNY_FLAT_PRICE_ID = 'price_test_123';
  process.env.NEXT_PUBLIC_APP_URL = 'https://canibuildit.com.au';
  mockCreate.mockResolvedValue({ url: 'https://checkout.stripe.com/pay/cs_test_123' });
});

afterEach(() => {
  delete process.env.STRIPE_GRANNY_FLAT_PRICE_ID;
});

// ---------------------------------------------------------------------------
// Input validation
// ---------------------------------------------------------------------------

describe('POST /api/stripe/checkout/granny-flat — input validation', () => {
  it('returns 400 when body is invalid JSON', async () => {
    const req = new NextRequest('http://localhost/api/stripe/checkout/granny-flat', {
      method: 'POST',
      body: 'not-json',
      headers: { 'Content-Type': 'application/json' },
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });

  it('returns 400 when job_id is missing', async () => {
    const res = await POST(makeReq({ address: VALID_ADDRESS }));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/job_id/i);
  });

  it('returns 400 when job_id is empty string', async () => {
    const res = await POST(makeReq({ job_id: '   ', address: VALID_ADDRESS }));
    expect(res.status).toBe(400);
  });

  it('returns 400 when address is missing', async () => {
    const res = await POST(makeReq({ job_id: VALID_JOB_ID }));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/address/i);
  });

  it('returns 500 when STRIPE_GRANNY_FLAT_PRICE_ID is not set', async () => {
    delete process.env.STRIPE_GRANNY_FLAT_PRICE_ID;
    const res = await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/not configured/i);
  });

  it('rejects body with only report_id (old flow shape)', async () => {
    const res = await POST(makeReq({ report_id: 'some-uuid', email: 'a@b.com' }));
    expect(res.status).toBe(400);
  });
});

// ---------------------------------------------------------------------------
// Happy path
// ---------------------------------------------------------------------------

describe('POST /api/stripe/checkout/granny-flat — happy path', () => {
  it('returns checkout_url on success', async () => {
    const res = await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS }));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.checkout_url).toBe('https://checkout.stripe.com/pay/cs_test_123');
  });

  it('sets product metadata to granny-flat-analysis', async () => {
    await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS }));
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        metadata: expect.objectContaining({
          product: 'granny-flat-analysis',
          job_id: VALID_JOB_ID,
          address: VALID_ADDRESS,
        }),
      })
    );
  });

  it('success_url includes jobId and payment=success', async () => {
    await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS }));
    const call = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(call.success_url).toContain(`jobId=${VALID_JOB_ID}`);
    expect(call.success_url).toContain('payment=success');
    expect(call.success_url).toContain(encodeURIComponent(VALID_ADDRESS));
  });

  it('success_url points to /reports/granny-flat', async () => {
    await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS }));
    const call = mockCreate.mock.calls[0][0] as { success_url: string };
    expect(call.success_url).toContain('/reports/granny-flat');
  });

  it('sets customer_email when email provided', async () => {
    await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS, email: 'test@example.com' }));
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ customer_email: 'test@example.com' })
    );
  });

  it('does not set customer_email when email omitted', async () => {
    await POST(makeReq({ job_id: VALID_JOB_ID, address: VALID_ADDRESS }));
    const call = mockCreate.mock.calls[0][0] as Record<string, unknown>;
    expect(call).not.toHaveProperty('customer_email');
  });
});
