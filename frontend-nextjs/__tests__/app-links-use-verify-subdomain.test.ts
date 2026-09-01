/**
 * App-route links must not point at the bare plotdetect.com.au domain.
 *
 * The apex serves a SEPARATE marketing site (a different Vercel project). The
 * app lives on verify.plotdetect.com.au. So `plotdetect.com.au/reports/flood`
 * is a 404 while `verify.plotdetect.com.au/reports/flood` is a 200 - measured
 * 2026-08-26, when 26 such links were found across 23 files.
 *
 * The worst were not the dead clicks. Customers were emailed a granny flat
 * result linking to the apex, the JSON-LD logo 404'd, and two canonical URLs
 * told search engines the real page lived at a dead address.
 *
 * A BARE https://plotdetect.com.au with no path is CORRECT and must keep
 * passing - that is the organisation's own website in the JSON-LD identity
 * block. Only host-plus-path is an app route.
 */
import fs from 'fs';
import path from 'path';
import { execFileSync } from 'child_process';

const APEX_WITH_PATH = /https:\/\/plotdetect\.com\.au\/(?=[A-Za-z0-9])/;
const ROOT = path.join(__dirname, '..', '..');

function trackedFiles(): string[] {
  // git is the population that ships. Scanning the filesystem instead would
  // sweep in build output and untracked scratch files.
  const env = { ...process.env };
  for (const k of Object.keys(env)) if (k.startsWith('GIT_')) delete env[k];
  return execFileSync(
    'git',
    ['ls-files', '--', 'frontend-nextjs', 'services', 'scripts'],
    { cwd: ROOT, encoding: 'utf8', env },
  )
    .split('\n')
    .filter((f) => /\.(ts|tsx|py|md)$/.test(f));
}

describe('app-route links use the verify subdomain', () => {
  const files = trackedFiles();

  it('git actually answered (guards the guard)', () => {
    // An empty list would make every assertion below pass vacuously.
    expect(files.length).toBeGreaterThan(0);
  });

  it('no tracked source file links the apex to an app route', () => {
    const offenders: string[] = [];
    for (const rel of files) {
      const full = path.join(ROOT, rel);
      if (!fs.existsSync(full)) continue;
      const src = fs.readFileSync(full, 'utf8');
      src.split('\n').forEach((line, i) => {
        if (APEX_WITH_PATH.test(line)) offenders.push(`${rel}:${i + 1}`);
      });
    }
    expect(offenders).toEqual([]);
  });

  it('still allows the bare apex as the organisation identity', () => {
    // The JSON-LD Organization url is the marketing site and is correct.
    // A rule that banned the host outright would delete a true statement.
    const layout = fs.readFileSync(
      path.join(ROOT, 'frontend-nextjs', 'app', 'layout.tsx'),
      'utf8',
    );
    expect(layout).toContain("url: 'https://plotdetect.com.au'");
    expect(APEX_WITH_PATH.test("url: 'https://plotdetect.com.au',")).toBe(false);
  });

  it('does not let the fix over-reach onto the identity blocks', () => {
    // The first version of this test only asserted that SOME bare org url
    // survived. layout.tsx has TWO, so rewriting one still passed - a guard
    // that could not see half of what it guarded. Naming the app subdomain as
    // an identity url is always wrong: that block describes the organisation,
    // not the application.
    const layout = fs.readFileSync(
      path.join(ROOT, 'frontend-nextjs', 'app', 'layout.tsx'),
      'utf8',
    );
    const identityLines = layout
      .split(String.fromCharCode(10))
      .filter((l) => /^\s*url: 'https:\/\//.test(l));
    expect(identityLines.length).toBeGreaterThan(0);
    expect(
      identityLines.filter((l) => l.includes('verify.plotdetect.com.au')),
    ).toEqual([]);
  });
});
