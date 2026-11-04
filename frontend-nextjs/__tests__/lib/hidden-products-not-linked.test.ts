/**
 * Flood, bushfire, solar and climate risk are withdrawn from every menu,
 * sitemap and link until they are checked (lib/hidden-products.ts). This
 * scans every page, component and lib file for a route string that points at
 * one of them, so a new link anywhere fails CI instead of quietly sending
 * visitors to an unchecked product.
 */
import fs from 'fs';
import path from 'path';
import { HIDDEN_ROUTE_PREFIXES, isHiddenPath } from '@/lib/hidden-products';

const ROOT = path.resolve(__dirname, '..', '..');
const SCAN = ['app', 'components', 'lib'];

// The withdrawn pages themselves, API routes, and the files that do the hiding.
const EXEMPT = [
  /^app\/api\//,
  /^app\/\(tools\)\/(flood-risk|bushfire|solar-potential)\//,
  /^app\/reports\/(flood|bushfire|solar-yield)\//,
  /^app\/embed\/(flood|solar-yield)\//,
  /^app\/climate-risk\//,
  /^lib\/hidden-products\.ts$/,
  /^app\/sitemap\.ts$/,
];

function files(dir: string): string[] {
  const out: string[] = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === '__tests__') continue;
      out.push(...files(p));
    } else if (/\.(tsx?|jsx?)$/.test(e.name)) {
      out.push(p);
    }
  }
  return out;
}

// A quoted or template string whose path starts with a hidden prefix, e.g.
// '/reports/flood', `${base}/flood-risk/${slug}`, "https://x/bushfire".
const PREFIX_ALT = HIDDEN_ROUTE_PREFIXES.map((p) => p.replace(/[/-]/g, '\\$&')).join('|');
const LINK = new RegExp(`(?:['"\`]|\\}|https?://[^'"\`\\s/]+)(${PREFIX_ALT})(?=[/?#'"\`$]|$)`, 'g');

function offenders(): string[] {
  const found: string[] = [];
  for (const top of SCAN) {
    for (const file of files(path.join(ROOT, top))) {
      const rel = path.relative(ROOT, file).split(path.sep).join('/');
      if (EXEMPT.some((r) => r.test(rel))) continue;
      fs.readFileSync(file, 'utf8').split('\n').forEach((line, i) => {
        if (/^\s*(\/\/|\*)/.test(line)) return; // comments are not links
        for (const m of line.matchAll(LINK)) found.push(`${rel}:${i + 1}  ${m[1]}`);
      });
    }
  }
  return found;
}

describe('withdrawn products are not linked', () => {
  it('isHiddenPath matches each prefix and its sub-pages, nothing else', () => {
    expect(isHiddenPath('/reports/bushfire')).toBe(true);
    expect(isHiddenPath('/solar-potential/penrith')).toBe(true);
    // Flood is back (2026-10-30): its routes are linkable again.
    expect(isHiddenPath('/reports/flood')).toBe(false);
    expect(isHiddenPath('/flood-risk/penrith')).toBe(false);
    expect(isHiddenPath('https://canibuildit.com.au/bushfire/ballina?x=1')).toBe(true);
    expect(isHiddenPath('/reports/granny-flat')).toBe(false);
    expect(isHiddenPath('/blog/is-my-house-in-a-flood-zone-nsw')).toBe(false);
    expect(isHiddenPath('/reports/bushfire-zone')).toBe(false);
  });

  it('no page, component or lib file links to a withdrawn product', () => {
    const found = offenders();
    expect(found).toEqual([]);
  });
});
