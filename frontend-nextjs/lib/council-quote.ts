/**
 * Which words a council DCP rule shows: the council's own, when a program has copied them from its
 * PDF (migration 111, scripts/council_quote.py), else the extracted text with a note saying so.
 *
 * prior-art-checked: nothing chose a rule's display text -- every renderer printed provision_text,
 * which is the reader's output. 2026-10-12: 4,552 of 19,627 served quotes were not printed word for
 * word in the council's PDF; some were reworded (Northern Beaches 130236).
 *
 *   exact / recovered   council_quote is the council's printed text, shown alone with the council's
 *                       own line breaks; only its numbers may feed a reference chip
 *   unconfirmed         extracted text, "Not matched word for word to the council's PDF"; no chip
 *   not_a_control       extracted text, "Map or figure text from the plan, not a rule"; no chip
 *   no verdict yet      extracted text, "Not yet checked against the council's PDF"; no chip
 *   rows outside the check (no source_council: LEP/SEPP) -> unchanged
 */

export interface QuoteFields {
  provision_text?: string | null;
  council_quote?: string | null;
  quote_status?: string | null;
  quote_page?: number | null;
  source_council?: string | null;
}

const CONFIRMED = new Set(['exact', 'recovered']);

export const QUOTE_NOTE_CONFIRMED = "Wording copied from the council's plan";
export const QUOTE_NOTE_UNMATCHED = "Not matched word for word to the council's PDF";
export const QUOTE_NOTE_NOT_A_RULE = 'Map or figure text from the plan, not a rule';
export const QUOTE_NOTE_UNCHECKED = "Not yet checked against the council's PDF";

function hasText(q: string | null | undefined): boolean {
  return typeof q === 'string' && q.trim().length > 0;
}

/** Server side: true when the council's own words are stored for this rule. */
export function hasCouncilWords(p: QuoteFields): boolean {
  return Boolean(p.quote_status && CONFIRMED.has(p.quote_status) && hasText(p.council_quote)
    && typeof p.quote_page === 'number' && p.quote_page > 0);
}

/** Server side: the status to send. exact / recovered only when the words really are stored (the
 *  migration 111 constraint already requires it), because the client trusts this status alone --
 *  the quote itself is not sent twice. */
export function servedQuoteStatus(p: QuoteFields): string | null {
  const s = p.quote_status ?? null;
  return s && CONFIRMED.has(s) && !hasCouncilWords(p) ? null : s;   // words AND their page, or neither
}

/** Client side: the rule's served text is the council's own words. */
export function showsCouncilWords(p: QuoteFields): boolean {
  return Boolean(p.quote_status && CONFIRMED.has(p.quote_status));
}

/** A label alone on its PDF line ("(a)", "C3", "2.1") joins the text printed beside it. Every other
 *  line break is kept as the council printed it: joining lines changes words ("Multi-\nunit") and
 *  merges table rows. */
// Case matters: "C3" is a control label, "m2" is a unit printed alone in a table cell.
const BARE_LABEL = /^(?:\(?(?:[a-zA-Z]|[ivxIVX]{1,4}|\d{1,3})[.)]|[A-Z]{1,3}\d+[A-Za-z]?|\d+(?:\.\d+)+|[•▪◦])$/;

function joinBareLabels(quote: string): string {
  const out: string[] = [];
  for (const line of quote.split('\n')) {
    const last = out[out.length - 1];
    if (last !== undefined && BARE_LABEL.test(last.trim()) && line.trim()) out[out.length - 1] = `${last.trim()} ${line.trim()}`;
    else out.push(line);
  }
  return out.join('\n').trim();
}

/** The text a rule shows: only the council's words when they are stored -- no heading of ours above
 *  them, because the note says the wording is the council's. */
export function shownText(p: QuoteFields): string | null {
  if (!hasCouncilWords(p)) return p.provision_text ?? null;   // unchanged, null included
  return joinBareLabels(p.council_quote as string);
}

/** The note printed under a council DCP rule, by the copier's verdict; null outside the check (LEP/SEPP). */
export function quoteNote(p: QuoteFields): string | null {
  if (!p.source_council) return null;
  if (showsCouncilWords(p)) return QUOTE_NOTE_CONFIRMED;
  if (p.quote_status === 'unconfirmed') return QUOTE_NOTE_UNMATCHED;
  if (p.quote_status === 'not_a_control') return QUOTE_NOTE_NOT_A_RULE;
  return QUOTE_NOTE_UNCHECKED;
}

/** Whether numbers may be read from this rule's text: never from an unconfirmed council rule. */
export function numbersUsable(p: QuoteFields): boolean {
  return !p.source_council || showsCouncilWords(p);
}

/** The quote columns every route serving council DCP rules selects, for a table alias. */
export function quoteColumns(alias = 'rp'): string {
  return `${alias}.council_quote, ${alias}.quote_page, ${alias}.quote_status`;
}

/**
 * Server side: a served rule row as the client must see it -- its text the council's own words when
 * stored, its status normalised (servedQuoteStatus), and the quote itself not sent twice. `clean`
 * runs on the extracted text only (e.g. the OCR page-header strip in the for-property route).
 * One helper for every route, so no page shows the reader's words where another shows the council's.
 */
export function withCouncilWords<T extends Record<string, any>>(
  { council_quote, ...row }: T & { council_quote?: string | null },
  clean: (t: string | null) => string | null = (t) => t,
): Omit<T, 'council_quote'> & { provision_text: string | null; quote_status: string | null } {
  return {
    ...(row as Omit<T, 'council_quote'>),
    provision_text: shownText({ ...row, council_quote, provision_text: clean(row.provision_text ?? null) }),
    quote_status: servedQuoteStatus({ ...row, council_quote }),
  };
}
