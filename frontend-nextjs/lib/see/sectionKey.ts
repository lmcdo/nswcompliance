/**
 * Section key derivation — shared utility used by both ProvisionsByTocStructure
 * (for progress counting) and PageGroupedProvisions (for section grouping).
 *
 * Section key format: "${partKey}::${toc_section_number|inferred|general}"
 * Matches the same partKey logic as derivePartKey in ProvisionsByTocStructure.
 */

export interface ProvisionForSectionKey {
  v2_dcp_part?: string;
  source_chapter_key?: string;
  toc_section_number?: string | null;
  /** Embedded section heading text — used to infer a section number when toc_section_number is absent */
  section_header?: string | null;
}

/**
 * Derive the DCP part identifier from a provision.
 * Mirrors the derivePartKey logic in ProvisionsByTocStructure.
 */
export function deriveProvisionPartKey(p: ProvisionForSectionKey): string {
  if (p.v2_dcp_part && p.v2_dcp_part !== 'unknown') return p.v2_dcp_part;
  const ck = p.source_chapter_key;
  if (!ck) return 'general';
  const mSimple  = ck.match(/^part(\d+)-/);
  const mLetter  = ck.match(/^part-([a-z])-/);
  const mAppendix = ck.match(/^appendix-([a-z\d]+)/);
  if (mSimple)   return `Part ${mSimple[1]}`;
  if (mLetter)   return `Part ${mLetter[1].toUpperCase()}`;
  if (mAppendix) return `Appendix ${mAppendix[1].toUpperCase()}`;
  if (ck === 'da-guidelines') return 'Part 1';
  return ck;
}

/**
 * Try to infer a section number from the embedded section_header field.
 *
 * Some provisions have toc_section_number = null but carry a section heading
 * like "3.1 Setbacks" as the first line of the provision text. This extracts
 * the number portion so those provisions group correctly instead of all
 * collapsing into the "general" bucket.
 *
 * Recognises patterns like "3.1", "3.1.2", "B3.2" at the start of the text.
 * Returns null when no standard section number pattern is detected — those
 * provisions genuinely belong to "general" (true introductory/background text).
 */
export function inferSectionNumberFromHeader(header: string | null | undefined): string | null {
  if (!header) return null;
  const match = header.trim().match(/^([A-Z]?\d+(?:\.\d+)+)\b/i);
  return match ? match[1] : null;
}

/**
 * Build a unique section key for a provision.
 * This key is used as the primary identifier in da_section_responses.
 *
 * Resolution order:
 *  1. toc_section_number  — authoritative from DB join with dcp_table_of_contents
 *  2. section_header inference — fallback for provisions missing toc linkage
 *  3. "general"           — true un-numbered provisions (introductory/background)
 */
export function buildSectionKey(p: ProvisionForSectionKey): string {
  const partKey    = deriveProvisionPartKey(p);
  const sectionNum = p.toc_section_number
    || inferSectionNumberFromHeader(p.section_header)
    || 'general';
  return `${partKey}::${sectionNum}`;
}

/**
 * Parse a section key back into its component parts.
 * Inverse of buildSectionKey — single source of truth for SEEDocument and any
 * other consumer that needs to split a stored key.
 */
export function parseSectionKey(key: string): { part: string; sectionNumber: string } {
  const idx = key.indexOf('::');
  return idx === -1
    ? { part: key, sectionNumber: '' }
    : { part: key.substring(0, idx), sectionNumber: key.substring(idx + 2) };
}
