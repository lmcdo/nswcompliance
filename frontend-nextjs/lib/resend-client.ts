import { Resend } from 'resend';

/**
 * Lazily construct the Resend client.
 *
 * `new Resend(undefined)` THROWS — "Missing API key. Pass it to the constructor".
 * Three routes built it at module scope, so merely IMPORTING them threw wherever
 * RESEND_API_KEY was absent. Next imports every route to collect page data
 * during `next build`, so the whole production build failed on any machine
 * without the key.
 *
 * That went unnoticed because every environment that ran a build had the key:
 * local `.env` and Vercel. CI had neither the key nor, until 2026-08-26, a build
 * step — so nothing ever exercised the combination.
 *
 * Returns null rather than throwing: callers treat a missing key as "do not
 * send", because a notification is never worth failing the request that
 * triggered it (established in notifyOperator, #1007/#1008 — the underlying
 * action, e.g. a DB insert, already succeeded and is unrelated to email).
 *
 * Sol cross-review [HIGH] flagged the missing key going completely unlogged:
 * these three callers are CUSTOMER-facing (lead capture, granny-flat result,
 * solar interest) rather than an internal alert, so a silently absent key in
 * production could mean nobody gets their email indefinitely with zero signal
 * anywhere. notifyOperator's sibling convention doesn't log on a missing key
 * (only on a throw/reject) — this deliberately diverges from that by logging
 * here too, while still returning null rather than throwing, so a
 * misconfigured key degrades to "no email, request still succeeds" and is
 * visible in server logs, never a 500 for something the caller didn't cause.
 */
export function getResend(): Resend | null {
  const key = process.env.RESEND_API_KEY;
  if (!key) {
    console.error('[resend-client] RESEND_API_KEY is not set — email skipped, request continues.');
    return null;
  }
  return new Resend(key);
}
