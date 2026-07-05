/**
 * POST /api/reports/conveyancing/access
 * prior-art-checked: reuse not viable because no entitlement/access-code route
 * exists — generate/route.ts is the unauthenticated PDF proxy, satellite route
 * is the free check, stripe checkout is payment-only; this is the named-grant
 * validator they all lack.
 *
 * Validates a named early-access grant code (arrives via an ?access= link)
 * against the CONVEYANCING_ACCESS_CODES env var. Returns { valid: boolean }
 * only — never the code list.
 *
 * A valid grant unlocks the full-PDF download CTA on /reports/conveyancing
 * without Stripe checkout. Billing does not exist yet; comps are named codes
 * handed out privately, one per grantee, revocable by removing the code.
 */

import { NextRequest, NextResponse } from 'next/server';
import { isValidAccessCode } from '@/lib/access-codes';

export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  let body: { code?: unknown };

  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const code = typeof body.code === 'string' ? body.code.trim() : '';
  if (!code || code.length > 100) {
    return NextResponse.json({ error: 'code is required' }, { status: 400 });
  }

  const valid = isValidAccessCode(code, process.env.CONVEYANCING_ACCESS_CODES);
  if (valid) {
    // The Vercel log line is the usage trail per named grantee until billing exists.
    console.log('[conveyancing/access] grant code used:', code);
  }

  return NextResponse.json({ valid });
}
