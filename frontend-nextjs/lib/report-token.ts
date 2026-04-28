// HMAC-based report tokens for satellite PDF generate routes.
//
// When a satellite analysis completes (/api/satellite/X), the route signs
// { lat, lng, address, run_date } with a server-side secret and returns the
// token. Each /api/reports/X/generate route verifies the token before rendering,
// preventing PDF generation from arbitrary injected data.
//
// Token format: <hex-sig>.<expires-ms>   Expiry: 2 hours.

import crypto from 'crypto';

const SECRET = process.env.REPORT_TOKEN_SECRET;

function getSecret(): string {
  if (!SECRET) {
    // In development without the env var, use a fixed dev key so things work locally.
    // In production this will throw if the var is missing.
    if (process.env.NODE_ENV === 'production') {
      throw new Error('REPORT_TOKEN_SECRET env var is required in production');
    }
    return 'dev-report-token-secret-not-for-production';
  }
  return SECRET;
}

function buildPayload(lat: number, lng: number, address: string, runDate: string): string {
  // Round coords to 6dp to absorb float serialisation differences.
  return `${lat.toFixed(6)}:${lng.toFixed(6)}:${address.trim().toLowerCase()}:${runDate}`;
}

/** Sign a report fingerprint. Called in satellite routes before returning to frontend. */
export function signReport(lat: number, lng: number, address: string, runDate: string): string {
  const expires = Date.now() + 2 * 3600_000; // 2 hours
  const payload = buildPayload(lat, lng, address, runDate);
  const sig = crypto.createHmac('sha256', getSecret()).update(payload).digest('hex');
  return `${sig}.${expires}`;
}

/** Verify a report token. Called in generate routes before rendering. Returns false on any failure. */
export function verifyReport(
  lat: number,
  lng: number,
  address: string,
  runDate: string,
  token: string | null | undefined,
): boolean {
  if (!token) return false;
  try {
    const dotIdx = token.lastIndexOf('.');
    if (dotIdx < 0) return false;
    const sig = token.slice(0, dotIdx);
    const expires = Number(token.slice(dotIdx + 1));
    if (!Number.isFinite(expires) || Date.now() > expires) return false;
    const payload = buildPayload(lat, lng, address, runDate);
    const expected = crypto.createHmac('sha256', getSecret()).update(payload).digest('hex');
    // Constant-time comparison
    const sigBuf = Buffer.from(sig.padEnd(64, '0'), 'hex');
    const expBuf = Buffer.from(expected, 'hex');
    return sigBuf.length === expBuf.length && crypto.timingSafeEqual(sigBuf, expBuf);
  } catch {
    return false;
  }
}
