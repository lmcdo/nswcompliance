/**
 * Which page a DCP rule's link opens, and what page number it shows.
 *
 * prior-art-checked: reuse not viable -- citation-display.ts decides whether a CLAUSE number is
 * shown (citation_status, migration 076); nothing decided whether the PAGE is the rule's.
 *
 * regulatory_provisions.page_check (migration 079, written by scripts/dcp_page_repair.py) says
 * whether pdf_page holds the rule. Measured 2026-09-26: 45% of served rules linked to the first
 * page of the AI reader's 12-page chunk. printed_page_label is the page number the council
 * prints on that page ("B5", "14-117", "4.1-2") -- what a reader of the printed plan looks for.
 *
 *   on_page / moved              -> link to that page; show the printed number, else "PDF page N"
 *   unresolved / not_found       -> the stored page does NOT hold the rule: open the document,
 *                                   no page anchor, "page not confirmed"
 *   NULL / too_short / no_source -> not checked: as before (link and "PDF page N")
 *
 * The anchor is always the PDF's own page index: that is what a browser's #page= counts.
 */

export interface PageFields {
  pdf_page?: number | null;
  printed_page_label?: string | null;
  page_check?: string | null;
}

const WRONG_PAGE = new Set(['unresolved', 'not_found']);
const CHECKED = new Set(['on_page', 'moved']);

/** The #page= anchor to open, or null when there is no page we can stand behind. */
export function pageAnchor(p: PageFields): number | null {
  if (p.page_check && WRONG_PAGE.has(p.page_check)) return null;
  return typeof p.pdf_page === 'number' && p.pdf_page > 0 ? p.pdf_page : null;
}

/** The page reference to print beside a rule, or null when it has none at all. */
export function pageLabel(p: PageFields): string | null {
  if (p.page_check && WRONG_PAGE.has(p.page_check)) return 'page not confirmed';
  const label = typeof p.printed_page_label === 'string' ? p.printed_page_label.trim() : '';
  if (label && p.page_check && CHECKED.has(p.page_check)) return `page ${label}`;
  const anchor = pageAnchor(p);
  return anchor ? `PDF page ${anchor}` : null;
}

/** A chapter URL with the rule's page anchor, when there is one we can stand behind. */
export function pageHref(url: string, p: PageFields): string {
  const anchor = pageAnchor(p);
  return anchor ? `${url}#page=${anchor}` : url;
}
