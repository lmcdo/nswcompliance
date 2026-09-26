import { citationIsShown, stripStoredCode, withServedCitation } from '@/lib/citation-display';

describe('a DCP clause number is served only when its page proves it', () => {
  it('shows proven and imprecise, hides the rest, serves unchecked rows as before', () => {
    expect(citationIsShown('proven')).toBe(true);
    expect(citationIsShown('imprecise')).toBe(true);
    expect(citationIsShown(null)).toBe(true);
    for (const s of ['not_proven', 'unjudged', 'text_not_found', 'no_source']) {
      expect(citationIsShown(s)).toBe(false);
    }
  });

  it('strips exactly the stored code from our own first line', () => {
    const t = '# C4.9 Fences and walls\n\nFences are to be ...';
    expect(stripStoredCode(t, 'Doc__chap__C4_9')).toBe('# Fences and walls\n\nFences are to be ...');
    // a different code on the first line is not ours to remove
    expect(stripStoredCode('# C4.10 Fences\n\nx', 'Doc__chap__C4_1')).toBe('# C4.10 Fences\n\nx');
    // no heading line: untouched
    expect(stripStoredCode('Fences are to be ...', 'Doc__C4_9')).toBe('Fences are to be ...');
  });

  it('drops the clause label and code for an unproven row, keeps them for a proven one', () => {
    const row = { citation_status: 'not_proven', ref_number: 'D__G2 C14', provision_text: '# G2 C14 Setbacks\n\nBuildings ...' };
    const out = withServedCitation(row, 'G2 C14');
    expect(out.clause_label).toBeNull();
    expect(out.citation_shown).toBe(false);
    expect(out.provision_text).toBe('# Setbacks\n\nBuildings ...');
    const ok = withServedCitation({ ...row, citation_status: 'proven' }, 'G2 C14');
    expect(ok.clause_label).toBe('G2 C14');
    expect(ok.provision_text).toBe(row.provision_text);
  });
});
