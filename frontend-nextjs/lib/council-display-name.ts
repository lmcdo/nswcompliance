/**
 * A council name as the Planning Portal sends it ("THE HILLS SHIRE", "CITY OF PARRAMATTA"),
 * written for a sentence: "The Hills Shire", "City of Parramatta".
 *
 * Sentences must not put "the" in front of it: "in the THE HILLS SHIRE area" was on the live
 * page (2026-10-19). Use councilDisplayName and word the sentence so no article is needed.
 */
const SMALL = new Set(['of', 'and', 'the', 'on']);

export function councilDisplayName(name: string | null | undefined): string | null {
  const raw = (name ?? '').trim();
  if (!raw) return null;
  return raw
    .toLowerCase()
    .split(/\s+/)
    .map((w, i) => (i > 0 && SMALL.has(w) ? w : w.replace(/(^|-)([a-z])/g, (_m, p, c) => p + c.toUpperCase())))
    .join(' ');
}
