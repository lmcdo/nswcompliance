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
 * Returns null rather than throwing. Callers already treat a missing key as
 * "do not send", which is correct: a notification is never worth failing the
 * request that triggered it.
 */
export function getResend(): Resend | null {
  const key = process.env.RESEND_API_KEY;
  if (!key) return null;
  return new Resend(key);
}
