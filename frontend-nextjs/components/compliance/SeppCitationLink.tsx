/**
 * prior-art-checked: presentational only — URLs come from lib/citation-instrument-urls.ts
 * (the DCP tab's citation module, reused, not duplicated). Split out of
 * StateLevelControls.tsx because that file is already ~1,600 lines.
 */
import { ExternalLink } from 'lucide-react';
import { REGISTRY_INSTRUMENT_URLS, legislationAnchorUrl } from '@/lib/citation-instrument-urls';

/**
 * SEPP (Sustainable Buildings) 2022 has no instrument_registry row (see
 * __tests__/lib/citation-instrument-urls.test.ts, unmatched set), so no
 * legislation.nsw.gov.au deep link is derived for it. The SEPP tab already links
 * this Planning Portal publication page; citations reuse it until a registry row
 * with a verified EPI number exists.
 */
export const SUSTAINABLE_BUILDINGS_SEPP_PORTAL_URL =
  'https://www.planningportal.nsw.gov.au/publications/environmental-planning-instruments/state-environmental-planning-policy-sustainable-buildings-2022';

/** Live, in-force SEPP (Housing) 2021 provision, e.g. `sec.24` or `sch.11`. */
export function seppHousingProvisionUrl(anchor: string): string {
  // Non-null: the base URL is a registry constant.
  return legislationAnchorUrl(REGISTRY_INSTRUMENT_URLS.sepp_housing_2021, anchor)!;
}

interface SeppCitationLinkProps {
  href: string;
  /** What the link opens — used for the tooltip and the accessible name. */
  label: string;
  className?: string;
}

/**
 * Icon link to the current in-force text of a SEPP provision. Replaces static
 * PDF page images, which froze a single past version of the instrument (and, for
 * some, pointed at image paths that were never published).
 */
export function SeppCitationLink({ href, label, className }: SeppCitationLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      title={label}
      aria-label={label}
      className={
        className ??
        'p-1 rounded text-purple-600 hover:text-purple-800 hover:bg-purple-50 transition-colors flex-shrink-0'
      }
    >
      <ExternalLink className="h-4 w-4" />
    </a>
  );
}
