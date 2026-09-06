/**
 * Lead route — verdict recomputation (Sol HIGH 0.99, PR #1015)
 * @jest-environment node
 *
 * The client's `eligible` claim must never reach the confirmation email or the
 * DB row untouched for 'duplex-result' / 'dual-occ-referral' — both are
 * treated as a stated fact downstream (the email text, and the internal
 * leads dashboard's "Eligible"/"Not eligible" column). These tests prove the
 * SERVER-recomputed value is what actually gets used, in both directions
 * (a false claim of true, and a false claim of false), and that every
 * recompute failure mode fails closed to the neutral state rather than
 * defaulting true or silently trusting the client.
 */

// Mock dns — MX check always passes so it never blocks these tests.
jest.mock('dns', () => ({
  promises: { resolveMx: jest.fn().mockResolvedValue([{ exchange: 'mail.example.com', priority: 10 }]) },
}));

jest.mock('@upstash/ratelimit', () => ({
  Ratelimit: jest.fn().mockImplementation(() => ({
    limit: jest.fn().mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 }),
  })),
}));
jest.mock('@upstash/redis', () => ({ Redis: jest.fn().mockImplementation(() => ({})) }));
jest.mock('@/lib/rate-limit', () => ({
  checkRateLimit: jest.fn().mockResolvedValue({ success: true, limit: 3, remaining: 2, reset: Date.now() + 600000 }),
  createRateLimitHeaders: jest.fn().mockReturnValue({}),
  getClientIdentifier: jest.fn().mockReturnValue('127.0.0.1'),
}));

