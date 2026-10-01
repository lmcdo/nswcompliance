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
 * is shown. A council DCP row that has not been checked yet (NULL, e.g. just published and
 * the re-check failed) is NOT shown: unchecked fails closed. Rows with no source_council
 * (LEP/SEPP) are outside this check and are served as before.
 */

const SHOWN = new Set(['proven', 'imprecise']);

export function citationIsShown(status?: string | null, sourceCouncil?: string | null): boolean {
  if (status == null) return !sourceCouncil;
  return SHOWN.has(status);
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
    // The code ends at the heading's end or at any non-alphanumeric character:
    // "# C4.9 Fences", "# C4.9: Fences", "# C4.9 – Fences" (cross-review, 2026-09-26).
    if (norm(heading.slice(0, i)) === want && (i === heading.length || !/[A-Za-z0-9]/.test(heading[i]))) {
      const title = heading.slice(i).replace(/^[\s:;,.\-–—]+/, '').trim();
      return title ? `# ${title}${rest}` : rest.replace(/^\n+/, '');
    }
  }
  return text;
}

/**
 * Drop the internal occurrence suffix from a label that is about to be shown.
 *
 * `dcp_extract_changed.diff_provisions` suffixes a repeated ref (`..._7_4 (a)~2`)
 * so two clauses the council prints under the same letter — section 7.4 restarts
 * (a)(b)(c) under a "Pedestrians" sub-heading — stop overwriting each other. That
 * suffix is OURS, for uniqueness; the council's document contains no clause
 * "7.4 (a)~2". `browse/section/route.ts` passes `ref_number` straight through as
 * the displayed label, and `citation_proof.split_ref` ignores the suffix entirely
 * (it reads `7_4 (a)~2` as section 7.4), so the row can be judged `proven` and the
 * invented reference rendered. That is the DQ-111 fabricated-clause-number class.
 *
 * The marker is a TILDE, not an underscore: section 3.16 is stored as `3_16`, so an
 * underscore suffix is indistinguishable from a real clause number and stripping it
 * would render section 3.16 as `3`. A tilde cannot occur in a section number.
 *
 * Stripping it shows both as the council's own `7.4 (a)`, which is imprecise where
 * a sub-heading restarts its list but is never untrue. Caught by the pre-push
 * cross-review, 2026-10-02.
 */
export function stripOccurrenceSuffix(label: string | null | undefined): string | null {
  if (typeof label !== 'string') return null;
  return label.replace(/~\d+$/, '');
}

/** The provision as served: clause label and code shown only when the page proves them. */
export function withServedCitation<T extends {
  citation_status?: string | null;
  source_council?: string | null;
  ref_number?: string | null;
  provision_text?: string | null;
}>(p: T, clauseLabel: string | null): T & { clause_label: string | null; citation_shown: boolean } {
  const shown = citationIsShown(p.citation_status, p.source_council);
  return {
    ...p,
    provision_text: shown ? p.provision_text : stripStoredCode(p.provision_text, p.ref_number),
    clause_label: shown ? stripOccurrenceSuffix(clauseLabel) : null,
    citation_shown: shown,
  };
}
