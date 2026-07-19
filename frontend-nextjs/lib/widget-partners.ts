/**
 * White-label duplex-checker partner registry.
 *
 * Drives the branded demo pages (/widget-demo/[slug]) and the partner embed
 * (/embed/upzoning?ref=<slug>). Presentation config ONLY — no planning data,
 * no gate logic; every check runs through /api/upzoning like the public tool.
 *
 * prior-art-checked: lib/sanitize.ts is DOMPurify HTML sanitisation for
 * dangerouslySetInnerHTML — it cannot validate a URL's protocol or whitelist
 * a display-name pattern for query params, which is what the two helpers here
 * do; app/partner/page.tsx is the marketing page listing iframe snippets (it
 * will LINK to these demos) and holds no partner data structure to extend.
 *
 * Sites and contact URLs verified live 2026-07-19 during outreach research
 * (see ~/.claude/plans/ce-builder-widget-outreach-emails-2026-07.md). Where a
 * contact page was not directly verified, ctaUrl falls back to the site root
 * rather than a guessed path.
 */

export interface WidgetPartner {
  /** URL slug for /widget-demo/[slug] and the embed ref param */
  slug: string;
  /** Display name shown on the widget ("The <name> duplex checker") */
  name: string;
  /** Partner's own website (https, verified) */
  site: string;
  /** Where the widget's enquiry button sends the visitor (partner's page) */
  ctaUrl: string;
}

export const WIDGET_PARTNERS: WidgetPartner[] = [
  { slug: 'buildana', name: 'Buildana', site: 'https://www.buildana.com.au', ctaUrl: 'https://www.buildana.com.au/contact' },
  { slug: 'clover-homes', name: 'Clover Homes', site: 'https://cloverhomes.com.au', ctaUrl: 'https://cloverhomes.com.au/contact/' },
  { slug: 'worthington', name: 'Worthington Homes', site: 'https://www.worthingtonhomes.com.au', ctaUrl: 'https://www.worthingtonhomes.com.au/contact-us/' },
  { slug: 'provincial', name: 'Provincial Homes', site: 'https://www.provincialhomes.com.au', ctaUrl: 'https://www.provincialhomes.com.au/contact/' },
  { slug: 'dixon-sydney', name: 'Dixon Homes Sydney', site: 'https://dixonhomessydney.com.au', ctaUrl: 'https://dixonhomessydney.com.au' },
  { slug: 'phase-projects', name: 'Phase Projects', site: 'https://phaseprojects.com.au', ctaUrl: 'https://phaseprojects.com.au/contact/' },
  { slug: 'royal', name: 'Royal Constructions', site: 'https://royalconstructions.com.au', ctaUrl: 'https://royalconstructions.com.au/contact/' },
  { slug: 'duplex-building-design', name: 'Duplex Building Design', site: 'https://duplexbuildingdesign.com', ctaUrl: 'https://duplexbuildingdesign.com/contact-sydney/' },
  { slug: 'meridian', name: 'Meridian Homes', site: 'https://www.meridianhomes.net.au', ctaUrl: 'https://www.meridianhomes.net.au/contact-us/' },
  { slug: 'hammercorp', name: 'Hammercorp', site: 'https://hammercorp.com.au', ctaUrl: 'https://hammercorp.com.au/contact/' },
  { slug: 'kobo', name: 'Kobo Projects', site: 'https://www.koboprojects.com.au', ctaUrl: 'https://www.koboprojects.com.au/contact' },
  { slug: 'icon-homes', name: 'Icon Homes', site: 'https://iconhomes.com.au', ctaUrl: 'https://iconhomes.com.au/contact/' },
  { slug: 'firmus', name: 'Firmus Building', site: 'https://www.firmusbuilding.com.au', ctaUrl: 'https://www.firmusbuilding.com.au' },
  { slug: 'brickwood', name: 'Brickwood Homes', site: 'https://brickwoodhomes.com.au', ctaUrl: 'https://brickwoodhomes.com.au/contact/' },
  { slug: 'managed-build', name: 'Managed Build', site: 'https://www.managedbuild.com.au', ctaUrl: 'https://www.managedbuild.com.au/contact-us/' },
  { slug: 'buildrite', name: 'BuildRite Sydney', site: 'https://buildritesydney.com.au', ctaUrl: 'https://buildritesydney.com.au/contact/' },
  { slug: 'ardent', name: 'Ardent Construction and Development', site: 'https://www.ardentconstruction.com.au', ctaUrl: 'https://www.ardentconstruction.com.au/contact/' },
  { slug: 'kurmond', name: 'Kurmond Homes', site: 'https://www.kurmondhomes.com.au', ctaUrl: 'https://www.kurmondhomes.com.au' },
  { slug: 'js-construction', name: 'JS Construction Sydney', site: 'https://jsconstructionsydney.com', ctaUrl: 'https://jsconstructionsydney.com/contact-us/' },
  { slug: 'allcastle', name: 'Allcastle Homes', site: 'https://www.allcastlehomes.com.au', ctaUrl: 'https://www.allcastlehomes.com.au' },
];

/**
 * Branding resolves ONLY from this registry — there are deliberately no
 * free-form partner/cta query params. Review finding (PR #790): free-form
 * params let an attacker render a registered builder's NAME with an
 * arbitrary https CTA (?partner=Buildana&cta=https://phishing.example);
 * name-vs-registry checks don't close that (typosquats, casing, spacing).
 * Adding a pilot partner = one registry entry in a PR — minutes, and every
 * brand/CTA pairing stays repo-reviewed.
 *
 * Accepts string | string[] because Next.js delivers repeated query params
 * as arrays; a repeated ref is rejected rather than silently picking one.
 */
export function getWidgetPartner(slug: string | string[] | undefined): WidgetPartner | null {
  if (typeof slug !== 'string') return null;
  return WIDGET_PARTNERS.find((p) => p.slug === slug) ?? null;
}
