import {
  DATA_DICTIONARY_FIELDS,
  getDataDictionaryField,
} from '@/lib/data-dictionary';

describe('data dictionary content integrity', () => {
  it('has unique, url-safe slugs', () => {
    const slugs = DATA_DICTIONARY_FIELDS.map(f => f.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const slug of slugs) {
      expect(slug).toMatch(/^[a-z0-9-]+$/);
    }
  });

  it('every field has non-empty documentation in every section', () => {
    for (const f of DATA_DICTIONARY_FIELDS) {
      expect(f.name.trim()).not.toBe('');
      expect(f.shortDefinition.trim()).not.toBe('');
      expect(f.explanation.length).toBeGreaterThan(0);
      f.explanation.forEach(p => expect(p.trim()).not.toBe(''));
      expect(f.sourceName.trim()).not.toBe('');
      expect(f.licence.trim()).not.toBe('');
      expect(f.attribution.trim()).not.toBe('');
      expect(f.currency.trim()).not.toBe('');
      expect(f.caveats.length).toBeGreaterThan(0);
      expect(f.related.length).toBeGreaterThan(0);
    }
  });

  it('source URLs are https', () => {
    for (const f of DATA_DICTIONARY_FIELDS) {
      expect(f.sourceUrl).toMatch(/^https:\/\//);
    }
  });

  it('every attribution names the State of New South Wales', () => {
    // CC-BY attribution is a licence condition, not decoration (MCP plan
    // phase 0.1 carve-out 1) — a field must never ship without it.
    for (const f of DATA_DICTIONARY_FIELDS) {
      expect(f.attribution).toContain('State of New South Wales');
    }
  });

  it('user-facing copy contains no liability language', () => {
    // Subset of the pre-pr-review banned list that is never acceptable in
    // descriptive data documentation. ("certified" is excluded: the RFS
    // bushfire map is certified by statute — that is the regulatory term.)
    const banned =
      /\b(guaranteed?|ensures?|assures?|accurate|comprehensive|reliable|definitive|recommends?|suitable|feasible|compliant|approved|verified|should)\b/i;
    for (const f of DATA_DICTIONARY_FIELDS) {
      const texts = [
        f.shortDefinition,
        ...f.explanation,
        f.currency,
        ...f.caveats,
      ];
      for (const text of texts) {
        expect(text).not.toMatch(banned);
      }
    }
  });

  it('related links are internal paths', () => {
    for (const f of DATA_DICTIONARY_FIELDS) {
      for (const r of f.related) {
        expect(r.href).toMatch(/^\//);
        expect(r.label.trim()).not.toBe('');
      }
    }
  });

  it('getDataDictionaryField resolves every slug and rejects unknowns', () => {
    for (const f of DATA_DICTIONARY_FIELDS) {
      expect(getDataDictionaryField(f.slug)).toBe(f);
    }
    expect(getDataDictionaryField('no-such-field')).toBeUndefined();
  });
});
