/**
 * Google Ads conversion tag — scoped, env-gated, ships dark.
 *
 * The site's primary analytics is PostHog; this adds ONLY a Google Ads
 * conversion signal so the $100 duplex-check test can optimise/measure in the
 * Ads UI. It is a no-op until BOTH env vars are set, so merging it changes
 * nothing until you paste the IDs from Google Ads → Conversions:
 *
 *   NEXT_PUBLIC_GOOGLE_ADS_ID          e.g. "AW-123456789"
 *   NEXT_PUBLIC_GOOGLE_ADS_LEAD_LABEL  the conversion action's label, e.g. "abCd_EfGhIjk"
 *
 * loadGoogleAds() injects gtag.js once (call it on the ads landing only — the
 * tag has no business loading site-wide). trackAdsConversion() fires the lead
 * conversion. Both guard on window + config, so they are SSR- and no-config-safe.
 */

const ADS_ID = process.env.NEXT_PUBLIC_GOOGLE_ADS_ID;
const LEAD_LABEL = process.env.NEXT_PUBLIC_GOOGLE_ADS_LEAD_LABEL;

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

let loaded = false;

/** Inject gtag.js and initialise the Ads tag. Idempotent; no-op if unconfigured. */
export function loadGoogleAds(): void {
  if (loaded || typeof window === 'undefined' || !ADS_ID) return;
  loaded = true;

  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${ADS_ID}`;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag(...args: unknown[]) {
    window.dataLayer!.push(args);
  };
  window.gtag('js', new Date());
  window.gtag('config', ADS_ID);
}

/**
 * Fire the lead conversion. No-op unless both env vars are set and gtag loaded.
 * Safe to call on every successful lead submit — Google dedupes by order id if
 * one is supplied; here we don't, so it counts each submit as a conversion.
 */
export function trackAdsConversion(): void {
  if (typeof window === 'undefined' || !ADS_ID || !LEAD_LABEL || !window.gtag) return;
  window.gtag('event', 'conversion', { send_to: `${ADS_ID}/${LEAD_LABEL}` });
}
