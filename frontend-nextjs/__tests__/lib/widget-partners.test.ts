/**
 * Widget partner registry + embed param sanitizers.
 *
 * The registry drives outreach demo pages — a broken slug or a non-https CTA
 * silently breaks a builder's first impression, so the config itself is
 * tested. The sanitizers are the XSS/open-redirect boundary for the embed's
 * free-form query params.
 */
import {
  WIDGET_PARTNERS,
  getWidgetPartner,
  sanitizeCtaUrl,
  sanitizePartnerName,
} from '@/lib/widget-partners';

describe('WIDGET_PARTNERS registry', () => {
  it('holds all 20 outreach targets', () => {
    expect(WIDGET_PARTNERS).toHaveLength(20);
  });

  it('has unique, kebab-case slugs', () => {
    const slugs = WIDGET_PARTNERS.map((p) => p.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const slug of slugs) {
      expect(slug).toMatch(/^[a-z0-9]+(-[a-z0-9]+)*$/);
    }
  });

  it('every site and ctaUrl is a valid https URL', () => {
    for (const p of WIDGET_PARTNERS) {
      expect(new URL(p.site).protocol).toBe('https:');
      expect(new URL(p.ctaUrl).protocol).toBe('https:');
    }
  });

  it('every partner has a non-empty display name', () => {
    for (const p of WIDGET_PARTNERS) {
      expect(p.name.trim().length).toBeGreaterThan(0);
    }
  });

  it('ctaUrl stays on the partner own registrable domain (enquiries are theirs)', () => {
    // Registrable-domain comparison, not exact host: www.buildana.com.au and
    // buildana.com.au are the same owner. duplex-building-design is the one
    // deliberate exception (published contact email lives on the sister
    // company domain, but its CTA page is still on its own domain).
    const registrable = (host: string) => host.split('.').slice(-3).join('.');
    for (const p of WIDGET_PARTNERS) {
      expect(registrable(new URL(p.ctaUrl).host)).toBe(registrable(new URL(p.site).host));
    }
  });
});

describe('getWidgetPartner', () => {
  it('returns the config for a known slug', () => {
    expect(getWidgetPartner('buildana')?.name).toBe('Buildana');
  });

  it('returns null for unknown slugs', () => {
    expect(getWidgetPartner('not-a-partner')).toBeNull();
    expect(getWidgetPartner('')).toBeNull();
  });
});

describe('sanitizePartnerName', () => {
  it('passes ordinary business names', () => {
    expect(sanitizePartnerName('Clover Homes')).toBe('Clover Homes');
    expect(sanitizePartnerName("O'Brien Building & Co (Syd)")).toBe("O'Brien Building & Co (Syd)");
  });

  it('rejects markup and empty input', () => {
    expect(sanitizePartnerName('<script>alert(1)</script>')).toBeNull();
    expect(sanitizePartnerName(undefined)).toBeNull();
    expect(sanitizePartnerName('')).toBeNull();
  });

  it('caps length at 40 characters before validating', () => {
    const long = 'A'.repeat(60);
    expect(sanitizePartnerName(long)).toBe('A'.repeat(40));
  });
});

describe('sanitizeCtaUrl', () => {
  it('passes https URLs', () => {
    expect(sanitizeCtaUrl('https://example.com.au/contact/')).toBe('https://example.com.au/contact/');
  });

  it('rejects javascript:, data:, http:, and garbage', () => {
    expect(sanitizeCtaUrl('javascript:alert(1)')).toBeNull();
    // eslint-disable-next-line no-script-url
    expect(sanitizeCtaUrl('data:text/html,<h1>x</h1>')).toBeNull();
    expect(sanitizeCtaUrl('http://example.com')).toBeNull();
    expect(sanitizeCtaUrl('not a url')).toBeNull();
    expect(sanitizeCtaUrl(undefined)).toBeNull();
  });
});
