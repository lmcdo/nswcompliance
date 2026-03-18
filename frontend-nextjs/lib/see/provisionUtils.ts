/**
 * Canonical numeric measurement pattern for planning regulation provisions.
 * Matches numeric values followed by planning units (m, m², ha, %, etc.)
 * with word boundaries to avoid partial matches within text.
 *
 * Exported for use in provision filtering, topic stats, and tests.
 */
export const NUMERIC_MEASUREMENT_RE =
  /\b\d+(?:\.\d+)?\s*(?:m²|m|mm|cm|km|%|metres?|meters?|centimètres?|centimeters?|sqm|square mètres?|ha|hectares?)(?!\w)/i;

/**
 * Filter and deduplicate a flat provisions array.
 * Removes TOC entries, non-actionable provisions, definitions, and exact-text duplicates.
 * NOTE: Negative pdf_page values are kept — they are PDF numbering artifacts, not bad data
 * (e.g. heritage controls for HCAs often have negative printed page numbers).
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function filterAndDedupeProvisions(provisions: any[]): any[] {
  // First pass: exclude non-provisions
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const valid = provisions.filter((p: any) => {
    const text: string = p.provision_text || '';

    if (p.v2_provision_type === 'TOC') return false;

    // NOTE: text-based TOC heuristic removed — \s+ in the regex matched newlines, causing
    // false positives for legitimate provisions whose text contains section headings inline
    // (e.g. Marrickville Part 2 provisions with "2.9\nCommunity Safety" patterns).
    // Server-side SQL already filters TOC entries via v2_provision_type and text patterns.

    if (p.v2_is_actionable === false) return false;

    const isDefinitions =
      text.includes('KEY TERMS') ||
      (text.includes('Definitions') && text.includes('means a')) ||
      p.v2_topic?.toLowerCase() === 'definitions';
    if (isDefinitions) return false;

    return true;
  });

  // Second pass: deduplicate by normalised text + page
  const seen = new Set<string>();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return valid.filter((p: any) => {
    const normalised = (p.provision_text || '')
      .replace(/^(C|O)?\d+\s+/gm, '')
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 100);
    const key = `${normalised}|${p.pdf_page || 0}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
