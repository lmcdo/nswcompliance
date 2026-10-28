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
 *   unconfirmed         our words are NOT shown (user, 2026-10-26: only words proven in the council's
 *   no verdict yet      current plan are served); the text is a pointer to page N of the council's plan,
 *                       page N is pageLabel(); no note, no chip. A changed council file clears the verdict
 *                       (migration 112 trigger), so superseded wording stops showing until re-proven.
 *   not_a_control       extracted text, "Map or figure text from the plan, not a rule"; no chip
 *   rows outside the check (no source_council: LEP/SEPP) -> unchanged
 */

import { PAGE_NOT_LOCATED, pageLabel, sectionPage, type PageFields } from '@/lib/page-citation';

export interface QuoteFields extends PageFields {
  provision_text?: string | null;
  council_quote?: string | null;
  quote_status?: string | null;
  quote_page?: number | null;
  source_council?: string | null;
  source_chapter_key?: string | null;
  citation_status?: string | null;
}

const CONFIRMED = new Set(['exact', 'recovered']);

export const QUOTE_NOTE_CONFIRMED = "Wording copied from the council's plan";
/** An unproven rule's note without a page; with one it reads "... on page 12 of the council's plan". */
export const QUOTE_NOTE_UNMATCHED = "Wording not shown here — read it in the council's plan";
export const QUOTE_NOTE_NOT_A_RULE = 'Map or figure text from the plan, not a rule';
export const QUOTE_NOTE_UNCHECKED = QUOTE_NOTE_UNMATCHED;
/** A council rule outside the wording check (no DCP chapter): shown, marked as our reading. */
export const QUOTE_NOTE_OUTSIDE = "Our reading — check the exact wording in the council's plan";

/** A council-named LEP clause (no DCP chapter) not proven against the NSW legislation: its text is withheld. */
export const QUOTE_NOTE_STATE_LAW_UNPROVEN = 'Wording not shown here — read it on the NSW legislation website';
/** A council-named LEP clause proven word for word against the NSW legislation (scripts/apply_state_law_proof.py). */
export const QUOTE_NOTE_STATE_LAW = 'Wording from the NSW legislation';

/** Council-named rule with no DCP chapter and no quote verdict: an LEP clause, checked against the legislation. */
function isStateLawRow(p: QuoteFields): boolean {
  return Boolean(p.source_council) && !p.source_chapter_key && !p.quote_status;
}

/** The note for a rule whose words are not proven, naming the page shown beside it when there is one. */
export function unprovenNote(p: QuoteFields): string {
  const label = pageLabel(p);
  const sp = sectionPage(p);
  if (sp !== null && label === `near PDF page ${sp}`) {
    return `Wording not shown here — read it in the council's plan near PDF page ${sp}, which has rules under the same heading`;
  }
  return label && label !== PAGE_NOT_LOCATED
    ? `Wording not shown here — read it on ${label} of the council's plan`
    : QUOTE_NOTE_UNMATCHED;
}

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
  if (isWithheld(p)) return isStateLawRow(p) ? QUOTE_NOTE_STATE_LAW_UNPROVEN : unprovenNote(p);
  if (!hasCouncilWords(p)) return p.provision_text ?? null;   // unchanged, null included
  return joinBareLabels(p.council_quote as string);
}

/** A council DCP rule whose words are not proven in the council's current plan: its text is withheld.
 *  Proven failing (unconfirmed), or a DCP chapter rule with no verdict -- a changed council file clears
 *  it. Rows with no chapter (LEP clauses carrying a council name, e.g. 495 inner_west) are checked
 *  against the NSW legislation instead: shown only when citation_status is 'proven'. */
export function isWithheld(p: QuoteFields): boolean {
  if (!p.source_council || hasCouncilWords(p) || p.quote_status === 'not_a_control') return false;
  if (isStateLawRow(p)) return p.citation_status !== 'proven';   // missing field fails closed
  return true;   // any other verdict, or a DCP chapter rule with none, fails closed
}

/** The note printed under a council DCP rule, by the copier's verdict; null outside the check (LEP/SEPP)
 *  and for a withheld rule, whose text already is the pointer. */
export function quoteNote(p: QuoteFields): string | null {
  if (!p.source_council) return null;
  if (showsCouncilWords(p)) return QUOTE_NOTE_CONFIRMED;
  if (p.quote_status === 'not_a_control') return QUOTE_NOTE_NOT_A_RULE;
  if (isWithheld(p)) return null;
  return isStateLawRow(p) ? QUOTE_NOTE_STATE_LAW : QUOTE_NOTE_OUTSIDE;
}

/** Whether numbers may be read from this rule's text: never from an unconfirmed council rule. */
export function numbersUsable(p: QuoteFields): boolean {
  return !p.source_council || showsCouncilWords(p) || (isStateLawRow(p) && !isWithheld(p));
}

/** The quote columns every route serving council DCP rules selects, for a table alias (a
 *  regulatory_provisions row). section_page: for a rule whose words are not proven, the quote_page
 *  of a PROVEN rule in the same document, council, chapter and section heading -- a page whose words were found
 *  in the current PDF -- the one nearest the rule's own pdf_page, and only within one reader chunk
 *  (12 pages): headings repeat across a chapter (Ashfield "DS4.1" is proven on 12 pages, 2026-10-28).
 *  No heading, no pdf_page, or no proven rule that near -> NULL, and the rule links to the plan with
 *  no page (a guessed page is worse than none). */
export function quoteColumns(alias = 'rp'): string {
  const a = alias;
  return `${a}.council_quote, ${a}.quote_page, ${a}.quote_status, ${a}.source_chapter_key, ${a}.citation_status,
    CASE WHEN ${a}.source_council IS NOT NULL AND ${a}.source_chapter_key IS NOT NULL
          AND COALESCE(BTRIM(${a}.section_header), '') <> ''
          AND ${a}.pdf_page > 0
          AND ${a}.quote_status IS DISTINCT FROM 'exact' AND ${a}.quote_status IS DISTINCT FROM 'recovered'
      THEN (SELECT sib.quote_page FROM regulatory_provisions sib
            WHERE sib.is_current AND sib.document_id = ${a}.document_id AND sib.source_council = ${a}.source_council
              AND sib.source_chapter_key = ${a}.source_chapter_key AND sib.section_header = ${a}.section_header
              AND sib.quote_status IN ('exact', 'recovered') AND sib.quote_page > 0
              AND COALESCE(BTRIM(sib.council_quote), '') <> ''
              AND abs(sib.quote_page - ${a}.pdf_page) <= 12
            ORDER BY abs(sib.quote_page - ${a}.pdf_page), sib.quote_page LIMIT 1)
    END AS section_page`;
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
