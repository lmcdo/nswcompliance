/**
 * SEPP (Housing) 2021 parking cards -> provision ids.
 *
 * Gate B of the STEP 5 AMENDMENT: each card renders a rate traced to a
 * `regulatory_provisions` id, asserted here. Gate A (deleting the hardcoded strings
 * from StateLevelControls.tsx) is satisfiable by deleting the six cards; this file is
 * what stops that, so these assertions must name ids and pages, not just "not empty".
 *
 * Every fixture row below is the verbatim live row, dumped 2026-10-05 from
 * `regulatory_provisions` (ids 40310 / 40570 / 40604-40606 / 40722-40723 / 41014-41015),
 * newlines and em dashes included. Hand-written fixtures would prove the resolver
 * matches hand-written fixtures.
 */
import {
  SEPP_PARKING_CARDS,
  HOUSING_SEPP_DOCUMENT_ID,
  UNSOURCED_CARDS,
  allParkingMatchPatterns,
  ilikeMatches,
  resolveParkingCards,
  type ParkingProvisionRow,
} from '@/lib/sepp-parking-cards';

const DOC = HOUSING_SEPP_DOCUMENT_ID;

const row = (
  id: number,
  ref_number: string,
  pdf_page: number,
  provision_text: string,
): ParkingProvisionRow => ({
  id,
  ref_number,
  pdf_page,
  citation_status: null,
  provision_text,
  document_id: DOC,
});

/** The nine live rows the nine predicates resolved to, in page order. */
const LIVE_ROWS: ParkingProvisionRow[] = [
  row(40310, 'provision_187', 11,
    '(i) for development on land within an accessible area—0.2 parking spaces for each boarding room, (ii) otherwise—0.5 parking spaces for each boarding room,'),
  row(40570, 'provision_550', 32,
    '(i) for development on land in an accessible area—0.2 parking spaces for each private room, or (ii) otherwise—0.5 parking spaces for each private room,'),
  row(40604, 'provision_596', 35,
    '(d) for development carried out wholly or partly on land in a designated Sydney local government area—'),
  row(40605, 'provision_597', 35,
    '(i) for land within an accessible area—0.2 parking spaces for each dwelling, or   \n(ii) otherwise—0.5 parking spaces for each dwelling, or   \n(iii) if a relevant planning instrument specifies a requirement for a lower number of parking spaces—the lower number specified in the relevant planning instrument,'),
  row(40606, 'provision_598', 36,
    '(e) if paragraph (d) does not apply—at least the number of parking spaces required under the relevant development control plan or local environmental plan for a residential flat building.'),
  row(40722, 'provision_765', 47,
    '(j) for a development application made by, or made by a person jointly with, a social housing provider or Landcom—at least 1 parking space for every 5 dwellings,'),
  row(40723, 'provision_766', 47,
    '(k) if paragraph (j) does not apply—at least 0.5 parking spaces for each bedroom.'),
  row(41014, 'provision_1188', 72,
    '(2) Development to which section 156 applies must provide the following number of parking spaces for each affordable housing dwelling required under that section—'),
  row(41015, 'provision_1189', 72,
    '(a) for each dwelling containing 1 bedroom—0.4 parking space, (b) for each dwelling containing 2 bedrooms—0.5 parking space, (c) for each dwelling containing 3 or more bedrooms—1 parking space.'),
];

const byKey = (rows: ParkingProvisionRow[]) =>
  Object.fromEntries(resolveParkingCards(rows).map((card) => [card.key, card]));

describe('ilikeMatches', () => {
  it('spans the newlines inside provision 40605, as ILIKE does', () => {
    const text = LIVE_ROWS.find((r) => r.id === 40605)!.provision_text;
    expect(text).toContain('\n');
    expect(ilikeMatches(text, '%0.2 parking spaces for each dwelling%')).toBe(true);
    expect(ilikeMatches(text, '%accessible area%lower number specified%')).toBe(true);
  });

  it('treats "." as a literal, as ILIKE does', () => {
    // '0.2' must not match '052'. A regex-style '.' here would make the
    // boarding-house and co-living predicates interchangeable.
    expect(ilikeMatches('052 parking spaces', '%0.2 parking spaces%')).toBe(false);
    expect(ilikeMatches('0.2 parking spaces', '%0.2 parking spaces%')).toBe(true);
  });

  it('is case-insensitive and anchored', () => {
    expect(ilikeMatches('0.2 PARKING spaces for each boarding room', '%for each boarding room%')).toBe(true);
    expect(ilikeMatches('for each boarding room and more', 'for each boarding room')).toBe(false);
  });
});

