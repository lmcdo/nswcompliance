import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

// Shadow tool turned off 2026-10-22 by the owner: it sold an "ADG solar access" verdict
// for neighbouring houses, but ADG 4A-1 (2 hours of sun) applies to a new apartment
// building's own apartments and 3F is visual privacy, so the verdict was not a real standard.
// New work is refused. Already-paid orders are still fulfilled by
// /api/reports/shadow/generate and the 'shadow' branch of /api/stripe/webhook.
function off() {
  return NextResponse.json({ error: 'The shadow tool has been turned off.' }, { status: 410 });
}

export const GET = off;
export const POST = off;
export const PUT = off;
export const PATCH = off;
export const DELETE = off;
export const OPTIONS = off;
export const HEAD = off;