jest.mock('@supabase/supabase-js', () => {
  const insertMock = jest.fn().mockResolvedValue({ error: null });
  const limitMock = jest.fn().mockResolvedValue({ data: [], error: null }); // no duplicate, ever
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
jest.mock('@/lib/supabase/server', () => ({ createClient: jest.fn().mockResolvedValue({ from: jest.fn() }) }));

jest.mock('resend', () => {
  const sendMock = jest.fn().mockResolvedValue({ id: 'mock-id' });
  return { Resend: jest.fn().mockImplementation(() => ({ emails: { send: sendMock } })), __send: sendMock };
});

jest.mock('next/server', () => jest.requireActual('next/server'));

import { NextRequest } from 'next/server';
import { POST, recomputeDualOccEligible } from '@/app/api/canibuildit/lead/route';
import * as supabasePkg from '@supabase/supabase-js';
import * as resendPkg from 'resend';
import type { UpzoningResult, FormResult } from '@/lib/upzoning';

/* eslint-disable @typescript-eslint/no-explicit-any */
const { insertMock } = (supabasePkg as any).__mocks as { insertMock: jest.Mock };
const emailSendMock = (resendPkg as any).__send as jest.Mock;
/* eslint-enable @typescript-eslint/no-explicit-any */

function makeRequest(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/canibuildit/lead', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function makeForm(overrides: Partial<FormResult> = {}): FormResult {
  return {
    development_type: 'dual_occupancy',
    eligible: true,
    reason: '',
    unconfirmed: false,
    requires_lmr_area: true,
    min_lot_size_m2: 450,
    min_lot_width_m: 15,
    source_clause: 'cl 6.1',
    legislation_url: null,
    effective_date: null,
    ...overrides,
  };
}

function makeUpzoningResult(overrides: Partial<UpzoningResult> = {}): UpzoningResult {
  return {
    address: '12 Test St, Marrickville NSW 2204',
    zone: 'R2',
    zone_full: 'R2 Low Density Residential',
    zone_epi: null,
    legislation_url: null,
    lot_area_m2: 600,
    lot_width_m: 18,
    lot_type: 'rectangular',
    lga_name: 'Inner West',
    heritage: { flag: false, items: [], hca: [] },
    gates: { in_lmr_area: true, in_tod: false, dual_occ_prohibited: false },
    status: 'ok',
    forms: [makeForm()],
    ...overrides,
  };
}

beforeAll(() => {
  process.env.RESEND_API_KEY = 'test-key';
  process.env.PYTHON_API_URL = 'http://fake-python-api.internal';
});

let fetchMock: jest.Mock;
let abortTimeoutSpy: jest.SpyInstance;
beforeEach(() => {
  jest.clearAllMocks();
  insertMock.mockResolvedValue({ error: null });
  emailSendMock.mockResolvedValue({ id: 'mock-id' });
  fetchMock = jest.fn();
  global.fetch = fetchMock as unknown as typeof fetch;
  // Every mocked fetch below settles synchronously (resolve or reject), so the
  // real 20s abort timer in recomputeDualOccEligible never has anything to
  // abort — it just sits pending until Node's event loop ticks it off, which
  // is what was leaking as "worker did not exit gracefully" before this spy.
  // A fresh AbortController's signal is never aborted, which is exactly the
  // "nothing timed out" case every test here actually exercises.
  abortTimeoutSpy = jest.spyOn(AbortSignal, 'timeout').mockReturnValue(new AbortController().signal);
});

afterEach(() => {
  abortTimeoutSpy.mockRestore();
});

function mockPipelineResponse(result: UpzoningResult) {
  fetchMock.mockResolvedValue({ ok: true, json: async () => result } as Response);
}

// ============================================================================
// recomputeDualOccEligible — the pure(ish) recompute helper, tri-state
// ============================================================================

describe('recomputeDualOccEligible', () => {
  it('returns true when the pipeline reports an eligible dual_occupancy form', async () => {
    mockPipelineResponse(makeUpzoningResult());
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBe(true);
  });

  it('returns false when the pipeline runs but no dual_occupancy form is eligible', async () => {
    mockPipelineResponse(makeUpzoningResult({ forms: [makeForm({ eligible: false })] }));
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBe(false);
  });

  it('returns null (not false) when status is not_residential — indeterminate, not a no', async () => {
    mockPipelineResponse(makeUpzoningResult({ status: 'not_residential', forms: [] }));
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBeNull();
  });

  it('returns null when status is unavailable', async () => {
    mockPipelineResponse(makeUpzoningResult({ status: 'unavailable', forms: [] }));
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBeNull();
  });

  it('returns null on a non-2xx response', async () => {
    fetchMock.mockResolvedValue({ ok: false, json: async () => ({}) } as Response);
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBeNull();
  });

  it('returns null when the fetch itself throws (network error / timeout)', async () => {
    fetchMock.mockRejectedValue(new Error('fetch failed'));
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBeNull();
  });

  it('returns null when the response body is not valid JSON', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: async () => { throw new Error('bad json'); } } as unknown as Response);
    await expect(recomputeDualOccEligible('12 Test St')).resolves.toBeNull();
  });

  it('never defaults to true on any failure path', async () => {
    // Sweep every failure shape above through one assertion style, so a future
    // edit that changes ANY of them to `true` is caught here too, not just in
    // the individual cases.
    const failureModes: Array<() => void> = [
      () => fetchMock.mockResolvedValueOnce({ ok: false, json: async () => ({}) } as Response),
      () => fetchMock.mockRejectedValueOnce(new Error('network')),
      () => fetchMock.mockResolvedValueOnce({ ok: true, json: async () => { throw new Error('bad'); } } as unknown as Response),
      () => fetchMock.mockResolvedValueOnce({ ok: true, json: async () => makeUpzoningResult({ status: 'unavailable' }) } as Response),
    ];
    for (const arrange of failureModes) {
      arrange();
      expect(await recomputeDualOccEligible('12 Test St')).not.toBe(true);
    }
  });
});

// ============================================================================
// POST handler — the client's `eligible` must never survive to the email or
// the DB row for the two verdict-bearing interest_types
// ============================================================================