describe('the card registry itself', () => {
  it('covers exactly the six cards on the SEPP tab', () => {
    expect(SEPP_PARKING_CARDS.map((c) => c.key)).toEqual([
      'boarding_house',
      'co_living',
      'build_to_rent',
      'in_fill_affordable',
      'seniors_independent_living',
      'tod_affordable',
    ]);
  });

  it('asks for nine provisions in one round trip', () => {
    const patterns = allParkingMatchPatterns();
    expect(patterns).toHaveLength(9);
    expect(new Set(patterns).size).toBe(9);
  });

  it('records the id and page each predicate resolved to, so a drift is a diff', () => {
    // Not decoration: `verifiedProvisionId` is what the assertions below compare
    // against, and what a reviewer checks when a predicate stops matching.
    const verified = SEPP_PARKING_CARDS.flatMap((c) =>
      c.refs.map((r) => [r.verifiedProvisionId, r.verifiedPdfPage]));
    expect(verified).toEqual([
      [40310, 11],
      [40570, 32],
      [40604, 35], [40605, 35], [40606, 36],
      [40722, 47], [40723, 47],
      [41014, 72], [41015, 72],
    ]);
  });

  it('never presents a clause number as database-sourced', () => {
    // No statewide row has a populated citation_status, so every anchor here is a
    // hand-verified label on a link. The two that could not be verified are null.
    const anchors = Object.fromEntries(
      SEPP_PARKING_CARDS.map((c) => [c.key, c.legislationAnchor]));
    expect(anchors.in_fill_affordable).toBeNull();
    expect(anchors.tod_affordable).toBeNull();
    for (const card of SEPP_PARKING_CARDS) {
      resolveParkingCards(LIVE_ROWS)
        .filter((r) => r.key === card.key && r.resolved)
        .forEach((r) => {
          if (r.resolved) r.provisions.forEach((p) => expect(p.citationProven).toBe(false));
        });
    }
  });
});

describe('resolveParkingCards, against the live rows', () => {
  const cards = byKey(LIVE_ROWS);

  it.each([
    ['boarding_house', [{ id: 40310, page: 11, role: 'rate' }]],
    ['co_living', [{ id: 40570, page: 32, role: 'rate' }]],
    ['build_to_rent', [
      { id: 40604, page: 35, role: 'condition' },
      { id: 40605, page: 35, role: 'rate' },
      { id: 40606, page: 36, role: 'fallback' },
    ]],
    ['seniors_independent_living', [
      { id: 40722, page: 47, role: 'rate' },
      { id: 40723, page: 47, role: 'rate' },
    ]],
    ['tod_affordable', [
      { id: 41014, page: 72, role: 'lead_in' },
      { id: 41015, page: 72, role: 'rate' },
    ]],
  ] as const)('%s traces to its provision ids and pages', (key, expected) => {
    const card = cards[key];
    expect(card.resolved).toBe(true);
    if (!card.resolved) return;
    expect(card.provisions.map((p) => ({ id: p.provisionId, page: p.pdfPage, role: p.role })))
      .toEqual(expected);
  });

  it('quotes the instrument verbatim — no rate is synthesised', () => {
    const card = cards.build_to_rent;
    expect(card.resolved).toBe(true);
    if (!card.resolved) return;
    const texts = card.provisions.map((p) => p.text);
    // The flat per-dwelling rate the instrument states, its LGA condition, and the
    // council-rate fallback. The card this replaced showed per-bedroom tiers, which
    // appear nowhere in s74.
    expect(texts[1]).toContain('0.2 parking spaces for each dwelling');
    expect(texts[1]).toContain('0.5 parking spaces for each dwelling');
    expect(texts[1]).not.toMatch(/containing 1 bedroom/);
    expect(texts[0]).toContain('designated Sydney local government area');
    expect(texts[2]).toContain('development control plan or local environmental plan');
  });

  it('states no rate for in-fill affordable housing, and says only what was measured', () => {
    const card = cards.in_fill_affordable;
    expect(card.resolved).toBe(false);
    if (card.resolved) return;
    expect(card.reason).toBe('unsourced');
    expect(card.message).toBe(UNSOURCED_CARDS.in_fill_affordable);
    // The rate this card used to show was the build-to-rent rate from s74.
    expect(card.message).not.toMatch(/0\.[0-9]/);
    // It must not name the source that sets the rate instead. The instrument in force
    // could not be read, so "set by the council DCP" is a conclusion nothing here
    // supports, and the control could sit in an LEP. Sol HIGH/liability, 2026-10-05.
    expect(card.message).not.toMatch(/is set by/i);
    expect(card.message).not.toMatch(/development control plan\b(?!.*apply)/i);
    expect(card.message).toMatch(/was found in the stored instrument/);
  });

  it('resolves five cards and leaves one unsourced — the gate-B count', () => {
    const resolved = resolveParkingCards(LIVE_ROWS).filter((c) => c.resolved);
    expect(resolved).toHaveLength(5);
    expect(resolveParkingCards(LIVE_ROWS).filter((c) => !c.resolved)).toHaveLength(1);
  });
});

