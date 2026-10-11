/**
 * One council key for every lookup: the value stored in regulatory_provisions.source_council
 * and dcp_chapter_registry.council.
 *
 * prior-art-checked: reuse not viable -- the for-property route had three spellings of this
 * conversion and none produced that key. Rules were found by a document-name pattern
 * (councilToDocPattern), PDF links by `.toLowerCase()`, the precinct warning by the raw
 * value. Measured 2026-10-11 on the served-answer audit:
 *   - "City of Sydney" -> registry key "city of sydney": 0 PDF links on ~2,000 Sydney rules.
 *   - "city_of_parramatta" -> pattern "City_Of_Parramatta": 0 rules for Parramatta houses
 *     (616 stored).
 *   - "Leichhardt" compared with source_council 'leichhardt': the precinct warning never fired.
 *   - the "inner_west" fallback matched every "Inner West Ashfield DCP" document, so an
 *     Inner West house with no former council was shown Ashfield's whole plan.
 * Matching on source_council picks out exactly the same rows as the name pattern did for every
 * real council (checked council by council), minus those two wrong matches.
 */

/** Names the Planning Portal or the page send that are not the stored key once normalised. */
const COUNCIL_KEY_ALIASES: Record<string, string> = {
  city_of_parramatta: 'parramatta',
  sydney: 'city_of_sydney',
};

export function councilKey(name: string | null | undefined): string | null {
  if (!name) return null;
  const slug = name.toLowerCase().trim().replace(/[-\s]+/g, '_').replace(/[^a-z0-9_]/g, '');
  if (!slug) return null;
  return COUNCIL_KEY_ALIASES[slug] ?? slug;
}
