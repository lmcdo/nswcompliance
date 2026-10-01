import { citationIsShown, stripStoredCode, withServedCitation, stripOccurrenceSuffix } from '@/lib/citation-display';

const NL = '\n';

describe('a DCP clause number is served only when its page proves it', () => {
  it('shows proven and imprecise, hides the rest; unchecked DCP rows fail closed', () => {
    expect(citationIsShown('proven')).toBe(true);
    expect(citationIsShown('imprecise')).toBe(true);
    expect(citationIsShown(null)).toBe(true); // LEP/SEPP: not a DCP row
    expect(citationIsShown(null, 'warringah')).toBe(false); // unchecked DCP row
    for (const s of ['partial', 'not_proven', 'unjudged', 'text_not_found', 'no_source']) {
      expect(citationIsShown(s, 'warringah')).toBe(false);
    }
  });

  it('strips exactly the stored code from our own first line', () => {
    const t = `# C4.9 Fences and walls${NL}${NL}Fences are to be ...`;
    expect(stripStoredCode(t, 'Doc__chap__C4_9')).toBe(`# Fences and walls${NL}${NL}Fences are to be ...`);
    // punctuation after the code ends it too
    expect(stripStoredCode(`# C4.9: Fences${NL}${NL}x`, 'Doc__C4_9')).toBe(`# Fences${NL}${NL}x`);
    expect(stripStoredCode(`# C4.9 – Fences${NL}${NL}x`, 'Doc__C4_9')).toBe(`# Fences${NL}${NL}x`);
    // a longer code that merely starts the same is not ours
    expect(stripStoredCode(`# C4.91 Fences${NL}${NL}x`, 'Doc__C4_9')).toBe(`# C4.91 Fences${NL}${NL}x`);
    // a different code on the first line is not ours to remove
    expect(stripStoredCode(`# C4.10 Fences${NL}${NL}x`, 'Doc__chap__C4_1')).toBe(`# C4.10 Fences${NL}${NL}x`);
    // no heading line: untouched
    expect(stripStoredCode('Fences are to be ...', 'Doc__C4_9')).toBe('Fences are to be ...');
  });

  it('drops the clause label and code for an unproven row, keeps them for a proven one', () => {
    const row = {
      citation_status: 'not_proven',
      source_council: 'northern_beaches',
      ref_number: 'D__G2 C14',
      provision_text: `# G2 C14 Setbacks${NL}${NL}Buildings ...`,
    };
    const out = withServedCitation(row, 'G2 C14');
    expect(out.clause_label).toBeNull();
    expect(out.citation_shown).toBe(false);
    expect(out.provision_text).toBe(`# Setbacks${NL}${NL}Buildings ...`);
    const ok = withServedCitation({ ...row, citation_status: 'proven' }, 'G2 C14');
    expect(ok.clause_label).toBe('G2 C14');
    expect(ok.provision_text).toBe(row.provision_text);
  });
});

describe('the internal occurrence suffix never reaches a reader', () => {
  // dcp_extract_changed suffixes a repeated ref (`..._7_4 (a)_2`) so two clauses
  // the council prints under the same letter stop overwriting each other —
  // schedules 7.4 restarts (a)(b)(c) under a "Pedestrians" sub-heading. The suffix
  // is ours. The council's document has no clause "7.4 (a)_2", and
  // browse/section/route.ts passes ref_number straight through as the label while
  // citation_proof.split_ref ignores the suffix, so a proven row would render the
  // invented reference. Caught by the pre-push cross-review, 2026-10-02.
  const proven = { citation_status: 'proven', source_council: 'city_of_sydney' };

  it('strips the suffix from a shown label', () => {
    const r = withServedCitation(proven, 'Sydney_DCP_2012__schedules__7_4 (a)~2');
    expect(r.clause_label).toBe('Sydney_DCP_2012__schedules__7_4 (a)');
    expect(r.clause_label).not.toMatch(/_\d+$/);
  });

  it('leaves a label with no suffix untouched', () => {
    const r = withServedCitation(proven, 'Sydney_DCP_2012__schedules__7_4 (a)');
    expect(r.clause_label).toBe('Sydney_DCP_2012__schedules__7_4 (a)');
  });

  it('strips a double-digit occurrence', () => {
    expect(stripOccurrenceSuffix('x__7_4 (a)~12')).toBe('x__7_4 (a)');
  });

  it('does NOT touch a section number that genuinely ends in _N', () => {
    // Section 3.16 is stored as `3_16`. An underscore marker would be eaten here
    // and render the clause as `3`, which is why the marker is a tilde.
    expect(stripOccurrenceSuffix('x__3_16')).toBe('x__3_16');
    expect(stripOccurrenceSuffix('x__7_4_2')).toBe('x__7_4_2');
  });

  it('returns null for a non-string label', () => {
    expect(stripOccurrenceSuffix(null)).toBeNull();
    expect(stripOccurrenceSuffix(undefined)).toBeNull();
  });

  it('an unproven row still shows no label at all', () => {
    const r = withServedCitation(
      { citation_status: 'not_proven', source_council: 'city_of_sydney' },
      'Sydney_DCP_2012__schedules__7_4 (a)~2');
    expect(r.clause_label).toBeNull();
  });
});
