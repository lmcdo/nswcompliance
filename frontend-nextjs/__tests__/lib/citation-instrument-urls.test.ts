/**
 * INSTRUMENT_CITATION_URLS / resolveCitationUrl — third-tier citation fallback.
 *
 * Two things this must prove, per ce-citation-wiring-and-cleanup-PROMPT.md step 5:
 *  (a) the 35 deterministically-matched document ids resolve to a real legislation.nsw.gov.au URL
 *  (b) the documents that did NOT match (7 SEPPs still missing from instrument_registry, their
 *      2026-08-27 duplicate-extraction siblings, and two unrelated DCP-chapter ids) are absent —
 *      proving the map wasn't padded with a guess to make coverage look better.
 */
import {
  INSTRUMENT_CITATION_URLS,
  REGISTRY_INSTRUMENT_URLS,
  epiIdFromUrl,
  storedLepTextEpi,
  legislationAnchorUrl,
  resolveCitationUrl,
} from '@/lib/citation-instrument-urls';

const MATCHED_IDS = [
  'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50',
  'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_101_150',
  'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_201_250',
  'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_251_288',
  'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_51_100',
  'Inner_West_Local_Environmental_Plan_2022__NSW_Legislation',
  'Inner_West_Local_Environmental_Plan_2022__NSW_Legislation_1_50',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_0',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_1',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_11',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_12',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_13',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_14',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_15',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_16',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_17',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_18',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_19',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_20',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_21',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_22',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_23',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_24',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_26',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_27',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_28',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_29',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_3',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_30',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_4',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_5',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_6',
  'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_7',
  'State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation',
];

const UNMATCHED_IDS = [
  // Not LEP/SEPP instruments at all — no deterministic key applies.
  'Chapter_E2_Haberfield_Neighbourhood',
  'Inner_West_Ashfield_DCP_2016___Chapter_D___Precinct_Guidelines_with_IWLEP_2022_amendments_Nov_22',
  'LE9962_1',
  // 7 SEPPs with no instrument_registry row at all (need a human-verified EPI lookup) —
  // both the original naming and the 2026-08-27 duplicate-extraction naming.
  'State_Environmental_Planning_Policy_(Biodiversity_and_Conservation)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_Biodiversity_and_Conservation_2021__NSW_Legislation',
  'State_Environmental_Planning_Policy_(Industry_and_Employment)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_Industry_and_Employment_2021__NSW_Legislation',
  'State_Environmental_Planning_Policy_(Planning_Systems)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_Planning_Systems_2021__NSW_Legislation',
  'State_Environmental_Planning_Policy_(Primary_Production)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_Primary_Production_2021__NSW_Legislation',
  'State_Environmental_Planning_Policy_(Resilience_and_Hazards)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_Resilience_and_Hazards_2021__NSW_Legislation',
  'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation',
  'State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation',
  'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation',
  'State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation',
];

