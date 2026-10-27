/**
 * Lead route — email_sent records whether the confirmation email actually went,
 * and consent records name the right recipient.
 * @jest-environment node
 *
 * Resend reports failure as { error }, not a throw. Before 2026-10-28 the route
 * dropped that, so every lead's email_sent stayed NULL and nobody could tell
 * whether a single confirmation had been delivered.
 */

import { NextRequest } from 'next/server';

jest.mock('dns', () => ({
  promises: { resolveMx: jest.fn().mockResolvedValue([{ exchange: 'mx.example.com', priority: 10 }]) },
}));
jest.mock('@upstash/ratelimit', () => ({ Ratelimit: jest.fn().mockImplementation(() => ({})) }));
jest.mock('@upstash/redis', () => ({ Redis: jest.fn().mockImplementation(() => ({})) }));
jest.mock('@/lib/rate-limit', () => ({
  checkRateLimit: jest.fn().mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 }),
  createRateLimitHeaders: jest.fn().mockReturnValue({}),
  getClientIdentifier: jest.fn().mockReturnValue('127.0.0.1'),
}));

jest.mock('@supabase/supabase-js', () => {
  const insertMock = jest.fn();
  const singleMock = jest.fn().mockResolvedValue({ data: { id: 42 }, error: null });
  const updateMock = jest.fn();
  const updateEqMock = jest.fn().mockResolvedValue({ error: null });
  const from = jest.fn().mockImplementation(() => ({
    // duplicate check: select().eq().eq().gte().limit()
    select: jest.fn().mockReturnValue({
      eq: jest.fn().mockReturnValue({
        eq: jest.fn().mockReturnValue({
          gte: jest.fn().mockReturnValue({ limit: jest.fn().mockResolvedValue({ data: [], error: null }) }),
        }),
      }),
    }),
    insert: insertMock.mockImplementation(() => ({ select: () => ({ single: singleMock }) })),
    update: updateMock.mockImplementation(() => ({ eq: updateEqMock })),
  }));
  return {
    createClient: jest.fn().mockReturnValue({ from }),
    __mocks: { insertMock, singleMock, updateMock, updateEqMock },
  };
});

jest.mock('resend', () => {
  const sendMock = jest.fn();
  return { Resend: jest.fn().mockImplementation(() => ({ emails: { send: sendMock } })), __send: sendMock };
});

jest.mock('next/server', () => jest.requireActual('next/server'));

import { POST } from '@/app/api/canibuildit/lead/route';
import * as supabasePkg from '@supabase/supabase-js';
import * as resendPkg from 'resend';

/* eslint-disable @typescript-eslint/no-explicit-any */
const { insertMock, singleMock, updateMock, updateEqMock } = (supabasePkg as any).__mocks as Record<string, jest.Mock>;
const sendMock = (resendPkg as any).__send as jest.Mock;
/* eslint-enable @typescript-eslint/no-explicit-any */

function req(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/canibuildit/lead', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

const LEAD = { email: 'owner@example.com', address: '12 Test St, Penrith NSW 2750', interest_type: 'flood-truth' };

beforeEach(() => {
  jest.clearAllMocks();
  process.env.RESEND_API_KEY = 'test-key';
  singleMock.mockResolvedValue({ data: { id: 42 }, error: null });
  updateEqMock.mockResolvedValue({ error: null });
});

describe('email_sent', () => {
  it('is true when Resend accepts the email', async () => {
    sendMock.mockResolvedValue({ data: { id: 'em_1' }, error: null });
    await POST(req(LEAD));
    expect(updateMock).toHaveBeenCalledWith({ email_sent: true });
    expect(updateEqMock).toHaveBeenCalledWith('id', 42);
  });

  it('is false when Resend returns an error object (e.g. unverified domain)', async () => {
    sendMock.mockResolvedValue({ data: null, error: { name: 'validation_error', message: 'domain not verified' } });
    await POST(req(LEAD));
    expect(updateMock).toHaveBeenCalledWith({ email_sent: false });
  });

  it('is false when Resend throws', async () => {
    sendMock.mockRejectedValue(new Error('network'));
    await POST(req(LEAD));
    expect(updateMock).toHaveBeenCalledWith({ email_sent: false });
  });

  it('is false when no API key is configured', async () => {
    delete process.env.RESEND_API_KEY;
    await POST(req(LEAD));
    expect(sendMock).not.toHaveBeenCalled();
    expect(updateMock).toHaveBeenCalledWith({ email_sent: false });
  });

  it('returns 500 and sends nothing when the insert failed (a lost lead must not read as success)', async () => {
    singleMock.mockResolvedValue({ data: null, error: { message: 'insert failed' } });
    sendMock.mockResolvedValue({ data: { id: 'em_1' }, error: null });
    const res = await POST(req(LEAD));
    expect(res.status).toBe(500);
    expect(sendMock).not.toHaveBeenCalled();
    expect(updateMock).not.toHaveBeenCalled();
  });
});

describe('response and stored id', () => {
  it('tells the caller when the email did not go', async () => {
    sendMock.mockResolvedValue({ data: null, error: { message: 'domain not verified' } });
    const res = await POST(req(LEAD));
    expect(await res.json()).toMatchObject({ ok: true, email_sent: false });
  });

  it('treats an insert that returns no id as a failed save', async () => {
    singleMock.mockResolvedValue({ data: null, error: null });
    const res = await POST(req(LEAD));
    expect(res.status).toBe(500);
    expect(sendMock).not.toHaveBeenCalled();
  });
});

describe('consent.shared_with', () => {
  const consent = { consent_version: 'v', consent_wording: 'wording' };
  const sharedWith = () => insertMock.mock.calls[0][0].consent.shared_with;

  beforeEach(() => sendMock.mockResolvedValue({ data: { id: 'em_1' }, error: null }));

  it('names the granny-flat partner for a granny-flat referral', async () => {
    await POST(req({ ...LEAD, interest_type: 'granny-flat-referral', ...consent }));
    expect(sharedWith()).toBe('granny-flat-referral-partner');
  });

  it('names the duplex partner for a duplex referral', async () => {
    await POST(req({ ...LEAD, interest_type: 'dual-occ-referral', ...consent }));
    expect(sharedWith()).toBe('duplex-referral-partner');
  });

  it('names nobody for a lead that only asked for its own result', async () => {
    // Before: every consent record said 'duplex-referral-partner', whatever was asked.
    await POST(req({ ...LEAD, ...consent }));
    expect(sharedWith()).toBeNull();
  });
});
