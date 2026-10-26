import {
  QUOTE_NOTE_CONFIRMED, QUOTE_NOTE_NOT_A_RULE, QUOTE_NOTE_UNCHECKED, QUOTE_NOTE_UNMATCHED,
  hasCouncilWords, isWithheld, QUOTE_NOTE_OUTSIDE, numbersUsable, quoteColumns, quoteNote, servedQuoteStatus, shownText, withCouncilWords,
} from '@/lib/council-quote';

const NB = { source_council: 'northern_beaches', source_chapter_key: 'g4-dee-why' };

describe("a council DCP rule shows the council's own words when a program copied them (migration 111)", () => {
  it("shows only the council's words, not the reader's rewording or our heading (Northern Beaches 130236)", () => {
    const p = {
      ...NB,
      provision_text: '# G4 C51 Public Transport\n\nIt is to accommodate the existing local and commuter bus networks.',
      council_quote: 'The interchange is to be capable of accommodating both the existing local and\ncommuter bus networks.',
      quote_status: 'recovered', quote_page: 134,
    };
    expect(shownText(p)).toBe(
      'The interchange is to be capable of accommodating both the existing local and\ncommuter bus networks.');
    expect(quoteNote(p)).toBe(QUOTE_NOTE_CONFIRMED);
  });

  it('keeps every line break as printed -- joining "Multi-\\nunit" would change the word', () => {
    const p = { ...NB, provision_text: 'x', quote_status: 'exact', quote_page: 3, council_quote: 'Multi-\nunit housing is permitted.\nSite area 450m2' };
    expect(shownText(p)).toBe('Multi-\nunit housing is permitted.\nSite area 450m2');
  });

  it('joins a label alone on its PDF line to the text printed beside it', () => {
    const p = { ...NB, provision_text: 'x', quote_status: 'exact', quote_page: 205,
      council_quote: '(a)\nNew buildings are to provide a minimum 6m\nrear setback.\n(b)\nSide setbacks are to be consistent with Table 3.' };
    expect(shownText(p)).toBe('(a) New buildings are to provide a minimum 6m\nrear setback.\n(b) Side setbacks are to be consistent with Table 3.');
  });

  it('withholds our words for a council rule not proven in its current plan, and keeps its numbers out (user, 2026-10-26)', () => {
    for (const quote_status of ['unconfirmed', null]) {
      const p = { ...NB, provision_text: 'Maximum height 9m', council_quote: null, quote_status };
      expect(isWithheld(p)).toBe(true);
      expect(shownText(p)).toBe(QUOTE_NOTE_UNMATCHED);
      expect(shownText(p)).not.toMatch(/9m/);
      expect(quoteNote(p)).toBeNull();
      expect(numbersUsable(p)).toBe(false);
    }
    const map = { ...NB, provision_text: 'Height 9m', council_quote: null, quote_status: 'not_a_control' };
    expect(isWithheld(map)).toBe(false);
    expect(shownText(map)).toBe('Height 9m');
    expect(quoteNote(map)).toBe(QUOTE_NOTE_NOT_A_RULE);
    expect(numbersUsable(map)).toBe(false);
  });

  it('keeps showing, marked as our reading, a council-named rule outside the check (no DCP chapter: inner_west LEP clauses)', () => {
    const lep = { source_council: 'inner_west', source_chapter_key: null, provision_text: 'Height 80m', council_quote: null, quote_status: null };
    expect(isWithheld(lep)).toBe(false);
    expect(shownText(lep)).toBe('Height 80m');
    expect(quoteNote(lep)).toBe(QUOTE_NOTE_OUTSIDE);
    expect(numbersUsable(lep)).toBe(false);
    // a proven failure is withheld whatever its chapter field says
    expect(isWithheld({ ...lep, quote_status: 'unconfirmed' })).toBe(true);
  });

  it('never serves a confirmed status without stored words (hollow), including a blank quote', () => {
    for (const council_quote of [null, '', ' \n ']) {
      const p = { ...NB, provision_text: 'Maximum height 9m', council_quote, quote_status: 'exact' };
      expect(hasCouncilWords(p)).toBe(false);
      expect(shownText(p)).toBe(QUOTE_NOTE_UNMATCHED);
      const served = { ...NB, provision_text: shownText(p), quote_status: servedQuoteStatus(p) };
      expect(served.quote_status).toBeNull();
      expect(shownText(served)).toBe(QUOTE_NOTE_UNMATCHED);   // idempotent on the client
      expect(numbersUsable(served)).toBe(false);
    }
  });

  it('serves a confirmed status unchanged when the words are stored', () => {
    expect(servedQuoteStatus({ ...NB, council_quote: 'Words', quote_status: 'recovered', quote_page: 9 })).toBe('recovered');
    // the words without the page they were copied from are not served as the council's
    expect(servedQuoteStatus({ ...NB, council_quote: 'Words', quote_status: 'exact', quote_page: null })).toBeNull();
    expect(servedQuoteStatus({ ...NB, council_quote: null, quote_status: 'unconfirmed' })).toBe('unconfirmed');
  });

  it('does not take a unit printed alone ("m2") for a label', () => {
    const p = { ...NB, provision_text: 'x', quote_status: 'exact', quote_page: 4, council_quote: 'Site area\nm2\n450' };
    expect(shownText(p)).toBe('Site area\nm2\n450');
  });

  it('serves a row once: council words in, the quote itself out, status normalised, extracted text cleaned only', () => {
    const row = { id: 1, ...NB, provision_text: '  junk header\nReworded', council_quote: 'Council words', quote_status: 'exact', quote_page: 7 };
    const served = withCouncilWords(row, (t) => (t ?? '').replace('junk header\n', '').trim());
    expect(served).toEqual({ id: 1, ...NB, provision_text: 'Council words', quote_status: 'exact', quote_page: 7 });
    expect('council_quote' in served).toBe(false);
    const unconfirmed = withCouncilWords({ ...row, council_quote: null, quote_status: 'unconfirmed', quote_page: null },
      (t) => (t ?? '').replace('junk header\n', '').trim());
    expect(unconfirmed.provision_text).toBe(QUOTE_NOTE_UNMATCHED);
    expect(quoteColumns('p')).toBe('p.council_quote, p.quote_page, p.quote_status, p.source_chapter_key');
  });

  it('leaves LEP and SEPP rules (no council) as they were', () => {
    const p = { provision_text: 'Clause 4.3 height', source_council: null };
    expect(shownText(p)).toBe('Clause 4.3 height');
    expect(quoteNote(p)).toBeNull();
    expect(numbersUsable(p)).toBe(true);
  });
});

