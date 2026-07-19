/**
 * Widget partner registry.
 *
 * The registry drives outreach demo pages — a broken slug or a non-https CTA
 * silently breaks a builder's first impression, so the config itself is
 * tested. Branding is registry-only (no free-form params — review finding,
 * PR #790), so getWidgetPartner is the entire trust boundary.
 */
import { WIDGET_PARTNERS, getWidgetPartner } from '@/lib/widget-partners';

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
    expect(getWidgetPartner(undefined)).toBeNull();
  });

  it('rejects a repeated ref param (array) instead of picking one', () => {
    expect(getWidgetPartner(['buildana', 'clover-homes'])).toBeNull();
    expect(getWidgetPartner(['buildana'])).toBeNull();
  });
});
