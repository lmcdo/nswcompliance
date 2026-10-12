import {
  QUOTE_NOTE_CONFIRMED, QUOTE_NOTE_NOT_A_RULE, QUOTE_NOTE_UNCHECKED, QUOTE_NOTE_UNMATCHED,
  hasCouncilWords, numbersUsable, quoteNote, servedQuoteStatus, shownText,
} from '@/lib/council-quote';

const NB = { source_council: 'northern_beaches' };

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

  it('says what the check found for a council rule whose words are not confirmed, and keeps its numbers out', () => {
    const cases: [string | null, string][] = [
      ['unconfirmed', QUOTE_NOTE_UNMATCHED], ['not_a_control', QUOTE_NOTE_NOT_A_RULE], [null, QUOTE_NOTE_UNCHECKED]];
    for (const [quote_status, note] of cases) {
      const p = { ...NB, provision_text: 'Maximum height 9m', council_quote: null, quote_status };
      expect(shownText(p)).toBe('Maximum height 9m');
      expect(quoteNote(p)).toBe(note);
      expect(numbersUsable(p)).toBe(false);
    }
  });

  it('never serves a confirmed status without stored words (hollow), including a blank quote', () => {
    for (const council_quote of [null, '', ' \n ']) {
      const p = { ...NB, provision_text: 'Maximum height 9m', council_quote, quote_status: 'exact' };
      expect(hasCouncilWords(p)).toBe(false);
      expect(shownText(p)).toBe('Maximum height 9m');
      const served = { ...NB, provision_text: shownText(p), quote_status: servedQuoteStatus(p) };
      expect(served.quote_status).toBeNull();
      expect(quoteNote(served)).toBe(QUOTE_NOTE_UNCHECKED);
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

  it('leaves LEP and SEPP rules (no council) as they were', () => {
    const p = { provision_text: 'Clause 4.3 height', source_council: null };
    expect(shownText(p)).toBe('Clause 4.3 height');
    expect(quoteNote(p)).toBeNull();
    expect(numbersUsable(p)).toBe(true);
  });
});
