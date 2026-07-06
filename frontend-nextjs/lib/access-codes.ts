/**
 * Named early-access grant codes for payment-gated report products.
 * prior-art-checked: no existing access-code/entitlement infrastructure —
 * lib/report-token.ts is an HMAC anti-injection guard (not entitlement) and
 * Stripe promo codes only apply once checkout is live.
 *
 * Free access is a private, named grant (founding member / design partner /
 * internal testing), never a public free tier. One code per grantee so a
 * grant can be revoked by removing its code from the env var.
 *
 * Codes live in a comma-separated env var, e.g.
 * CONVEYANCING_ACCESS_CODES="hamada-fm-01,internal-test-01".
 * Server-side only — never send the code list to the client.
 */

export function isValidAccessCode(
  code: string | null | undefined,
  envList: string | null | undefined,
): boolean {
  if (typeof code !== 'string' || typeof envList !== 'string') return false;
  const trimmed = code.trim();
  if (!trimmed) return false;
  return envList
    .split(',')
    .map((c) => c.trim())
    .filter(Boolean)
    .includes(trimmed);
}
