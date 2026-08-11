/**
 * Planning-Portal LGA display name -> `dcp_setback_controls.lga` slug.
 *
 * prior-art-checked: this is an EXTRACTION, not a new capability. The mapping
 * already existed twice, both times private to a route file and therefore
 * un-importable:
 *   - app/api/dcp/structured-controls/route.ts (getLgaSlugs + LGA_NAME_TO_SLUG)
 *   - app/api/canibuildit/check/route.ts:383 (its own inline normalise)
 * A third copy was about to be written for app/api/tod/parking-rates. Copy-pasted
 * lookup tables that drift apart are precisely what produced DQ-30, so the
 * structured-controls version — the more complete of the two — is lifted here
 * verbatim and that route now imports it. canibuildit/check adopted it in the
 * item-5 consolidation (2026-08-03) — its inline copy carried the same six
 * renames, so keying is unchanged and this is now the ONLY slug mapper.
 *
 * The portal returns display names ("City of Sydney", "The Hills Shire"); the
 * controls table is keyed by slug ("city_of_sydney", "the_hills"). Most pairs
 * differ only by case and separators, so those are handled mechanically and only
 * the genuine renames need a table entry.
 */

/** LGA display names whose slug is NOT just the lower-cased, underscored name. */
const LGA_NAME_TO_SLUG: Record<string, string> = {
  city_of_parramatta: 'parramatta',
  sydney: 'city_of_sydney',
  the_hills_shire: 'the_hills',
  city_of_canada_bay: 'canada_bay',
  city_of_ryde: 'ryde',
  strathfield_municipal: 'strathfield',
};

/**
 * Normalise an LGA display name or slug to the `dcp_setback_controls.lga` value.
 *
 * Returns null for empty/whitespace input rather than the empty string, so a
 * caller cannot accidentally query `WHERE lga = ''` and read the zero rows back
 * as "this council has no controls".
 */
export function toLgaSlug(name: string | null | undefined): string | null {
  const raw = (name ?? '').trim();
  if (!raw) return null;
  const normalised = raw
    .toLowerCase()
    .replace(/[-\s]+/g, '_')
    .replace(/[^a-z0-9_]/g, '');
  if (!normalised) return null;
  return LGA_NAME_TO_SLUG[normalised] ?? normalised;
}

/**
 * Slug list for a council, for callers that query with `= ANY($1)`.
 * Kept so app/api/dcp/structured-controls keeps its existing array-shaped call
 * site unchanged while sharing this table.
 */
export function toLgaSlugs(name: string | null | undefined): string[] {
  const slug = toLgaSlug(name);
  return slug ? [slug] : [];
}
