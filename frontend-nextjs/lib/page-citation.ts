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
 *   on_page / moved   -> link to that page; show the printed number, else "PDF page N"
 *   anything else on a council DCP row, INCLUDING not checked yet -> open the document with no
 *                        page anchor, "page not located". Unchecked fails closed, as clause
 *                        numbers do (citation-display.ts): a failed post-publish check must
 *                        not leave the reader's chunk-start page linked as if it were the rule's.
 *   rows outside this check (no source_council: LEP/SEPP) -> as before.
 *
 * The anchor is always the PDF's own page index: that is what a browser's #page= counts.
 */

export interface PageFields {
  pdf_page?: number | null;
  pdf_printed_page?: number | null;
  printed_page_label?: string | null;
  page_check?: string | null;
  source_council?: string | null;
}

const LOCATED = new Set(['on_page', 'moved']);
export const PAGE_NOT_LOCATED = 'page not located';

/** A council DCP row whose page was not shown to hold the rule. */
function unlocated(p: PageFields): boolean {
  if (p.page_check) return !LOCATED.has(p.page_check);
  return Boolean(p.source_council);
}

function positive(n: number | null | undefined): number | null {
  return typeof n === 'number' && n > 0 ? n : null;
}

/** The #page= anchor to open, or null when there is no page we can stand behind. */
export function pageAnchor(p: PageFields): number | null {
  return unlocated(p) ? null : positive(p.pdf_page);
}

/** The page reference to print beside a rule, or null when it has none at all. */
export function pageLabel(p: PageFields): string | null {
  if (unlocated(p)) return positive(p.pdf_page) ? PAGE_NOT_LOCATED : null;
  const label = typeof p.printed_page_label === 'string' ? p.printed_page_label.trim() : '';
  if (label) return `page ${label}`;
  // Rows outside the page check keep the page they always cited.
  const page = p.page_check ? positive(p.pdf_page) : positive(p.pdf_printed_page) ?? positive(p.pdf_page);
  return page ? `PDF page ${page}` : null;
}

/** A chapter URL with the rule's page anchor, when there is one we can stand behind. */
export function pageHref(url: string, p: PageFields): string {
  const anchor = pageAnchor(p);
  return anchor ? `${url}#page=${anchor}` : url;
}
