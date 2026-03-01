import { parseHtmlLink, containsHtml } from '@/lib/pdf/htmlUtils';

describe('parseHtmlLink', () => {
  describe('expected use', () => {
    it('extracts text and URL from an anchor tag', () => {
      const result = parseHtmlLink('<a href="https://example.nsw.gov.au">Greater Sydney Region Plan</a>');
      expect(result.text).toBe('Greater Sydney Region Plan');
      expect(result.url).toBe('https://example.nsw.gov.au');
    });

    it('strips HTML tags and returns plain text when no anchor', () => {
      const result = parseHtmlLink('<em>Greater Sydney Region Plan</em>');
      expect(result.text).toBe('Greater Sydney Region Plan');
      expect(result.url).toBeUndefined();
    });

    it('decodes entity-encoded HTML and returns plain text', () => {
      const result = parseHtmlLink('&lt;em&gt;NSW Greater Sydney Region Plan&lt;/em&gt;');
      expect(result.text).toBe('NSW Greater Sydney Region Plan');
      expect(result.url).toBeUndefined();
    });

    it('decodes entity-encoded anchor and extracts URL', () => {
      const result = parseHtmlLink('&lt;a href="https://example.com"&gt;Link Text&lt;/a&gt;');
      expect(result.text).toBe('Link Text');
      expect(result.url).toBe('https://example.com');
    });

    it('passes through plain text unchanged', () => {
      const result = parseHtmlLink('Sydney Metropolitan Region');
      expect(result.text).toBe('Sydney Metropolitan Region');
      expect(result.url).toBeUndefined();
    });
  });

  describe('edge cases', () => {
    it('handles &amp; entity in text', () => {
      const result = parseHtmlLink('<em>Beaches &amp; Headlands</em>');
      expect(result.text).toBe('Beaches & Headlands');
    });

    it('handles empty string', () => {
      const result = parseHtmlLink('');
      expect(result.text).toBe('');
      expect(result.url).toBeUndefined();
    });

    it('handles multiple HTML entities in the same string', () => {
      const result = parseHtmlLink('&lt;strong&gt;Class 1&lt;/strong&gt;');
      expect(result.text).toBe('Class 1');
    });
  });
});

describe('containsHtml', () => {
  it('returns true for strings with HTML tags', () => {
    expect(containsHtml('<em>text</em>')).toBe(true);
    expect(containsHtml('<a href="url">link</a>')).toBe(true);
  });

  it('returns true for strings with HTML entities', () => {
    expect(containsHtml('&lt;em&gt;text&lt;/em&gt;')).toBe(true);
  });

  it('returns false for plain text', () => {
    expect(containsHtml('Greater Sydney Region Plan')).toBe(false);
    expect(containsHtml('R2 Low Density Residential')).toBe(false);
  });

  it('returns false for empty string', () => {
    expect(containsHtml('')).toBe(false);
  });
});
