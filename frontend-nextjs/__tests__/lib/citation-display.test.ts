import { citationIsShown, stripStoredCode, withServedCitation, stripOccurrenceSuffix, stateClauseLabel, servedClauseLabel, referenceForDocument } from '@/lib/citation-display';

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

describe('compound structural references and document-id fail-closed', () => {
  it.each(['Part 2, Division 3', 'Part 2 Division 3', 'Schedule 1 Part 2', 'Chapter 3 Part 2', 'Part 5A'])('accepts %s', (ref) => {
    expect(stateClauseLabel(ref)).toBe(ref);
  });
  it('still rejects internal ids with a Part-like prefix', () => {
    expect(stateClauseLabel('Part_2')).toBeNull();
    expect(stateClauseLabel('Part provision_9')).toBeNull();
  });
  it('referenceForDocument: unrecognised document id with provision_99 gets no clause', () => {
    expect(referenceForDocument('provision_99', 'Some_Unknown_Doc')).toBeNull();
    expect(referenceForDocument('provision_99', null)).toBeNull();
    expect(referenceForDocument('provision_99', 'State_Environmental_Planning_Policy_DCP')).toBeNull();
  });
  it('referenceForDocument: a council DCP document passes its reference', () => {
    expect(referenceForDocument('C4.9', 'Warringah_DCP_2011')).toBe('C4.9');
  });
});

describe('a state-law reference is shown only if it looks like a real NSW clause', () => {
  it('shows real clause shapes', () => {
    for (const ok of ['2.30AB', '3A.12', 'cl 5.10', 'Clause 4.1', 'Schedule 2 cl 6', 'Schedule 1', 's 87', '4.6(3)', 'Chapter 3',
      // labels written by scripts/sepp_ref_fix.py from the law's own unit ids
      'Section 3.4(2)(e)', 'Schedule 11, section 4', 'Schedule 6A, section 19', 'Schedule 2A, section 141R(1)(c)']) {
      expect(stateClauseLabel(ok)).toBe(ok);
    }
  });
  it('never shows internal ids', () => {
    for (const bad of ['provision_2344', 'layout_no', 'Provision 12', '2344', '3f2b8c1e-1234-4abc-9def-0123456789ab', 'SEPP__part_3__3_1', '', '   ', null, undefined, 42]) {
      expect(stateClauseLabel(bad)).toBeNull();
    }
  });
  it('withServedCitation: state row with internal id gets no clause label, real one kept', () => {
    const base = { citation_status: null, source_council: null, provision_text: 'x' };
    expect(withServedCitation({ ...base, ref_number: 'provision_2344' }, 'provision_2344').clause_label).toBeNull();
    expect(withServedCitation({ ...base, ref_number: '2.30AB' }, '2.30AB').clause_label).toBe('2.30AB');
  });
  it('council rows are unchanged', () => {
    expect(servedClauseLabel('C4.9', 'warringah')).toBe('C4.9');
    expect(servedClauseLabel('2.6 C3', 'marrickville')).toBe('2.6 C3');
    const p = { citation_status: 'proven', source_council: 'warringah', ref_number: 'D__C4_9', provision_text: 'x' };
    expect(withServedCitation(p, 'C4.9').clause_label).toBe('C4.9');
  });
});
