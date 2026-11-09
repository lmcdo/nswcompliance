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
  PILOT_COUNCIL_LABELS,
  PILOT_COUNCIL_NAMES,
  PILOT_UNLISTED_PREFIXES,
  dataCouncilKey,
  isPilotCouncil,
  isPilotZone,
  pilotCouncilKey,
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
  // The company pages the menu and footer link to.
  'app/how-it-works/page.tsx',
  'app/about/page.tsx',
  'app/contact/page.tsx',
  'app/terms/page.tsx',
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
    // The label list pages show has exactly one entry per council in the scope file, no more.
    expect(PILOT_COUNCIL_LABELS).toHaveLength(PILOT_COUNCILS.length);
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

  it('pilotCouncilKey finds the pilot council by former council or by current council', () => {
    expect(pilotCouncilKey('ashfield', 'Inner West')).toBe('ashfield');
    // An old former-council name must not push a listed council out of the pilot.
    expect(pilotCouncilKey('warringah', 'Northern Beaches')).toBe('northern_beaches');
    expect(pilotCouncilKey('hurstville', 'Georges River')).toBe('georges_river');
    expect(pilotCouncilKey(undefined, 'Hornsby')).toBe('hornsby');
    expect(pilotCouncilKey('leichhardt', 'Inner West')).toBeNull();
    expect(pilotCouncilKey('marrickville', 'Inner West')).toBeNull();
    expect(pilotCouncilKey(null, null)).toBeNull();
    expect(pilotCouncilKey('', '')).toBeNull();
  });

  it('dataCouncilKey prefers the pilot key and otherwise keeps the key the page always used', () => {
    expect(dataCouncilKey('warringah', 'Northern Beaches')).toBe('northern_beaches');
    expect(dataCouncilKey('leichhardt', 'Inner West')).toBe('leichhardt');
    expect(dataCouncilKey(undefined, 'Campbelltown')).toBe('campbelltown');
    expect(dataCouncilKey(undefined, undefined)).toBe('');
  });

  it('every pilot council is found from its own LGA name', () => {
    const lgaNames: Record<string, string> = {
      penrith: 'Penrith', wollongong: 'Wollongong', waverley: 'Waverley', ku_ring_gai: 'Ku-ring-gai',
      blacktown: 'Blacktown', northern_beaches: 'Northern Beaches', georges_river: 'Georges River',
      parramatta: 'City of Parramatta', hornsby: 'Hornsby',
    };
    for (const [key, lga] of Object.entries(lgaNames)) expect(pilotCouncilKey(undefined, lga)).toBe(key);
  });

  it('isPilotZone accepts R2 labels only; other zones and unreadable zones are out', () => {
    expect(isPilotZone('R2')).toBe(true);
    expect(isPilotZone('R2 Low Density Residential')).toBe(true);
    expect(isPilotZone('R2: Low Density Residential')).toBe(true);
    expect(isPilotZone('R3')).toBe(false);
    expect(isPilotZone('R4 High Density Residential')).toBe(false);
    expect(isPilotZone('B4')).toBe(false);
    expect(isPilotZone('Low Density Residential')).toBe(false);
    expect(isPilotZone(undefined)).toBe(false);
    expect(isPilotZone(null)).toBe(false);
    expect(isPilotZone('')).toBe(false);
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
