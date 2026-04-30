/**
 * POST /api/stripe/webhook — granny-flat-analysis product handler
 * @jest-environment node
 *
 * Tests: granny-flat-analysis product sends link email (no PDF generation),
 *        graceful on missing metadata, no email if email field absent.
 */

import { NextRequest } from 'next/server';

// ---------------------------------------------------------------------------
// Mock Stripe signature verification
// ---------------------------------------------------------------------------

const mockConstructEvent = jest.fn();

jest.mock('stripe', () => {
  return jest.fn().mockImplementation(() => ({
    webhooks: {
      constructEvent: mockConstructEvent,
    },
    checkout: {
      sessions: {},
    },
  }));
});

// ---------------------------------------------------------------------------
// Mock Resend
// ---------------------------------------------------------------------------

const mockSendEmail = jest.fn().mockResolvedValue({ id: 'mock-email-id' });

jest.mock('resend', () => ({
  Resend: jest.fn().mockImplementation(() => ({
    emails: { send: mockSendEmail },
  })),
}));

import { POST } from '@/app/api/stripe/webhook/route';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeWebhookReq(metadata: Record<string, string>): NextRequest {
  const body = JSON.stringify({ id: 'evt_test', type: 'checkout.session.completed' });
  return new NextRequest('http://localhost/api/stripe/webhook', {
    method: 'POST',
    body,
    headers: {
      'Content-Type': 'application/json',
      'stripe-signature': 'mock-sig',
    },
  });
}

function buildEvent(metadata: Record<string, string>, mode = 'payment') {
  return {
    type: 'checkout.session.completed',
    data: {
      object: {
        id: 'cs_test_123',
        mode,
        metadata,
        subscription: null,
      },
    },
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  process.env.STRIPE_WEBHOOK_SECRET = 'whsec_test';
  process.env.NEXT_PUBLIC_APP_URL = 'https://canibuildit.com.au';
});

// ---------------------------------------------------------------------------
// granny-flat-analysis routing
// ---------------------------------------------------------------------------

describe('webhook granny-flat-analysis product', () => {
  it('returns 200 received:true for granny-flat-analysis', async () => {
    mockConstructEvent.mockReturnValueOnce(
      buildEvent({
        product: 'granny-flat-analysis',
        job_id: 'job-uuid-123',
        address: '5 Commercial Rd Haberfield NSW 2045',
        email: 'buyer@example.com',
      })
    );
    const res = await POST(makeWebhookReq({}));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.received).toBe(true);
  });

  it('sends link email for granny-flat-analysis', async () => {
    mockConstructEvent.mockReturnValueOnce(
      buildEvent({
        product: 'granny-flat-analysis',
        job_id: 'job-uuid-123',
        address: '5 Commercial Rd Haberfield NSW 2045',
        email: 'buyer@example.com',
      })
    );
    await POST(makeWebhookReq({}));
    expect(mockSendEmail).toHaveBeenCalledTimes(1);
    const call = mockSendEmail.mock.calls[0][0] as { to: string[]; subject: string; html: string };
    expect(call.to).toEqual(['buyer@example.com']);
    expect(call.subject).toMatch(/granny flat/i);
    // Should contain a link, not a PDF attachment
    expect(call).not.toHaveProperty('attachments');
  });

  it('email body contains results URL with jobId and payment=success', async () => {
    mockConstructEvent.mockReturnValueOnce(
      buildEvent({
        product: 'granny-flat-analysis',
        job_id: 'job-uuid-456',
        address: '1 Test St Sydney NSW 2000',
        email: 'test@test.com',
      })
    );
    await POST(makeWebhookReq({}));
    const call = mockSendEmail.mock.calls[0][0] as { html: string };
    expect(call.html).toContain('jobId=job-uuid-456');
    expect(call.html).toContain('payment=success');
  });

  it('does not send email when email metadata is empty', async () => {
    mockConstructEvent.mockReturnValueOnce(
      buildEvent({
        product: 'granny-flat-analysis',
        job_id: 'job-uuid-789',
        address: '1 Test St Sydney NSW 2000',
        email: '',
      })
    );
    await POST(makeWebhookReq({}));
    expect(mockSendEmail).not.toHaveBeenCalled();
  });

  it('returns 200 gracefully when job_id is missing', async () => {
    mockConstructEvent.mockReturnValueOnce(
      buildEvent({
        product: 'granny-flat-analysis',
        address: '1 Test St Sydney NSW 2000',
        email: 'test@test.com',
        // no job_id
      })
    );
    const res = await POST(makeWebhookReq({}));
    expect(res.status).toBe(200);
    expect(mockSendEmail).not.toHaveBeenCalled();
  });

  it('does not call PDF generate endpoint for granny-flat-analysis', async () => {
    const fetchSpy = jest.spyOn(global, 'fetch').mockResolvedValue(
      new Response('{}', { status: 200 })
    );
    mockConstructEvent.mockReturnValueOnce(
      buildEvent({
        product: 'granny-flat-analysis',
        job_id: 'job-uuid-123',
        address: '1 Test St Sydney NSW 2000',
        email: 'test@test.com',
      })
    );
    await POST(makeWebhookReq({}));
    // Should NOT have called /api/reports/granny-flat/generate
    const pdfCalls = fetchSpy.mock.calls.filter(([url]) =>
      String(url).includes('/api/reports/granny-flat/generate')
    );
    expect(pdfCalls).toHaveLength(0);
    fetchSpy.mockRestore();
  });
});
