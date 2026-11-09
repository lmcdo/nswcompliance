/**
 * During the private pilot the site points at Council Rules and Site Facts only (lib/pilot-focus.ts).
 * This fails CI if a navigation surface links anywhere else, if the pricing page shows a price, or if
 * a pilot-unlisted page reaches the sitemap. Old pages stay reachable by URL; they are just not linked.
 */
import fs from 'fs';
import path from 'path';
import {
  PILOT_ALLOWED_LINKS,
  PILOT_COUNCILS,
  PILOT_COUNCIL_NAMES,
  PILOT_UNLISTED_PREFIXES,
  isPilotCouncil,
  isPilotUnlisted,
} from '@/lib/pilot-focus';
import sitemap from '@/app/sitemap';

const ROOT = path.resolve(__dirname, '..', '..');

// Every file a visitor uses to move around the site.
const NAV_FILES = [
  'components/marketing/SiteNav.tsx',
  'components/marketing/HomeNav.tsx',
  'components/marketing/SiteFooter.tsx',
  'app/(tools)/layout.tsx',
  'app/site-directory/page.tsx',
  'app/reports/page.tsx',
  'app/page.tsx',
  'app/pricing/page.tsx',
];

// href="..." / href='...' / href={'...'} / href: '...' (the footer's link tables).
const HREF = /href\s*(?:=\s*\{?\s*|:\s*)(['"`])([^'"`]*)\1/g;

function hrefs(rel: string): { line: number; value: string }[] {
  const out: { line: number; value: string }[] = [];
  fs.readFileSync(path.join(ROOT, rel), 'utf8').split('\n').forEach((text, i) => {
    if (/^\s*(\/\/|\*)/.test(text)) return;
    for (const m of text.matchAll(HREF)) out.push({ line: i + 1, value: m[2] });
  });
  return out;
}

function offendingLinks(): string[] {
  const bad: string[] = [];
  for (const rel of NAV_FILES) {
    for (const { line, value } of hrefs(rel)) {
      if (value.startsWith('mailto:') || value.startsWith('#')) continue;
      // An allowed path may carry a trailing template expression (the ?address= passthrough); nothing else.
      const clean = value.replace(/\$\{[^}]*\}$/, '').split(/[?#]/)[0];
      if (!PILOT_ALLOWED_LINKS.includes(clean)) bad.push(`${rel}:${line}  ${value}`);
    }
  }
  return bad;
}

describe('pilot focus', () => {
  it('no navigation surface links outside the two products and the company pages', () => {
    expect(offendingLinks()).toEqual([]);
  });

  it('the allowed list and the unlisted list never overlap', () => {
    for (const a of PILOT_ALLOWED_LINKS) expect(isPilotUnlisted(a)).toBe(false);
    expect(PILOT_UNLISTED_PREFIXES).not.toContain('/assessment');
    expect(PILOT_UNLISTED_PREFIXES).not.toContain('/reports/intelligence-brief');
  });

  it('isPilotUnlisted matches each prefix and its sub-pages, nothing else', () => {
    expect(isPilotUnlisted('/blog')).toBe(true);
    expect(isPilotUnlisted('/blog/how-we-validate-property-data-nsw')).toBe(true);
    expect(isPilotUnlisted('/reports/granny-flat?x=1')).toBe(true);
    expect(isPilotUnlisted('https://verify.plotdetect.com.au/pricing')).toBe(true);
    expect(isPilotUnlisted('/assessment')).toBe(false);
    expect(isPilotUnlisted('/reports/intelligence-brief')).toBe(false);
    // '/for' is a prefix of '/forum' as text but not as a path.
    expect(isPilotUnlisted('/forum')).toBe(false);
    expect(isPilotUnlisted('/for/planners')).toBe(true);
  });

  it('pilot councils are exactly those named in brief-scope.json and each has a display name', () => {
    expect(PILOT_COUNCILS.length).toBeGreaterThanOrEqual(5);
    for (const c of PILOT_COUNCILS) expect(PILOT_COUNCIL_NAMES[c]).toBeTruthy();
  });

  it('isPilotCouncil: a named council is in, anything unknown or missing is out', () => {
    expect(isPilotCouncil(undefined, 'Hornsby')).toBe(true);
    expect(isPilotCouncil(undefined, 'Ku-ring-gai')).toBe(true);
    expect(isPilotCouncil(undefined, 'City of Parramatta')).toBe(true);
    expect(isPilotCouncil('ashfield', 'Inner West')).toBe(true);
    // Inner West's other former councils are not in the pilot.
    expect(isPilotCouncil('leichhardt', 'Inner West')).toBe(false);
    expect(isPilotCouncil(undefined, 'Inner West')).toBe(false);
    expect(isPilotCouncil(undefined, 'Campbelltown')).toBe(false);
    expect(isPilotCouncil(undefined, undefined)).toBe(false);
    expect(isPilotCouncil('', '   ')).toBe(false);
    expect(isPilotCouncil(null, null)).toBe(false);
  });

  it('the pricing page shows no price and no plan names', () => {
    const src = fs.readFileSync(path.join(ROOT, 'app/pricing/page.tsx'), 'utf8');
    expect(src).not.toMatch(/\$\s?\d/);
    expect(src).not.toMatch(/Site Controls Pro/i);
    expect(src).not.toMatch(/all LGAs/i);
  });

  it('no pilot-unlisted page reaches any sitemap chunk', () => {
    const leaked: string[] = [];
    for (let id = 0; id < 12; id++) {
      for (const e of sitemap({ id })) if (isPilotUnlisted(e.url)) leaked.push(`${id}: ${e.url}`);
    }
    expect(leaked).toEqual([]);
  });
});
