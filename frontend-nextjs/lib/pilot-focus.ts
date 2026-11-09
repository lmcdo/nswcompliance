/**
 * Private pilot focus (owner decision 2026-11-09): the site points at two products only,
 * Council Rules (/assessment) and Site Facts (/reports/intelligence-brief), for the ten councils
 * named in shared/brief-scope.json.
 *
 * Everything else stays reachable by URL, but is not linked from any menu, footer, directory or
 * sitemap, and middleware sends `X-Robots-Tag: noindex` on it. To bring a page back, remove its
 * prefix from PILOT_UNLISTED_PREFIXES and restore its links.
 *
 * Gate: __tests__/lib/pilot-focus-links.test.ts fails if a navigation file links anywhere outside
 * PILOT_ALLOWED_LINKS. The older, narrower list is lib/hidden-products.ts (still enforced).
 *
 * prior-art-checked: lib/hidden-products.ts hides three withdrawn products and is scanned across
 * the whole repo; this list is wider and is enforced on navigation surfaces only, because the 39
 * blog posts link inward to the old tools and nobody reaches them once the blog is unlinked.
 */
import briefScope from '@/shared/brief-scope.json';
import { toLgaSlug } from '@/lib/lga-slug';
import { zoneCode } from '@/lib/zone-code';

/** The councils the pilot is measured on (the brief's scope file, one source). */
export const PILOT_COUNCILS: readonly string[] = briefScope.councils;

/** Plain display names for the pilot page. Names only, no planning data. */
export const PILOT_COUNCIL_NAMES: Record<string, string> = {
  penrith: 'Penrith',
  wollongong: 'Wollongong',
  waverley: 'Waverley',
  ku_ring_gai: 'Ku-ring-gai',
  ashfield: 'Ashfield (Inner West)',
  blacktown: 'Blacktown',
  northern_beaches: 'Northern Beaches',
  georges_river: 'Georges River',
  parramatta: 'City of Parramatta',
  hornsby: 'Hornsby',
};

/** Display names of the councils in the scope file, in its order. Pages list these, never the names table, so a
 * council removed from brief-scope.json disappears from every page at once. A key with no name is a test failure. */
export const PILOT_COUNCIL_LABELS: readonly string[] = PILOT_COUNCILS.map((k) => PILOT_COUNCIL_NAMES[k]).filter(Boolean);

/** The only internal paths a navigation surface may link to. */
export const PILOT_ALLOWED_LINKS: readonly string[] = [
  '/',
  '/assessment',
  '/reports/intelligence-brief',
  '/how-it-works',
  '/contact',
  '/terms',
  '/privacy',
];

/** Reachable by URL, never linked, never indexed, during the pilot. */
export const PILOT_UNLISTED_PREFIXES = [
  '/blog',
  '/pricing',
  '/for',
  '/tools',
  '/check',
  '/duplex-check',
  '/granny-flat',
  '/conveyancing',
  '/flood-risk',
  '/pre-da-history',
  '/bushfire',
  '/solar-potential',
  '/climate-risk',
  '/reports/granny-flat',
  '/reports/flood',
  '/reports/conveyancing',
  '/reports/threat-radar',
  '/reports/pre-da-history',
  '/reports/bushfire',
  '/reports/solar-yield',
  '/embed',
  '/prospector',
  '/simple',
  '/water-demo',
  '/widget-demo',
  '/developers',
  '/partner',
  '/browse',
  '/dcp-browse',
  '/open-data',
  '/planning-standards',
  '/glossary',
  '/quick-guide',
  '/user-guide',
  '/what-you-get',
  '/canibuildit',
  '/site-directory',
] as const;

/** True when a path or URL is withdrawn from navigation and search for the pilot. */
export function isPilotUnlisted(pathOrUrl: string): boolean {
  let path = pathOrUrl;
  try {
    if (/^https?:\/\//.test(pathOrUrl)) path = new URL(pathOrUrl).pathname;
  } catch {
    return false;
  }
  path = path.split(/[?#]/)[0];
  return PILOT_UNLISTED_PREFIXES.some((p) => path === p || path.startsWith(`${p}/`));
}

/**
 * The pilot council key for an address, or null when it is not in the pilot. Tries the portal's
 * former-council slug first (it separates Ashfield from the rest of Inner West), then the LGA name
 * slugged exactly as the brief route does, and returns the first that is a pilot council. Trying both
 * means an address whose former-council value is an old name (for example an amalgamated area) is
 * still found by its current council. Unknown or missing council is NOT in the pilot.
 */
export function pilotCouncilKey(formerCouncil: string | null | undefined, lga: string | null | undefined): string | null {
  const candidates = [(formerCouncil || '').trim().toLowerCase(), toLgaSlug(lga) || ''];
  return candidates.find((k) => !!k && PILOT_COUNCILS.includes(k)) ?? null;
}

/** The council key the data calls use: the pilot key when there is one, otherwise the key the page always used. */
export function dataCouncilKey(formerCouncil: string | null | undefined, lga: string | null | undefined): string {
  return pilotCouncilKey(formerCouncil, lga) ?? ((formerCouncil || '').trim().toLowerCase() || toLgaSlug(lga) || '');
}

export function isPilotCouncil(formerCouncil: string | null | undefined, lga: string | null | undefined): boolean {
  return pilotCouncilKey(formerCouncil, lga) !== null;
}

/** The one zone the clause lists were measured for (shared/brief-scope.json zone_group). */
export const PILOT_ZONE: string = briefScope.zone_group;

/** True only when the zone label reads as the pilot zone. An unreadable or missing zone is NOT in the pilot. */
export function isPilotZone(zone: string | null | undefined): boolean {
  return zoneCode(zone) === PILOT_ZONE;
}
