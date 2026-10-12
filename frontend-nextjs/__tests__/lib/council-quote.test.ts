import {
  QUOTE_NOTE_CONFIRMED, QUOTE_NOTE_UNCHECKED, hasCouncilWords, numbersUsable, quoteNote, servedQuoteStatus,
  shownText,
} from '@/lib/council-quote';

const NB = { source_council: 'northern_beaches' };

describe("a council DCP rule shows the council's own words when a program copied them (migration 111)", () => {
  it("shows the council's words, not the reader's rewording (Northern Beaches 130236)", () => {
    const p = {
      ...NB,
      provision_text: '# G4 C51 Public Transport\n\nIt is to accommodate the existing local and commuter bus networks.',
      council_quote: 'The interchange is to be capable of accommodating both the existing local and\ncommuter bus networks.',
      quote_status: 'recovered',
    };
    expect(shownText(p)).toBe(
      '# G4 C51 Public Transport\n\nThe interchange is to be capable of accommodating both the existing local and commuter bus networks.');
    expect(quoteNote(p)).toBe(QUOTE_NOTE_CONFIRMED);
  });

  it('keeps a label on its own PDF line with its text, and starts each labelled item on a new line', () => {
    const p = { ...NB, provision_text: 'x', quote_status: 'exact',
      council_quote: '(a)\nNew buildings are to provide a minimum 6m\nrear setback.\n(b)\nSide setbacks are to be consistent with Table 3.' };
    expect(shownText(p)).toBe('(a) New buildings are to provide a minimum 6m rear setback.\n(b) Side setbacks are to be consistent with Table 3.');
  });

  it('does not take a word that ends a sentence for a label', () => {
    const p = { ...NB, provision_text: 'x', quote_status: 'exact', council_quote: 'Landscaping of the\narea. The rest' };
    expect(shownText(p)).toBe('Landscaping of the area. The rest');
  });

  it('marks an unchecked council rule and keeps its numbers out of any chip', () => {
    for (const quote_status of ['unconfirmed', 'not_a_control', null]) {
      const p = { ...NB, provision_text: 'Maximum height 9m', council_quote: null, quote_status };
      expect(shownText(p)).toBe('Maximum height 9m');
      expect(quoteNote(p)).toBe(QUOTE_NOTE_UNCHECKED);
      expect(numbersUsable(p)).toBe(false);
    }
  });

  it('never serves a confirmed status without stored words, so the client cannot trust a hollow one', () => {
    const p = { ...NB, provision_text: 'Maximum height 9m', council_quote: null, quote_status: 'exact' };
    expect(hasCouncilWords(p)).toBe(false);
    expect(shownText(p)).toBe('Maximum height 9m');
    const served = { ...NB, provision_text: shownText(p), quote_status: servedQuoteStatus(p) };
    expect(served.quote_status).toBeNull();
    expect(quoteNote(served)).toBe(QUOTE_NOTE_UNCHECKED);
    expect(numbersUsable(served)).toBe(false);
  });

  it('serves a confirmed status unchanged when the words are stored', () => {
    expect(servedQuoteStatus({ ...NB, council_quote: 'Words', quote_status: 'recovered' })).toBe('recovered');
    expect(servedQuoteStatus({ ...NB, council_quote: null, quote_status: 'unconfirmed' })).toBe('unconfirmed');
  });

  it('leaves LEP and SEPP rules (no council) as they were', () => {
    const p = { provision_text: 'Clause 4.3 height', source_council: null };
    expect(shownText(p)).toBe('Clause 4.3 height');
    expect(quoteNote(p)).toBeNull();
    expect(numbersUsable(p)).toBe(true);
  });
});
