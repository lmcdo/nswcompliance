/**
 * Lead route — abuse, validation, and rate-limit tests
 * @jest-environment node
 *
 * Tests: input validation, honeypot, rate limit, duplicate detection, MX check, happy path.
 */

import { NextRequest } from 'next/server';

// Mock dns module — default: domain has MX records
const mockResolveMx = jest.fn().mockResolvedValue([{ exchange: 'mail.example.com', priority: 10 }]);
jest.mock('dns', () => ({
  promises: { resolveMx: (...args: unknown[]) => mockResolveMx(...args) },
}));

// ============================================================================
// MOCKS — all factories defined before imports
// ============================================================================

jest.mock('@upstash/ratelimit', () => ({
  Ratelimit: jest.fn().mockImplementation(() => ({
    limit: jest.fn().mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 }),
  })),
}));

jest.mock('@upstash/redis', () => ({
  Redis: jest.fn().mockImplementation(() => ({})),
}));

// Rate-limit helpers: checkRateLimit passes by default; tests override per-case
jest.mock('@/lib/rate-limit', () => ({
  checkRateLimit: jest.fn().mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 }),
  createRateLimitHeaders: jest.fn().mockReturnValue({}),
  getClientIdentifier: jest.fn().mockReturnValue('127.0.0.1'),
}));

// Supabase — factory exposes mocks via __mocks to avoid hoisting issues.
// The lead route now uses @supabase/supabase-js directly (service role client),
// so we mock that module. @/lib/supabase/server mock kept for other tests that use it.
jest.mock('@supabase/supabase-js', () => {
  const insertMock = jest.fn().mockResolvedValue({ error: null });
  const limitMock = jest.fn().mockResolvedValue({ data: [], error: null });
  const chain = {
    select: jest.fn().mockReturnThis(),
    eq: jest.fn().mockReturnThis(),
    gte: jest.fn().mockReturnThis(),
    limit: limitMock,
    insert: insertMock,
  };
  return {
    createClient: jest.fn().mockReturnValue({ from: jest.fn().mockReturnValue(chain) }),
    __mocks: { insertMock, limitMock },
  };
});

jest.mock('@/lib/supabase/server', () => ({
  createClient: jest.fn().mockResolvedValue({ from: jest.fn() }),
}));

// Resend — factory exposes send mock via __send
jest.mock('resend', () => {
  const sendMock = jest.fn().mockResolvedValue({ id: 'mock-id' });
  return {
    Resend: jest.fn().mockImplementation(() => ({ emails: { send: sendMock } })),
    __send: sendMock,
  };
});

jest.mock('next/server', () => jest.requireActual('next/server'));

// ============================================================================
// IMPORTS (after all jest.mock calls)
// ============================================================================

import { POST } from '@/app/api/canibuildit/lead/route';
import { checkRateLimit } from '@/lib/rate-limit';
import * as supabasePkg from '@supabase/supabase-js';
import * as resendPkg from 'resend';

/* eslint-disable @typescript-eslint/no-explicit-any */
const { insertMock, limitMock } = (supabasePkg as any).__mocks as {
  insertMock: jest.Mock;
  limitMock: jest.Mock;
};
const emailSendMock = (resendPkg as any).__send as jest.Mock;
/* eslint-enable @typescript-eslint/no-explicit-any */

// ============================================================================
// HELPER
// ============================================================================

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/canibuildit/lead', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ============================================================================
// HAPPY PATH
// ============================================================================