describe('the pointer shown for a withheld council rule names the page shown beside it', () => {
  it('uses the printed page label when the page is located', () => {
    const p = { ...NB, provision_text: 'Maximum height 9m', quote_status: 'unconfirmed', pdf_page: 40,
      page_check: 'on_page', printed_page_label: '12' };
    expect(shownText(p)).toBe("Wording not shown: we could not match it to the council's current plan — read it on page 12 of the council's plan");
  });

  it('says PDF page when no printed label is known', () => {
    const p = { ...NB, provision_text: 'x', quote_status: null, pdf_page: 40, page_check: 'on_page' };
    expect(shownText(p)).toBe("Wording not shown: we could not match it to the council's current plan — read it on PDF page 40 of the council's plan");
  });

  it('names no page when the page was not located', () => {
    const p = { ...NB, provision_text: 'x', quote_status: 'unconfirmed', pdf_page: 40, page_check: 'not_found' };
    expect(shownText(p)).toBe(QUOTE_NOTE_UNMATCHED);
  });

  it('no longer says the old "Not yet checked" wording anywhere', () => {
    expect(QUOTE_NOTE_UNCHECKED).not.toMatch(/Not yet checked/);
    expect(QUOTE_NOTE_UNMATCHED).not.toMatch(/Not matched/);
  });
});
