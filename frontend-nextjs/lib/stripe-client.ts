import Stripe from 'stripe';

// prior-art-checked: this REPLACES the module-scope `const stripe = new
// Stripe(process.env.STRIPE_SECRET_KEY!)` duplicated across bushfire,
// conveyancing, flood-truth, granny-flat, pre-da-history, shadow, solar-yield,
// threat-radar-monitor and the webhook route — nine copies of the same broken
// pattern, not nine independent implementations. Consolidating them here is
// the fix, not new capability: same as resend-client.ts for the Resend client.

/**
 * Lazily construct the Stripe client.
 *
 * `new Stripe(undefined)` THROWS — "Neither apiKey nor config.authenticator
 * provided". Nine routes built it at module scope, so merely IMPORTING any of
 * them threw wherever STRIPE_SECRET_KEY was absent. Next imports every route
 * to collect page data during `next build`, so the whole production build
 * failed on any machine without the key — the same defect class as the Resend
 * one fixed earlier (frontend-nextjs/lib/resend-client.ts), caught by CI's new
 * build gate for the same reason: CI has never had this key.
 *
 * Unlike Resend (a secondary notification a request can succeed without),
 * Stripe IS the purpose of these routes — a checkout session cannot exist
 * without it. So this returns null rather than throwing (to protect the
 * build), but callers MUST treat null as a real failure and return an
 * explicit error response, never silently proceed. Every checkout route
 * already has this exact shape for a missing price ID:
 *
 *   if (!priceId) {
 *     console.error('[route] ... not set');
 *     return NextResponse.json({ error: 'Payment not configured' }, { status: 500 });
 *   }
 *
 * getStripe() is meant to be checked the same way, immediately after.
 */
export function getStripe(): Stripe | null {
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) {
    console.error('[stripe-client] STRIPE_SECRET_KEY is not set — Stripe unavailable.');
    return null;
  }
  return new Stripe(key);
}