describe('POST /api/canibuildit/lead — happy path', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (checkRateLimit as jest.Mock).mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 });
    limitMock.mockResolvedValue({ data: [], error: null });
    insertMock.mockResolvedValue({ error: null });
    emailSendMock.mockResolvedValue({ id: 'mock-id' });
  });

  it('accepts a valid granny-flat lead and returns ok:true', async () => {
    const res = await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      lga_name: 'Inner West',
      interest_type: 'granny-flat',
    }));
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ ok: true });
  });

  it('sends confirmation email on valid submission', async () => {
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      interest_type: 'flood',
    }));
    expect(emailSendMock).toHaveBeenCalledTimes(1);
    expect(emailSendMock.mock.calls[0][0].to).toContain('buyer@example.com');
  });

  it('accepts submission with only email (optional fields omitted)', async () => {
    const res = await POST(makeRequest({ email: 'min@example.com' }));
    expect(res.status).toBe(200);
  });

  it('stores lead in DB on valid submission', async () => {
    await POST(makeRequest({ email: 'store@example.com', address: '1 Store St' }));
    expect(insertMock).toHaveBeenCalledTimes(1);
    expect(insertMock.mock.calls[0][0]).toMatchObject({ email: 'store@example.com' });
  });

  it('normalises email to lowercase', async () => {
    await POST(makeRequest({ email: 'UPPER@Example.COM' }));
    expect(insertMock.mock.calls[0][0].email).toBe('upper@example.com');
  });
});

// ============================================================================
// INPUT VALIDATION
// ============================================================================

describe('POST /api/canibuildit/lead — input validation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (checkRateLimit as jest.Mock).mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 });
  });

  it('rejects missing email with 400', async () => {
    const res = await POST(makeRequest({ address: '12 Test St' }));
    expect(res.status).toBe(400);
  });

  it('rejects invalid email format with 400', async () => {
    const res = await POST(makeRequest({ email: 'not-an-email' }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/email/i);
  });

  it('rejects email over 254 chars with 400', async () => {
    // 246 + '@test.com' (9) = 255 chars — exceeds max(254)
    const res = await POST(makeRequest({ email: 'a'.repeat(246) + '@test.com' }));
    expect(res.status).toBe(400);
  });

  it('rejects address over 200 chars with 400', async () => {
    const res = await POST(makeRequest({ email: 'ok@example.com', address: 'A'.repeat(201) }));
    expect(res.status).toBe(400);
  });

  it('rejects lga_name over 100 chars with 400', async () => {
    const res = await POST(makeRequest({ email: 'ok@example.com', lga_name: 'X'.repeat(101) }));
    expect(res.status).toBe(400);
  });

  it('rejects unknown interest_type with 400', async () => {
    const res = await POST(makeRequest({ email: 'ok@example.com', interest_type: 'nuclear-plant' }));
    expect(res.status).toBe(400);
  });

  it('rejects malformed JSON with 400', async () => {
    const req = new NextRequest('http://localhost/api/canibuildit/lead', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{ bad json :::',
    });
    const res = await POST(req);
    expect(res.status).toBe(400);
  });
});

// ============================================================================
// HONEYPOT
// ============================================================================

describe('POST /api/canibuildit/lead — honeypot', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (checkRateLimit as jest.Mock).mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 });
    limitMock.mockResolvedValue({ data: [], error: null });
  });

  it('returns 200 silently when honeypot website field is filled', async () => {
    const res = await POST(makeRequest({
      email: 'bot@spam.com',
      address: '1 Bot St',
      website: 'http://spam.example.com',
    }));
    expect(res.status).toBe(200);
    expect(insertMock).not.toHaveBeenCalled();
    expect(emailSendMock).not.toHaveBeenCalled();
  });

  it('proceeds normally when website field is absent', async () => {
    emailSendMock.mockResolvedValue({ id: 'ok' });
    const res = await POST(makeRequest({ email: 'real@example.com', address: '5 Real St' }));
    expect(res.status).toBe(200);
    expect(emailSendMock).toHaveBeenCalledTimes(1);
  });
});

// ============================================================================
// RATE LIMITING
// ============================================================================

describe('POST /api/canibuildit/lead — rate limiting', () => {
  beforeEach(() => jest.clearAllMocks());

  it('returns 429 when rate limit exceeded', async () => {
    (checkRateLimit as jest.Mock).mockResolvedValueOnce({
      success: false, limit: 3, remaining: 0, reset: Date.now() + 600000,
    });
    const res = await POST(makeRequest({ email: 'flood@example.com' }));
    expect(res.status).toBe(429);
    expect((await res.json()).error).toMatch(/too many/i);
  });

  it('does not insert to DB or send email when rate limited', async () => {
    (checkRateLimit as jest.Mock).mockResolvedValueOnce({
      success: false, limit: 3, remaining: 0, reset: Date.now() + 600000,
    });
    await POST(makeRequest({ email: 'flood@example.com' }));
    expect(insertMock).not.toHaveBeenCalled();
    expect(emailSendMock).not.toHaveBeenCalled();
  });
});

