/**
 * Show a DCP clause number only when it is printed on the council's page.
 *
 * prior-art-checked: reuse not viable -- citation-instrument-urls.ts resolves a
 * document to its legislation URL, and services/clause_citation_inline.py is an
 * AutoSchemaKG text lookup; neither decides whether a served clause NUMBER is the
 * council's. The verdict itself is scripts/citation_proof.py, stored per row.
 *
 * regulatory_provisions.citation_status (migration 076) holds the page check's verdict,
 * written by scripts/dcp_citation_status.py. Clause numbers were written by the AI
 * extractor and never checked (DQ-111); an unproven one must not be served as the
 * council's. The page is still shown, so the citation stays true: "page 91" instead of a
 * guessed "C4.9". 'imprecise' is true but coarse (every piece printed above the rule) and
 * is shown. NULL = not checked (LEP/SEPP rows, or not yet run) and is served as before.
 */

const SHOWN = new Set(['proven', 'imprecise']);

export function citationIsShown(status?: string | null): boolean {
  return status == null || SHOWN.has(status);
}

const norm = (s: string) => s.toLowerCase().replace(/[\s._]+/g, '');

/**
 * Remove the stored code from the provision's own "# <code> <title>" first line.
 * Only the exact stored code is removed; any other first line is left as it is.
 */
export function stripStoredCode(text: string | null | undefined, refNumber: string | null | undefined): string {
  if (typeof text !== 'string' || typeof refNumber !== 'string') return typeof text === 'string' ? text : '';
  if (!text.startsWith('#')) return text;
  const want = norm(refNumber?.split('__').pop() ?? '');
  if (!want) return text;
  const nl = text.indexOf('\n');
  const first = nl === -1 ? text : text.slice(0, nl);
  const rest = nl === -1 ? '' : text.slice(nl);
  const heading = first.replace(/^#+/, '').trim();
  for (let i = 1; i <= heading.length; i++) {
    if (norm(heading.slice(0, i)) === want && (i === heading.length || heading[i] === ' ')) {
      const title = heading.slice(i).trim();
      return title ? `# ${title}${rest}` : rest.replace(/^\n+/, '');
    }
  }
  return text;
}

/** The provision as served: clause label and code shown only when the page proves them. */
export function withServedCitation<T extends {
  citation_status?: string | null;
  ref_number?: string | null;
  provision_text?: string | null;
}>(p: T, clauseLabel: string | null): T & { clause_label: string | null; citation_shown: boolean } {
  const shown = citationIsShown(p.citation_status);
  return {
    ...p,
    provision_text: shown ? p.provision_text : stripStoredCode(p.provision_text, p.ref_number),
    clause_label: shown ? clauseLabel : null,
    citation_shown: shown,
  };
}
