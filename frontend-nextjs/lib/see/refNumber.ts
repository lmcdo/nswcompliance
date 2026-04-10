/**
 * Clause reference surfacing — parse raw ref_number into human-readable citation.
 *
 * Each council stores ref_number differently:
 *   Marrickville: "Marrickville_DCP_2011__part2_s06_privacy__2_6_C3"
 *     → extract tail after last __ → format underscores → "2.6 C3"
 *   Leichhardt:   "C2.2.1.1" (already human-readable, stored verbatim)
 *     → use as-is
 *   Ashfield:     "Inner_West_Ashfield_DCP_2016__chapter_a__A-Part1_PC1"
 *     → internal code, not a standard DCP citation → skip
 */

/**
 * Parse a raw ref_number into a display-ready clause label.
 * Returns null when no useful citation can be derived.
 */
export function parseRefNumber(
  refNumber: string | null | undefined,
  sourceCouncil: string | null | undefined
): string | null {
  if (!refNumber) return null;

  const council = (sourceCouncil || '').toLowerCase();

  // Leichhardt: two formats exist —
  //   Short (173 rows):  "C2.2.1.1", "C2.2.1.1(a)" — already human-readable, use as-is
  //   Long (655 rows):   "Leichhardt_DCP_2013__part_d_energy__C6" — extract tail
  if (council === 'leichhardt') {
    if (!refNumber.includes('__')) {
      return refNumber.trim() || null;
    }
    const tail = refNumber.split('__').pop();
    if (!tail) return null;
    return formatDcpTail(tail);
  }

  // Marrickville: extract tail after last __, then format underscores
  // "Marrickville_DCP_2011__part2_s06_privacy__2_6_C3" → tail "2_6_C3" → "2.6 C3"
  if (council === 'marrickville') {
    const tail = refNumber.split('__').pop();
    if (!tail) return null;
    return formatDcpTail(tail);
  }

  // Ashfield: internal codes (A-Part1_PC1) — not standard DCP citations, skip
  return null;
}

/**
 * Format DCP ref_number tail into citation string.
 * Shared by Marrickville and Leichhardt long-format refs.
 * Splits on underscore, joins numeric-only tokens with dots, letter tokens with spaces.
 *
 * Examples:
 *   "2_6_C3"  → "2.6 C3"
 *   "1_1_11"  → "1.1.11"
 *   "2_6"     → "2.6"
 *   "C2"      → "C2"
 *   "C1_11_1" → "C1 11.1"
 *   "C2_C2"   → "C2 C2"  (section + control both named C2)
 *   "preamble"→ null
 */
function formatDcpTail(tail: string): string | null {
  // Skip non-citation entries like "preamble", "application", bare numbers that are page refs
  if (/^(preamble|application)$/i.test(tail)) return null;

  const tokens = tail.split('_');
  const parts: string[] = [];
  let numericRun: string[] = [];

  for (const token of tokens) {
    if (/^\d+$/.test(token)) {
      // Pure numeric token — accumulate for dot-joining
      numericRun.push(token);
    } else {
      // Non-numeric (e.g. "C3", "O1") — flush numeric run first, then add
      if (numericRun.length > 0) {
        parts.push(numericRun.join('.'));
        numericRun = [];
      }
      parts.push(token);
    }
  }

  // Flush any remaining numeric run
  if (numericRun.length > 0) {
    parts.push(numericRun.join('.'));
  }

  const result = parts.join(' ').trim();
  return result || null;
}