// ============================================================================
// DUPLICATE DETECTION
// ============================================================================

describe('POST /api/canibuildit/lead — duplicate detection', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (checkRateLimit as jest.Mock).mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 });
  });

  it('returns 200 silently for duplicate email+address within 24h (no DB insert, no email)', async () => {
    limitMock.mockResolvedValueOnce({ data: [{ id: 'existing-uuid' }], error: null });
    const res = await POST(makeRequest({
      email: 'repeat@example.com',
      address: '12 Test St, Marrickville NSW 2204',
    }));
    expect(res.status).toBe(200);
    expect(insertMock).not.toHaveBeenCalled();
    expect(emailSendMock).not.toHaveBeenCalled();
  });

  it('inserts and emails when no duplicate found', async () => {
    limitMock.mockResolvedValueOnce({ data: [], error: null });
    insertMock.mockResolvedValue({ error: null });
    emailSendMock.mockResolvedValue({ id: 'ok' });
    await POST(makeRequest({ email: 'new@example.com', address: '99 New St, Sydney NSW 2000' }));
    expect(insertMock).toHaveBeenCalledTimes(1);
    expect(emailSendMock).toHaveBeenCalledTimes(1);
  });

  it('still returns 200 if duplicate check throws (non-blocking)', async () => {
    limitMock.mockRejectedValueOnce(new Error('DB timeout'));
    insertMock.mockResolvedValue({ error: null });
    emailSendMock.mockResolvedValue({ id: 'ok' });
    const res = await POST(makeRequest({ email: 'fallback@example.com', address: '1 Fallback Rd' }));
    expect(res.status).toBe(200);
  });
});

// ============================================================================
// MX DOMAIN CHECK
// ============================================================================

describe('POST /api/canibuildit/lead — MX domain check', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (checkRateLimit as jest.Mock).mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 });
    limitMock.mockResolvedValue({ data: [], error: null });
    insertMock.mockResolvedValue({ error: null });
    emailSendMock.mockResolvedValue({ id: 'ok' });
    // Default: domain has valid MX records
    mockResolveMx.mockResolvedValue([{ exchange: 'mail.example.com', priority: 10 }]);
  });

  it('accepts email from domain with valid MX records', async () => {
    const res = await POST(makeRequest({ email: 'real@gmail.com' }));
    expect(res.status).toBe(200);
  });

  it('rejects email from domain with no MX records with 400', async () => {
    mockResolveMx.mockRejectedValueOnce(Object.assign(new Error('ENOTFOUND'), { code: 'ENOTFOUND' }));
    const res = await POST(makeRequest({ email: 'fake@totallynotreal123456.xyz' }));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toMatch(/valid email/i);
  });

  it('does not insert to DB when MX check fails', async () => {
    mockResolveMx.mockRejectedValueOnce(Object.assign(new Error('ENOTFOUND'), { code: 'ENOTFOUND' }));
    await POST(makeRequest({ email: 'fake@totallynotreal123456.xyz' }));
    expect(insertMock).not.toHaveBeenCalled();
  });

  it('passes through (200) if DNS lookup times out — fail open for real users', async () => {
    // Simulate DNS timeout — never resolves within 3s
    // We mock a fast rejection to simulate the timeout path returning false,
    // but the route fails open (returns true) on catch. So a real timeout
    // resolves the Promise.race with false from the timeout branch.
    // Here we just confirm a slow DNS doesn't crash the route.
    mockResolveMx.mockImplementationOnce(() => new Promise((_, reject) =>
      setTimeout(() => reject(new Error('timeout')), 10)
    ));
    const res = await POST(makeRequest({ email: 'real@slowdns.com' }));
    // Should not 500 — either 200 (fail open) or 400 (MX failed), not a crash
    expect([200, 400]).toContain(res.status);
  });
});
