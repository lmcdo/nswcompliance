/**
 * Products withdrawn from navigation, sitemaps and links until they are
 * checked (owner decision 2026-10-28): bushfire, solar, and climate
 * risk (which runs flood and bushfire together).
 *
 * The pages still work for anyone who has a link; they are not linked from
 * anywhere on the site, not listed in any sitemap, and middleware sends
 * `X-Robots-Tag: noindex` on them.
 *
 * Gate: __tests__/lib/hidden-products-not-linked.test.ts fails if any page or
 * component links to one of these routes. To bring a product back, remove its
 * prefixes here and restore its links.
 *
 * prior-art-checked: no product-visibility switch exists (grep for hidden
 * tools/routes/flags found only per-page noindex metadata); the guard's other
 * matches are setuptools internals and a satellite manifest checker.
 */
export const HIDDEN_ROUTE_PREFIXES = [
  '/bushfire',
  '/reports/bushfire',
  '/solar-potential',
  '/reports/solar-yield',
  '/embed/solar-yield',
  '/climate-risk',
] as const;

/** True when a path or URL points at a hidden product route. */
export function isHiddenPath(pathOrUrl: string): boolean {
  let path = pathOrUrl;
  try {
    if (/^https?:\/\//.test(pathOrUrl)) path = new URL(pathOrUrl).pathname;
  } catch {
    return false;
  }
  path = path.split(/[?#]/)[0];
  return HIDDEN_ROUTE_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}
