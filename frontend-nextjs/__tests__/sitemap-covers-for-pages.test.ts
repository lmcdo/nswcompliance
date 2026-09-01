/**
 * Every /for/<audience> page that exists on disk must appear in the sitemap.
 *
 * `/for/students` was live and sat in NONE of the 8 sitemap chunks until
 * 2026-08-25. The page was built, reviewed and shipped; nothing ever told a
 * search engine it existed. Six of the seven /for/ pages were listed, so the
 * omission looked exactly like the list being complete.
 *
 * This reads the FILESYSTEM as the source of truth rather than a hardcoded
 * list — a second hardcoded list would drift from the first in the same way
 * and reproduce the defect one level up.
 */
import fs from 'fs';
import path from 'path';

const APP_DIR = path.join(__dirname, '..', 'app');
const FOR_DIR = path.join(APP_DIR, 'for');
const SITEMAP = path.join(APP_DIR, 'sitemap.ts');

function audiencesOnDisk(): string[] {
  return fs
    .readdirSync(FOR_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .filter((e) => fs.existsSync(path.join(FOR_DIR, e.name, 'page.tsx')))
    .map((e) => e.name)
    .sort();
}

describe('sitemap covers every /for/ page', () => {
  const sitemapSource = fs.readFileSync(SITEMAP, 'utf8');
  const audiences = audiencesOnDisk();

  it('finds the audience pages at all (guards the guard)', () => {
    // If the directory move or a rename made this list empty, every assertion
    // below would pass vacuously — which is how a check stops checking.
    expect(audiences.length).toBeGreaterThan(0);
  });

  it.each(audiences)('lists /for/%s', (audience) => {
    expect(sitemapSource).toContain(`/for/${audience}`);
  });
});