describe('INSTRUMENT_CITATION_URLS — matched set', () => {
  it('has exactly 35 entries', () => {
    expect(Object.keys(INSTRUMENT_CITATION_URLS)).toHaveLength(35);
  });

  it.each(MATCHED_IDS)('resolves %s to a legislation.nsw.gov.au URL', (id) => {
    expect(INSTRUMENT_CITATION_URLS[id]).toMatch(/^https:\/\/legislation\.nsw\.gov\.au\//);
  });
});

describe('INSTRUMENT_CITATION_URLS — unmatched set stays unmatched', () => {
  it.each(UNMATCHED_IDS)('does NOT contain a guessed entry for %s', (id) => {
    expect(INSTRUMENT_CITATION_URLS[id]).toBeUndefined();
  });
});

describe('resolveCitationUrl — priority order', () => {
  const chapterPdfUrls = { 'part-1-chapter': 'https://council.example/dcp.pdf' };

  it('prefers the per-page image URL over everything else', () => {
    const result = resolveCitationUrl(
      {
        pdf_page_image_url: 'https://r2.example/page-12.png',
        pdf_page: 12,
        source_chapter_key: 'part-1-chapter',
        document_id: 'State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation',
      },
      chapterPdfUrls
    );
    expect(result).toEqual({ url: 'https://r2.example/page-12.png', kind: 'image' });
  });

  it('falls back to the chapter URL when no page image exists', () => {
    const result = resolveCitationUrl(
      { pdf_page: 12, source_chapter_key: 'part-1-chapter', document_id: 'no-match' },
      chapterPdfUrls
    );
    expect(result).toEqual({ url: 'https://council.example/dcp.pdf', kind: 'chapter' });
  });

  it('resolves the chapter URL even when pdf_page is absent — Sol cross-review 2026-09-01', () => {
    // A provision with a real chapter match but no page number must still get
    // the more specific chapter link, not fall through to the coarser
    // whole-of-instrument map. Gating the chapter lookup on pdf_page silently
    // broke this: it returned 'instrument' here instead of 'chapter'.
    const result = resolveCitationUrl(
      { source_chapter_key: 'part-1-chapter', document_id: 'no-match' },
      chapterPdfUrls
    );
    expect(result).toEqual({ url: 'https://council.example/dcp.pdf', kind: 'chapter' });
  });

  it('falls back to the instrument_registry map when neither image nor chapter URL exists', () => {
    const result = resolveCitationUrl(
      { document_id: 'State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation' },
      undefined
    );
    expect(result).toEqual({
      url: 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
      kind: 'instrument',
    });
  });

  it('returns null when nothing resolves — never a guessed/broken link', () => {
    const result = resolveCitationUrl({ document_id: 'some-unmatched-document-id' }, undefined);
    expect(result).toBeNull();
  });

  it('returns null for a document with no id at all', () => {
    expect(resolveCitationUrl({}, undefined)).toBeNull();
  });
});

describe('REGISTRY_INSTRUMENT_URLS — no URL the document_id map does not already vouch for', () => {
  const vouched = new Set(Object.values(INSTRUMENT_CITATION_URLS));

  it('Housing SEPP and Inner West LEP match the document_id map exactly', () => {
    expect(vouched.has(REGISTRY_INSTRUMENT_URLS.sepp_housing_2021)).toBe(true);
    expect(vouched.has(REGISTRY_INSTRUMENT_URLS.inner_west_lep_2022)).toBe(true);
  });

  it('carries the zero-padded E&C id from the migration 010 seed, not epi-2008-572', () => {
    expect(REGISTRY_INSTRUMENT_URLS.sepp_exempt_complying_2008).toBe(
      'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572'
    );
  });

  it('has no Sustainable Buildings entry — that SEPP has no registry row', () => {
    expect(Object.keys(REGISTRY_INSTRUMENT_URLS).some((k) => /sustainable/i.test(k))).toBe(false);
  });
});

describe('legislationAnchorUrl', () => {
  const base = 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714';

  it('appends the provision anchor', () => {
    expect(legislationAnchorUrl(base, 'sec.24')).toBe(`${base}#sec.24`);
    expect(legislationAnchorUrl(base, 'sch.11')).toBe(`${base}#sch.11`);
  });

  it('replaces an existing fragment rather than stacking a second one', () => {
    expect(legislationAnchorUrl(`${base}#sec.1`, 'sec.5.10')).toBe(`${base}#sec.5.10`);
  });

  it('returns the bare instrument URL when no anchor is given', () => {
    expect(legislationAnchorUrl(`${base}#sec.1`, null)).toBe(base);
  });

  it('returns null with no base URL — never a dead "#sec.x" link', () => {
    expect(legislationAnchorUrl(undefined, 'sec.5.10')).toBeNull();
    expect(legislationAnchorUrl('', 'sec.5.10')).toBeNull();
  });
});

describe('storedLepTextEpi — which LEPs /api/lep/provisions may be asked about', () => {
  it('accepts the Inner West LEP 2022 URL in any view form', () => {
    expect(storedLepTextEpi('https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457')).toBe('epi-2022-0457');
    expect(storedLepTextEpi('https://legislation.nsw.gov.au/view/whole/html/inforce/current/EPI-2022-0457#sec.5.10')).toBe('epi-2022-0457');
  });

  it("rejects another council's LEP", () => {
    // Waverley LEP 2012 (epi-2012-0540, per lib/lep-local-provisions-mapping.ts)
    expect(storedLepTextEpi('https://legislation.nsw.gov.au/view/html/inforce/current/epi-2012-0540')).toBeNull();
  });

  it('rejects a missing or unparseable URL (fails closed)', () => {
    expect(storedLepTextEpi(undefined)).toBeNull();
    expect(storedLepTextEpi('https://legislation.nsw.gov.au/')).toBeNull();
  });

  it('does not match a longer EPI number that merely contains the id', () => {
    expect(epiIdFromUrl('https://x/epi-2022-04571')).toBeNull();
  });
});
