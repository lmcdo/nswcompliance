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

const ARTICLES = new Set(['and', 'or', 'of', 'the', 'in', 'to', 'a', 'an', 'for', 'at', 'by']);

/**
 * Derive a human-readable section title from a provision's toc_section_number and
 * section_header fields. Used as a fallback when the TOC structure does not carry a
 * section_title that matches the provision's section key (e.g. Leichhardt where
 * complete_toc indexes by slug "part-c-s1-general" but provisions group by "C1.2").
 *
 * Returns e.g. "C1.2 Demolition" from toc_section_number="C1.2", section_header="DEMOLITION".
 * Returns just the section number when the header looks like objective/control text rather
 * than a DCP section heading. Returns null when neither field is useful.
 */
export function deriveSectionTitleFromProvision(p: ProvisionForSectionKey): string | null {
  const secNum = p.toc_section_number?.trim();
  const header = p.section_header?.trim();
  if (!secNum) return null;
  if (!header) return secNum;

  // A heading the document prints in full caps has to be recased to read as a
  // title. That recasing REWRITES the source, so it stays confined to this
  // branch, where the original carries no case information to lose.
  const isAllCapsHeading = /^[A-Z][A-Z\s\d\-–()\/&,]+$/.test(header);
  if (isAllCapsHeading) {
    const titleCase = header
      .split(' ')
      .map((word, i) => {
        const lower = word.toLowerCase();
        return i === 0 || !ARTICLES.has(lower)
          ? lower.charAt(0).toUpperCase() + lower.slice(1)
          : lower;
      })
      .join(' ');
    return `${secNum} ${titleCase}`;
  }

  // Mixed-case header: the document's own heading. Shown VERBATIM — never
  // recased, reordered or paraphrased — minus a leading section number that
  // would otherwise print twice.
  //
  // WHY THIS BRANCH EXISTS. The all-caps test above matches 59 of the 19,219
  // served DCP provisions (measured 2026-10-08). The other 17,788 with a header
  // returned the bare section number here, and ProvisionsByTocStructure then
  // fell through to the chapter slug — so every section in a chapter was
  // labelled with the chapter's own name. Cumberland showed nineteen sections
  // as "2.10 Cumberland Dcp Part B Residential", "2.11 Cumberland Dcp Part B
  // Residential", ... while the database held "2.10 Visual and acoustic
  // privacy", "2.11 Solar access", "2.14 Fencing", "2.19 Garages and carports".
  // Fleet-wide: marrickville 2,966, leichhardt 2,757, city_of_sydney 2,375,
  // ashfield 2,010, canterbury_bankstown 1,902, northern_beaches 1,598.
  //
  // No heading-versus-body-text classifier is applied, deliberately. Every one
  // of the 19,219 rows carries a pdf_page, so whatever is shown here is
  // checkable against that page, and the alternative it replaces — the chapter
  // slug — is wrong for every section in the chapter. A header that reads like
  // body text is still the text at that page; the chapter slug never was.
  const body = stripLeadingSectionNumber(header, secNum);
  return body ? `${secNum} ${body}` : secNum;
}

/**
 * Remove a leading copy of THIS provision's own section number from its header,
 * so "2.10" + "2.10 Visual and acoustic privacy" does not render the number
 * twice.
 *
 * The header's own leading number is parsed and compared for EQUALITY, rather
 * than the section number being matched as a prefix. Prefix matching is wrong
 * whenever one section number is a prefix of another, which is common:
 * interpolating "2.1" into `^2\.1` ate the "2.1" out of "2.10 Visual privacy"
 * and rendered "2.1 0 Visual privacy", and "C1" did the same to "C1.5". Caught
 * by cross-review (gpt-5.6-sol, HIGH/MEDIUM pass on this branch) after the
 * first version of this function shipped a boundary-free regex.
 *
 * When the leading number is NOT this section's own, the header is returned
 * untouched — duplication is ugly but honest, and a mismatch there means the
 * row's toc_section_number and its heading disagree, which is a grouping
 * question about the data, not something to paper over here.
 */
function stripLeadingSectionNumber(header: string, secNum: string): string {
  const leading = header.match(/^([A-Za-z]?\d+(?:\.\d+)*)\s*[-–—:.]?\s*/);
  if (leading && leading[1] === secNum) {
    return header.slice(leading[0].length).trim();
  }
  return header.trim();
}