describe('POST /api/canibuildit/lead — duplex-result ignores the client eligible claim', () => {
  it('client claims eligible=true, server recomputes false: email states the negative, not the claim', async () => {
    mockPipelineResponse(makeUpzoningResult({ forms: [makeForm({ eligible: false })] }));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true, // the spoofed claim
      interest_type: 'duplex-result',
    }));
    expect(emailSendMock).toHaveBeenCalledTimes(1);
    const html = emailSendMock.mock.calls[0][0].html;
    expect(html).toMatch(/does not meet/i);
    expect(html).not.toMatch(/can apply to build/i);
  });

  it('client claims eligible=false, server recomputes true: email states the positive, not the claim', async () => {
    mockPipelineResponse(makeUpzoningResult({ forms: [makeForm({ eligible: true })] }));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: false, // the spoofed claim, other direction
      interest_type: 'duplex-result',
    }));
    const html = emailSendMock.mock.calls[0][0].html;
    expect(html).toMatch(/can apply to build a duplex/i);
    expect(html).not.toMatch(/does not meet/i);
  });

  it('recompute failure resolves to the neutral email, never the client claim', async () => {
    fetchMock.mockRejectedValue(new Error('pipeline down'));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'duplex-result',
    }));
    const html = emailSendMock.mock.calls[0][0].html;
    expect(html).not.toMatch(/can apply to build/i);
    expect(html).not.toMatch(/does not meet/i);
    expect(html).toMatch(/duplex check has been run/i);
  });

  it('missing address never attempts a recompute call and stays neutral', async () => {
    await POST(makeRequest({
      email: 'buyer@example.com',
      eligible: true,
      interest_type: 'duplex-result',
    }));
    expect(fetchMock).not.toHaveBeenCalled();
    const html = emailSendMock.mock.calls[0][0].html;
    expect(html).toMatch(/duplex check has been run/i);
  });
});

describe('POST /api/canibuildit/lead — dual-occ-referral: the STORED value, not just the email', () => {
  it('client claims eligible=true, server recomputes false: the DB row stores false, not true', async () => {
    mockPipelineResponse(makeUpzoningResult({ forms: [makeForm({ eligible: false })] }));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'dual-occ-referral',
    }));
    expect(insertMock).toHaveBeenCalledTimes(1);
    expect(insertMock.mock.calls[0][0].eligible).toBe(false);
  });

  it('recompute failure stores null, never the client claim', async () => {
    fetchMock.mockRejectedValue(new Error('pipeline down'));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'dual-occ-referral',
    }));
    expect(insertMock.mock.calls[0][0].eligible).toBeNull();
  });
});

describe('POST /api/canibuildit/lead — recompute is scoped to verdict-bearing interest_types only', () => {
  it('does not call the pipeline for granny-flat even when eligible is sent', async () => {
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'granny-flat',
    }));
    expect(fetchMock).not.toHaveBeenCalled();
    // Unaffected path: stores null now (was previously whatever the client sent) —
    // granny-flat never populated a meaningful eligible value before this fix either
    // (grep of every caller confirms none send eligible for this interest_type), so
    // this is not a behaviour change for any real caller.
    expect(insertMock.mock.calls[0][0].eligible).toBeNull();
  });

  it('honeypot short-circuits before any recompute call', async () => {
    await POST(makeRequest({
      email: 'bot@spam.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'duplex-result',
      website: 'http://spam.example.com',
    }));
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('POST /api/canibuildit/lead — mismatch visibility', () => {
  it('logs a warning when the client claim disagrees with the recomputed verdict', async () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockPipelineResponse(makeUpzoningResult({ forms: [makeForm({ eligible: false })] }));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'duplex-result',
    }));
    expect(warnSpy).toHaveBeenCalledWith(
      expect.stringContaining('did not match recomputed verdict'),
      expect.objectContaining({ client_claimed: true, verified: false }),
    );
    warnSpy.mockRestore();
  });

  it('does not log when the client claim matches the recomputed verdict', async () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockPipelineResponse(makeUpzoningResult({ forms: [makeForm({ eligible: true })] }));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'duplex-result',
    }));
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it('does not log when recompute is indeterminate (nothing confirmed to disagree with)', async () => {
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    fetchMock.mockRejectedValue(new Error('pipeline down'));
    await POST(makeRequest({
      email: 'buyer@example.com',
      address: '12 Test St, Marrickville NSW 2204',
      eligible: true,
      interest_type: 'duplex-result',
    }));
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });
});
