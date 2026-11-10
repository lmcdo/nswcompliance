/**
 * A DCP row's condition as the reader should see it.
 *
 * Some stored conditions carry an extraction note for us after the council's words, e.g.
 * "excludes outbuildings and secondary dwellings. NOT yet stored: upper-floor living room 9.0m
 * (C10) ...". That note was shown on the live DCP tab (Concord, 2026-10-19). It is cut here.
 *
 * prior-art-checked: the guard's matches (scripts/_set_all_public_urls.py etc.) set PDF URLs;
 * nothing trims condition text for display.
 */
const INTERNAL_TAIL = /\s*NOT yet stored:[\s\S]*$/i;
// The note also comes as a sentence of its own: "Tiers >900-1500m2 = 6.5m ... are NOT yet stored."
// (Mount Annan, 2026-10-19). Drop every sentence that carries the marker.
// Sentences end at ". " before a capital, so "6.5m" or "p.11" is never split.
const SENTENCE_BREAK = /(?<=\.)\s+(?=[A-Z])/;
const INTERNAL_MARKER = /\bNOT yet stored\b/;
// Our own row-type tags at the start of a condition, written by our scripts
// (scripts/archive/tmp_insert_explanation_rows.py, dq142_build_controls_migration.py), never by a
// council. The six measured on served rows 2026-11-10 (nofig_db.json); listed, not pattern-matched,
// so a council's own capitalised heading ("NOTE:") is never cut.
const INTERNAL_PREFIX =
  /^\s*(?:NO FIGURE|FSR-CONTROLLED|DEFERS-TO-ADG|CHARACTER-BASED|ALTERNATIVE-METRIC|QUALITATIVE)\s*:\s*/;

export function publicCondition(condition: string | null | undefined): string | null {
  const shown = (condition ?? '')
    .replace(INTERNAL_PREFIX, '')
    .replace(INTERNAL_TAIL, '')
    .split(SENTENCE_BREAK)
    .filter((s) => !INTERNAL_MARKER.test(s))
    .join(' ')
    .trim();
  return shown || null;
}
