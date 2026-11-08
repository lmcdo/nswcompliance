/**
 * The two products have one name each, and the names cannot collide again:
 *   Council Rules = the address-and-project page (/assessment)
 *   Site Facts    = the generated report (/reports/intelligence-brief)
 * "Site Report" named both at once and is retired. This scans app, components and lib.
 *
 * prior-art-checked: reuse not viable because no test pins product names; this follows the
 * source-scan pattern of __tests__/lib/hidden-products-not-linked.test.ts.
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(__dirname, '..', '..');
const SCAN = ['app', 'components', 'lib'];

function files(dir: string): string[] {
  const out: string[] = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === '__tests__' || e.name === '.next') continue;
      out.push(...files(p));
    } else if (/\.(tsx?|jsx?)$/.test(e.name)) {
      out.push(p);
    }
  }
  return out;
}

const ALL = SCAN.flatMap((d) => files(path.join(ROOT, d))).map((p) => ({
  rel: path.relative(ROOT, p).split(path.sep).join('/'),
  text: fs.readFileSync(p, 'utf8'),
}));

describe('product names', () => {
  it('the retired name "Site Report" is not used anywhere', () => {
    expect(ALL.filter((f) => f.text.includes('Site Report')).map((f) => f.rel)).toEqual([]);
  });

  it('"Site Facts" is not used on the address page or the marketing shell', () => {
    const councilRulesSide = /^(app\/assessment\/|app\/page\.tsx$|components\/marketing\/|components\/compliance\/)/;
    const bad = ALL.filter((f) => councilRulesSide.test(f.rel) && f.text.includes('Site Facts')).map((f) => f.rel);
    expect(bad).toEqual([]);
  });

  it('"Council Rules" is not used inside the generated report', () => {
    const bad = ALL.filter((f) => f.rel.startsWith('app/reports/intelligence-brief/') && f.text.includes('Council Rules')).map((f) => f.rel);
    expect(bad).toEqual([]);
  });
});
