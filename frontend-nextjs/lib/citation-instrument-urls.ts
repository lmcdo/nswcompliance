/**
 * Third-tier citation fallback: document_id -> instrument_registry.legislation_url.
 *
 * prior-art-checked: reuse not viable — instrument-currency/route.ts and
 * InstrumentCurrency.tsx (flagged by the prior-art guard) check instrument
 * version/staleness, not document_id -> legislation_url resolution for citation
 * links; grepped both for document_id/legislation_url/citation, zero matches.
 * scripts/_check_*_urls.py are one-off diagnostic scripts (not committed
 * capabilities) that inspect other url columns (R2, hub, registry), not this
 * document_id -> instrument_registry join. No existing consumer resolves
 * documents.r2_pdf_url/source_url or an instrument_registry join for
 * regulatory_provisions citations — confirmed by reading
 * app/api/provisions/for-property/route.ts (PROVISION_BASE_SELECT has no
 * documents join) and PageGroupedProvisions.tsx (only pdf_page_image_url and
 * dcp_chapter_registry-sourced chapterPdfUrls are consulted today).
 *
 * Read-only, code-level lookup — deliberately NOT a database write. 35 `documents`
 * rows have no r2_pdf_url or source_url (44 at prior measurement 2026-08-26, now
 * 52 as of 2026-08-27 — 17 more duplicate-extraction rows appeared for 7 SEPPs in
 * that window, see the flagged finding in ce-citation-wiring-and-cleanup-PROMPT.md
 * follow-up; those 17 are NOT in this map and must not be guessed into it).
 *
 * These 35 document ids were matched to instrument_registry.legislation_url by a
 * DETERMINISTIC name-derivation (strip _NSW_Legislation / _section_N / page-range
 * suffixes, drop parens, lowercase, then "<council>_lep_<year>" or
 * "sepp_<subname>_<year>") — re-verified 2026-08-27 against live instrument_registry,
 * exact same 35 as the 2026-08-26 measurement. Re-derive against instrument_registry
 * before trusting this list stale.
 *
 * Kept as a static map rather than a live join so a wrong match is a one-line,
 * reviewable diff to revert — never a production UPDATE on a 55,696-row table.
 * Do NOT add an entry here without it being the output of that deterministic
 * derivation. Never guess an EPI number or council URL into this file.
 */
export const INSTRUMENT_CITATION_URLS: Record<string, string> = {
  Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_101_150:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_201_250:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_251_288:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_51_100:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  Inner_West_Local_Environmental_Plan_2022__NSW_Legislation:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  Inner_West_Local_Environmental_Plan_2022__NSW_Legislation_1_50:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_0':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_1':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_11':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_12':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_13':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_14':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_15':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_16':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_17':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_18':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_19':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_20':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_21':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_22':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_23':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_24':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_26':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_27':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_28':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_29':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_3':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_30':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_4':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_5':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_6':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_7':
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
  // prior-art-checked: restoring the entry force-red-tested above; HousingSEPPEligibilityCard.tsx
  // and StateLevelControls.tsx read housing_sepp_standards.r2_pdf_url (a different, curated
  // 45-row table), not documents/instrument_registry — not reusable for this map.
  State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation:
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
};

/**
 * Resolve a citation link for a provision, in priority order:
 *   1. A per-page rendered image (pdf_page_image_url) — most precise, opens the exact page.
 *   2. The DCP chapter's registered PDF/council URL, keyed by source_chapter_key.
 *   3. This static instrument_registry-derived map, keyed by document_id — whole-of-instrument,
 *      not page-precise, and HTML (legislation.nsw.gov.au) rather than PDF.
 * Returns null if none apply — callers must not render a broken/dead link.
 */
export interface ResolvedCitation {
  url: string;
  /** 'image' and 'chapter' open a paginated PDF viewer; 'instrument' is a plain external link. */
  kind: 'image' | 'chapter' | 'instrument';
}

export function resolveCitationUrl(
  provision: { pdf_page_image_url?: string; pdf_page?: number; source_chapter_key?: string; document_id?: string },
  chapterPdfUrls: Record<string, string> | undefined
): ResolvedCitation | null {
  if (provision.pdf_page_image_url) {
    return { url: provision.pdf_page_image_url, kind: 'image' };
  }
  // Gating this on `pdf_page` (dropped 2026-09-01, Sol cross-review) meant a
  // provision with a real chapter match but no page number skipped the more
  // specific chapter URL and fell through to the coarser whole-of-instrument
  // link — the exact priority-order violation this module's own header
  // documents as forbidden. The page number is only needed for the #page=
  // anchor, which the caller now adds conditionally.
  const chapterUrl = provision.source_chapter_key
    ? chapterPdfUrls?.[provision.source_chapter_key]
    : undefined;
  if (chapterUrl) {
    return { url: chapterUrl, kind: 'chapter' };
  }
  const instrumentUrl = provision.document_id ? INSTRUMENT_CITATION_URLS[provision.document_id] : undefined;
  if (instrumentUrl) {
    return { url: instrumentUrl, kind: 'instrument' };
  }
  return null;
}
