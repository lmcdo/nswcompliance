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

/**
 * Machine-proven citation: a script proved the clause (citation_status) or the page
 * (page_check) against the source document. Mirrors DQ-145 in scripts/dq_probe_live.py:
 *   COALESCE(citation_status,'') IN ('proven','imprecise') OR COALESCE(page_check,'') IN ('on_page','moved')
 * 'read_by_person' is a person's reading, not a script's, so it does not count.
 * tests/test_citation_checked_parity.py (and the jest parity test) fail if the two drift.
 */
export const CITATION_PROVEN_STATUSES = ['proven', 'imprecise'] as const;
export const CITATION_PROVEN_PAGE_CHECKS = ['on_page', 'moved'] as const;

/** Whether a served rule's citation is machine-proven. Missing columns = not checked (fail closed). */
export function isCitationChecked(row?: { citation_status?: unknown; page_check?: unknown } | null): boolean {
  if (!row) return false;
  const status = typeof row.citation_status === 'string' ? row.citation_status : '';
  const check = typeof row.page_check === 'string' ? row.page_check : '';
  return (CITATION_PROVEN_STATUSES as readonly string[]).includes(status)
    || (CITATION_PROVEN_PAGE_CHECKS as readonly string[]).includes(check);
}

export const CITATION_UNCHECKED_LABEL = 'Citation not yet checked';
export const CITATION_UNCHECKED_TOOLTIP =
  'No automated page or clause match is recorded for this rule. Compare it with the source document.';

/**
 * The "<instrument> — <clause>" badge text, or null when we hold neither.
 *
 * Same principle as citationIsShown below, applied to the LEP/SEPP cards: name
 * only what the source named. Until 2026-10-06 the callers defaulted the clause
 * in their own signatures (`legislativeClause = 'Clause 2.3'` in
 * LandUseZoningCard, `= 'Clause 4.1'` in MinimumLotSizeCard) and the instrument
 * in the badge (`epiName || 'Local Environmental Plan'`, and in one case
 * `|| 'Inner West Local Environmental Plan 2022'` for a property in any council).
 * 2.3 and 4.1 are the usual zoning and minimum-lot-size clauses in NSW LEPs,
 * which is precisely why a wrong one would never have looked wrong.
 *
 * Returning null rather than a placeholder lets the caller drop the badge
 * entirely: a badge reading "Local Environmental Plan" names no instrument and
 * cites no clause, so it asserts authority it does not have.
 */
/**
 * Trimmed text, or null — for a value that came from an UNTYPED source.
 *
 * `planningLayers` and the heritage record are `any`, so a declared
 * `string | null` is a statement of intent, not of runtime. A numeric
 * 'EPI Name' would make `.trim()` throw and take the whole page down, which is a
 * worse failure than the fabricated citation this module exists to prevent. The
 * QA gate blocked a push on exactly this, 2026-10-06, at three call sites.
 */
export function asTrimmedString(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed === '' ? null : trimmed;
}

export function instrumentClauseLabel(epiName?: unknown, clause?: unknown): string | null {
  const instrument = asTrimmedString(epiName);
  const reference = asTrimmedString(clause);
  if (instrument && reference) return `${instrument} — ${reference}`;
  return instrument ?? reference;
}

const NUM = String.raw`\d+[A-Z]{0,2}(?:\.\d+[A-Z]{0,2})*(?:\s*\([A-Za-z0-9]{1,4}\))*`;
const DIVISION = String.raw`(?:schedule|sch|chapter|part|division|div)\.?\s+\d+[A-Z]{0,2}`;
const CLAUSE_WORD = String.raw`(?:clause|cl|section|sec|s)\.?\s*`;
const STATE_CLAUSE_RE = new RegExp(
  String.raw`^(?:${DIVISION}(?:\s*,?\s*${DIVISION})*(?:\s*,?\s*(?:${CLAUSE_WORD})?${NUM})?|(?:${CLAUSE_WORD})${NUM}|${NUM})$`,
  'i',
);

/**
 * A state-law (SEPP/LEP) reference as served, or null.
 *
 * state rows (source_council NULL) carry `ref_number` values that are often OUR
 * internal ids (`provision_2344`, `layout_no`, uuids); `section_header` is NULL, so
 * nothing else says what they are. Shown as-is they look like the law's clause number
 * -- the DQ-111 fabricated-citation class. Only a string shaped like a real NSW
 * clause/section/schedule reference ("2.30AB", "3A.12", "cl 5.10",
 * "Schedule 2 cl 6", "s 87") is shown; otherwise the caller shows the instrument name
 * and its legislation link only. Shape is checked, not truth: a real-looking value
 * still depends on the extractor. A bare integer longer than 3 digits is refused
 * (reads as a row id).
 */
// One standard printed word for word in several codes: every place is cited, none picked (DQ-145 step 2,
// 2026-10-17): "Section 3.29(3); same words in 3C.32(3), 3D.53(4)". Mirrors sepp_ref_fix.SAME_WORDS_RE.
const SAME_WORDS = '; same words in ';
const PLACE = String.raw`(?!\d{4,}(?:,|$))(?:${DIVISION}(?:\s*,?\s*${DIVISION})*\s*,?\s*(?:${CLAUSE_WORD})?${NUM}|(?:${CLAUSE_WORD})?${NUM})`;
const SAME_WORDS_RE = new RegExp(String.raw`^(.+?); same words in ${PLACE}(?:,\s*${PLACE})*$`, 'i');

export function stateClauseLabel(ref?: unknown): string | null {
  const s = asTrimmedString(ref);
  const multi = s && s.length <= 200 && s.toLowerCase().includes(SAME_WORDS) ? SAME_WORDS_RE.exec(s) : null;
  if (multi) return stateClauseLabel(multi[1]) === multi[1] ? s : null;
  if (!s || s.length > 60) return null;
  if (/provision|layout|_|__|~/i.test(s)) return null;
  if (/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(s)) return null;
  if (/^\d{4,}$/.test(s)) return null;
  return STATE_CLAUSE_RE.test(s) ? s : null;
}

/**
 * A reference for a row known only by its document id. Fails closed: the stored
 * reference passes through only when the id is clearly a council DCP; every other
 * or unrecognised id goes through stateClauseLabel.
 */
export function referenceForDocument(ref: unknown, documentId?: string | null): string | null {
  const id = documentId ?? '';
  const isCouncilDcp = /dcp|development_control/i.test(id) && !/sepp|state_environmental|lep|environmental_plan/i.test(id);
  return isCouncilDcp ? asTrimmedString(ref) : stateClauseLabel(ref);
}

/** Council rows keep their proven label; state rows only a well-formed one. */
export function servedClauseLabel(label: string | null | undefined, sourceCouncil?: string | null): string | null {
  if (sourceCouncil) return asTrimmedString(label);
  return stateClauseLabel(label);
}

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
  page_check?: string | null;
}>(p: T, clauseLabel: string | null): T & { clause_label: string | null; citation_shown: boolean; citation_checked: boolean } {
  const shown = citationIsShown(p.citation_status, p.source_council);
  return {
    ...p,
    provision_text: shown ? p.provision_text : stripStoredCode(p.provision_text, p.ref_number),
    clause_label: shown ? servedClauseLabel(stripOccurrenceSuffix(clauseLabel), p.source_council) : null,
    citation_shown: shown,
    citation_checked: isCitationChecked(p),
  };
}
