/**
 * Which words a council DCP rule shows: the council's own, when a program has copied them from its
 * PDF (migration 111, scripts/council_quote.py), else the extracted text with a note saying so.
 *
 * prior-art-checked: nothing chose a rule's display text -- every renderer printed provision_text,
 * which is the reader's output. 2026-10-12: 4,552 of 19,627 served quotes were not printed word for
 * word in the council's PDF; some were reworded (Northern Beaches 130236).
 *
 *   exact / recovered   council_quote is the council's printed text; it is shown, and only its
 *                       numbers may feed a reference chip
 *   anything else on a council DCP row (unconfirmed, not_a_control, not checked yet) -> the extracted
 *                       text, marked "not yet checked against the council's PDF"; no number chip
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

export const QUOTE_NOTE_CONFIRMED = "Council's wording, copied from the plan";
export const QUOTE_NOTE_UNCHECKED = "Not yet checked against the council's PDF";

/** Server side: true when the council's own words are stored for this rule. */
export function hasCouncilWords(p: QuoteFields): boolean {
  return Boolean(p.quote_status && CONFIRMED.has(p.quote_status) && p.council_quote);
}

/** Server side: the status to send. exact / recovered only when the words really are stored (the
 *  migration 111 constraint already requires it), because the client trusts this status alone --
 *  the quote itself is not sent twice. */
export function servedQuoteStatus(p: QuoteFields): string | null {
  const s = p.quote_status ?? null;
  return s && CONFIRMED.has(s) && !p.council_quote ? null : s;
}

/** Client side: the rule's served text is the council's own words. */
export function showsCouncilWords(p: QuoteFields): boolean {
  return Boolean(p.quote_status && CONFIRMED.has(p.quote_status));
}

/** A label line ("(b)", "C3", "2.1", "iv.", a bullet) starts a new line; any other PDF line break
 *  is only where the page ran out of width, so it reads as a space. */
const LABEL = String.raw`(?:\(?(?:[a-z]|[ivx]{1,4}|\d{1,3})[.)]|[A-Z]{1,3}\d+[A-Za-z]?|\d+(?:\.\d+)+|[•▪◦–-])`;
const STARTS_ITEM = new RegExp(`^${LABEL}(?:\\s|$)`, 'i');
const BARE_LABEL = new RegExp(`^${LABEL}$`, 'i');

function reflow(quote: string): string {
  const lines = quote.split('\n').map((l) => l.trim()).filter(Boolean);
  const out: string[] = [];
  for (const line of lines) {
    const last = out[out.length - 1];
    if (last === undefined) out.push(line);
    else if (BARE_LABEL.test(last)) out[out.length - 1] = `${last} ${line}`;   // "(a)" + its text
    else if (STARTS_ITEM.test(line)) out.push(line);
    else out[out.length - 1] = `${last} ${line}`;
  }
  return out.join('\n');
}

/** The text a rule shows. Keeps the extracted "# heading" line, which renderers use as a title. */
export function shownText(p: QuoteFields): string {
  const extracted = p.provision_text ?? '';
  if (!hasCouncilWords(p)) return extracted;
  const head = extracted.trimStart().startsWith('#') ? extracted.trimStart().split('\n')[0] : '';
  const words = reflow(p.council_quote as string);
  return head ? `${head}\n\n${words}` : words;
}

/** The note printed under a council DCP rule; null for rules outside the check (LEP/SEPP). */
export function quoteNote(p: QuoteFields): string | null {
  if (!p.source_council) return null;
  return showsCouncilWords(p) ? QUOTE_NOTE_CONFIRMED : QUOTE_NOTE_UNCHECKED;
}

/** Whether numbers may be read from this rule's text: never from an unchecked council rule. */
export function numbersUsable(p: QuoteFields): boolean {
  return !p.source_council || showsCouncilWords(p);
}