describe('fail-closed behaviour', () => {
  it('reports a card unmatched rather than partially — a rate without its condition', () => {
    // Drop s74's LGA condition (40604) and keep the rate. The rate alone is true of
    // the text and wrong about the law, so the card must not render.
    const withoutCondition = LIVE_ROWS.filter((r) => r.id !== 40604);
    const card = byKey(withoutCondition).build_to_rent;
    expect(card.resolved).toBe(false);
    if (card.resolved) return;
    expect(card.reason).toBe('unmatched');
    expect(card.missing).toHaveLength(1);
    expect(card.message).toMatch(/1 of 3 provisions/);
  });

  it('distinguishes "the law has no such standard" from "our copy lost it"', () => {
    const none = byKey([]);
    expect(none.in_fill_affordable.resolved).toBe(false);
    expect(none.boarding_house.resolved).toBe(false);
    if (none.in_fill_affordable.resolved || none.boarding_house.resolved) return;
    expect(none.in_fill_affordable.reason).toBe('unsourced');
    expect(none.boarding_house.reason).toBe('unmatched');
  });

  it('returns no provisions at all when the query returns nothing', () => {
    // A `return []` implementation of the route must not look like a clean answer.
    const cards = resolveParkingCards([]);
    expect(cards.every((c) => !c.resolved)).toBe(true);
    expect(cards.filter((c) => !c.resolved && c.reason === 'unmatched')).toHaveLength(5);
  });

  it('ignores a row from the other extraction generation', () => {
    // The split generation carries the same wording with no pdf_page (this is live row
    // 15472, the s108(2)(k) seniors rate). Handed FIRST, it is what `find` would reach
    // for, and the card would report a provision id with no page — the one citation
    // these cards can prove. The document-id scope, not row order, is what excludes it.
    const splitGeneration: ParkingProvisionRow = {
      id: 15472,
      ref_number: '108(2)(k)',
      pdf_page: null,
      citation_status: null,
      provision_text: 'if paragraph (j) does not apply—at least 0.5 parking spaces for each bedroom',
      document_id: 'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_13',
    };
    const card = byKey([splitGeneration, ...LIVE_ROWS]).seniors_independent_living;
    expect(card.resolved).toBe(true);
    if (!card.resolved) return;
    expect(card.provisions.map((p) => p.provisionId)).toEqual([40722, 40723]);
    expect(card.provisions.map((p) => p.pdfPage)).not.toContain(null);
  });

  it('refuses to pick between two paragraphs with the same wording', () => {
    // Sol HIGH/silent-failure, 2026-10-05: the resolver took the FIRST match, so an
    // amendment adding a second paragraph containing "0.2 parking spaces for each
    // dwelling" would have been served as the build-to-rent rate by row order alone.
    const amendmentDuplicate = row(99001, 'provision_9001', 35,
      '(i) for land within an accessible area—0.2 parking spaces for each dwelling, or (ii) otherwise—nil,');
    const card = byKey([amendmentDuplicate, ...LIVE_ROWS]).build_to_rent;
    expect(card.resolved).toBe(false);
    if (card.resolved) return;
    expect(card.reason).toBe('ambiguous');
    expect(card.ambiguous).toEqual([
      { match: '%0.2 parking spaces for each dwelling%', provisionIds: [99001, 40605] },
    ]);
    expect(card.message).toMatch(/match more than one paragraph/);
  });

  it('will not resolve a paragraph that carries no page', () => {
    // Sol MEDIUM/null-guard, 2026-10-05. The page is the entire citation: no current
    // statewide row has a populated citation_status, so a rate with no page is a rate
    // we cannot say where we read.
    const pageless = LIVE_ROWS.map((r) => (r.id === 40310 ? { ...r, pdf_page: null } : r));
    const card = byKey(pageless).boarding_house;
    expect(card.resolved).toBe(false);
    if (card.resolved) return;
    expect(card.reason).toBe('uncited');
    expect(card.uncited).toEqual([
      { match: '%parking spaces for each boarding room%', provisionId: 40310 },
    ]);
    expect(card.message).toMatch(/carry no page in the stored instrument/);
  });

  it('reports ambiguity ahead of a missing page, and both ahead of a missing row', () => {
    // Most-wrong first: ambiguity is the state in which a WRONG paragraph would be
    // served. All three diagnostics are carried either way so none masks the others.
    const rows = LIVE_ROWS
      .filter((r) => r.id !== 40604)                                        // -> missing
      .map((r) => (r.id === 40606 ? { ...r, pdf_page: null } : r))          // -> uncited
      .concat(row(99002, 'provision_9002', 35,
        '(i) for land within an accessible area—0.2 parking spaces for each dwelling, or (ii) otherwise—nil,'));
    const card = byKey(rows).build_to_rent;
    expect(card.resolved).toBe(false);
    if (card.resolved) return;
    expect(card.reason).toBe('ambiguous');
    expect(card.ambiguous).toHaveLength(1);
    expect(card.uncited).toHaveLength(1);
    expect(card.missing).toHaveLength(1);
  });

  it('resolves nothing at all if only the other generation is in scope', () => {
    // Forcing the guard's failure: a result set made entirely of split-generation rows
    // must leave every card unresolved, not quietly serve pageless citations.
    const splitOnly: ParkingProvisionRow[] = LIVE_ROWS.map((r) => ({
      ...r,
      pdf_page: null,
      document_id: 'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_13',
    }));
    expect(resolveParkingCards(splitOnly).filter((c) => c.resolved)).toHaveLength(0);
  });
});
