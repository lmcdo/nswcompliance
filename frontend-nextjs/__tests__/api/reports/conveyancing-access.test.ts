/**
 * POST /api/reports/conveyancing/access + lib/access-codes
 * @jest-environment node
 *
 * Tests: validator edge cases (empty env, whitespace, partial match, revoked),
 * route input validation, valid/invalid grant codes, env var unset.
 */

import { NextRequest } from 'next/server';

import { isValidAccessCode } from '@/lib/access-codes';
import { POST } from '@/app/api/reports/conveyancing/access/route';

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/reports/conveyancing/access', {
    method: 'POST',
    body: typeof body === 'string' ? body : JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('isValidAccessCode', () => {
  it('accepts a code present in the list', () => {
    expect(isValidAccessCode('grantee-a-01', 'grantee-a-01,internal-test-01')).toBe(true);
  });

  it('accepts a code with surrounding whitespace in code and env list', () => {
    expect(isValidAccessCode('  internal-test-01 ', 'grantee-a-01, internal-test-01 ')).toBe(true);
  });

  it('rejects a code not in the list (revoked)', () => {
    expect(isValidAccessCode('grantee-a-01', 'internal-test-01')).toBe(false);
  });

  it('rejects a partial/prefix match', () => {
    expect(isValidAccessCode('grantee', 'grantee-a-01')).toBe(false);
    expect(isValidAccessCode('grantee-a-01-extra', 'grantee-a-01')).toBe(false);
  });

  it('rejects when env list is empty, undefined, or only separators', () => {
    expect(isValidAccessCode('x', '')).toBe(false);
    expect(isValidAccessCode('x', undefined)).toBe(false);
    expect(isValidAccessCode('x', ' , , ')).toBe(false);
  });

  it('rejects empty or whitespace-only codes even against a non-empty list', () => {
    expect(isValidAccessCode('', 'a,b')).toBe(false);
    expect(isValidAccessCode('   ', 'a,b')).toBe(false);
    expect(isValidAccessCode(null, 'a,b')).toBe(false);
    expect(isValidAccessCode(undefined, 'a,b')).toBe(false);
  });

  it('never matches the empty string produced by trailing commas', () => {
    expect(isValidAccessCode(' ', 'a,,b,')).toBe(false);
  });
});

describe('POST /api/reports/conveyancing/access', () => {
  const ENV_KEY = 'CONVEYANCING_ACCESS_CODES';
  const originalEnv = process.env[ENV_KEY];

  afterEach(() => {
    if (originalEnv === undefined) {
      delete process.env[ENV_KEY];
    } else {
      process.env[ENV_KEY] = originalEnv;
    }
  });

  it('returns 400 on invalid JSON', async () => {
    const res = await POST(makeReq('not-json{'));
    expect(res.status).toBe(400);
  });

  it('returns 400 when code is missing or not a string', async () => {
    expect((await POST(makeReq({}))).status).toBe(400);
    expect((await POST(makeReq({ code: 42 }))).status).toBe(400);
    expect((await POST(makeReq({ code: '   ' }))).status).toBe(400);
  });

  it('returns 400 when code exceeds 100 characters', async () => {
    const res = await POST(makeReq({ code: 'x'.repeat(101) }));
    expect(res.status).toBe(400);
  });

  it('returns valid=true for a configured code', async () => {
    process.env[ENV_KEY] = 'grantee-a-01,internal-test-01';
    const res = await POST(makeReq({ code: 'internal-test-01' }));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ valid: true });
  });

  it('returns valid=false for an unknown code', async () => {
    process.env[ENV_KEY] = 'grantee-a-01';
    const res = await POST(makeReq({ code: 'guess-01' }));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ valid: false });
  });

  it('returns valid=false when the env var is unset (fails closed)', async () => {
    delete process.env[ENV_KEY];
    const res = await POST(makeReq({ code: 'grantee-a-01' }));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ valid: false });
  });

  it('never echoes the configured code list in the response body', async () => {
    process.env[ENV_KEY] = 'secret-code-a,secret-code-b';
    const res = await POST(makeReq({ code: 'nope' }));
    const text = JSON.stringify(await res.json());
    expect(text).not.toContain('secret-code-a');
    expect(text).not.toContain('secret-code-b');
  });
});
