/**
 * Every static URL in the sitemap must resolve to something.
 *
 * A sitemap entry that 404s is worse than an absent one: it spends crawl budget
 * and is reported back as a soft 404. Measured 2026-08-26, /shadow and
 * /solar-potential were both advertised and both dead, because the clean URLs
 * in next.config.js are /shadow-check and /solar-yield - different slugs that
 * nothing reconciled.
 *
 * "Resolves" means one of:
 *   - a page.tsx exists for that route (including inside a (group) folder), or
 *   - next.config.js redirects it.
 *
 * Scope is the STATIC entries in sitemap chunk 0. The LGA chunks are generated
 * from data arrays by mapping a slug onto a [lga-slug] route, so their shape is
 * guaranteed by construction rather than by enumeration.
 */
import fs from 'fs';
import path from 'path';

const APP = path.join(__dirname, '..', 'app');
const SITEMAP = path.join(APP, 'sitemap.ts');
const CONFIG = path.join(__dirname, '..', 'next.config.js');

/** Static `${base}/some/path` entries, which are the ones typed by hand. */
function staticSitemapPaths(): string[] {
  const src = fs.readFileSync(SITEMAP, 'utf8');
  const out = new Set<string>();
  for (const m of src.matchAll(/\$\{base\}(\/[a-z0-9/-]*)`/g)) {
    const p = m[1];
    if (p && p !== '/' && !p.includes('${')) out.add(p);
  }
  return [...out].sort();
}

function redirectSources(): Set<string> {
  const src = fs.readFileSync(CONFIG, 'utf8');
  return new Set([...src.matchAll(/source:\s*'([^']+)'/g)].map((m) => m[1]));
}

/** A route exists if any page.tsx maps to it, ignoring (group) segments. */
function routeExists(urlPath: string): boolean {
  const wanted = urlPath.replace(/^\//, '').split('/');
  const walk = (dir: string, parts: string[]): boolean => {
    if (parts.length === 0) return fs.existsSync(path.join(dir, 'page.tsx'));
    const [head, ...rest] = parts;
    if (!fs.existsSync(dir)) return false;
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!e.isDirectory()) continue;
      if (e.name === head) {
        if (walk(path.join(dir, e.name), rest)) return true;
      } else if (e.name.startsWith('(') && e.name.endsWith(')')) {
        if (walk(path.join(dir, e.name), parts)) return true;   // route group
      }
    }
    return false;
  };
  return walk(APP, wanted);
}

describe('static sitemap URLs resolve', () => {
  const paths = staticSitemapPaths();
  const redirects = redirectSources();

  it('found sitemap entries at all (guards the guard)', () => {
    expect(paths.length).toBeGreaterThan(10);
  });

  it('finds a known-good route, so routeExists is not always false', () => {
    // Without this, a broken resolver would report every URL as missing and the
    // suite would look catastrophically red rather than subtly wrong - or, if
    // inverted, silently green.
    expect(routeExists('/assessment')).toBe(true);
    expect(routeExists('/definitely-not-a-route')).toBe(false);
  });

  it.each(paths)('%s has a page or a redirect', (p) => {
    expect(routeExists(p) || redirects.has(p)).toBe(true);
  });
});
