/**
 * An unknown property fact must never be shown or used as "No".
 *
 * /api/property returns null (heritage, strata, corner lot) or nothing (acid sulfate, BASIX) when the
 * source did not answer, and names it in constraints.notChecked. Code that turns that into "No",
 * false or "pass" re-creates the made-up answer on the page. This scans every source file for the
 * ways that happens. A flagged line passes only when fixed or marked `unknown-ok: <reason>`.
 *
 * prior-art-checked: reuse not viable because scripts/qa_gate.py checks only the PR's own diff and the
 * fabricated-verdict lint looks for literal verdicts, not unknown-to-No coercions of these fields.
 */
import { readdirSync, readFileSync, statSync } from 'fs';
import { join, relative } from 'path';

const ROOT = join(__dirname, '..');
const DIRS = ['app', 'components', 'lib', 'hooks'];

/** Facts the lookup can leave unknown. */
const FIELD = String.raw`(?:isHeritage|isStrata|isCornerLot|acidSulfateSoils|basixClimate|basixWater|heritage)`;
/** A read of one of them: `a.b?.isHeritage`, `isHeritage`, `data.heritage`. */
const READ = String.raw`[\w$.?\[\]'"]*\b${FIELD}\b`;

const PATTERNS: Array<[string, RegExp]> = [
  ['unknown read as "No"', new RegExp(String.raw`${READ}\)?\s*\?[^:;]*:\s*['"\`]No\b`)],
  ['unknown shown in the "clear" colour', new RegExp(String.raw`${READ}\)?\s*\?[^:;]*:\s*['"\`][^'"\`]*green`)],
  ['unknown read as false',new RegExp(String.raw`${READ}\)?\s*(?:\|\||\?\?)\s*false\b`)],
  ['unknown read as false (!!)', new RegExp(String.raw`!!\s*\(?\s*${READ}`)],
  ['unknown read as false (Boolean)', new RegExp(String.raw`Boolean\(\s*${READ}`)],
  ['unknown read as "not" (!)', new RegExp(String.raw`(?:^|[^!=\w])!\s*\(?\s*${READ}\s*(?:\)|\}|\]|&&|\|\||\?|;|,|$)`)],
];

export function scan(text: string): Array<{ line: number; kind: string; code: string }> {
  const out: Array<{ line: number; kind: string; code: string }> = [];
  text.split('\n').forEach((code, i) => {
    const t = code.trim();
    if (t.startsWith('//') || t.startsWith('*') || t.startsWith('/*')) return;
    if (/unknown-ok:\s*\S/.test(code)) return;
    for (const [kind, re] of PATTERNS) {
      if (re.test(code)) {
        out.push({ line: i + 1, kind, code: t.slice(0, 160) });
        break;
      }
    }
  });
  return out;
}

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return name === 'node_modules' || name === '__tests__' ? [] : files(p);
    return /\.(ts|tsx)$/.test(name) && !/\.d\.ts$/.test(name) ? [p] : [];
  });
}

describe('unknown facts are never shown or used as "No"', () => {
  it('the scanner flags every bad pattern (fixture)', () => {
    const fixture = [
      "const a = p.heritage?.isHeritage ? 'Yes' : 'No';",
      'const b = p.heritage?.isHeritage || false;',
      'const c = p.strataInfo?.isStrata ?? false;',
      'const d = !!p.strataInfo?.isStrata;',
      'const e = Boolean(p.constraints?.acidSulfateSoils);',
      'const f = { pass: !isHeritage };',
      "const g = data.heritage ? 'Yes' : 'No';",
      "const h = c.acidSulfateSoils ? `Class ${c.acidSulfateSoils}` : 'No';",
      "const i = `x ${p.heritage?.isHeritage ? 'text-red-600' : 'text-green-600'}`;",
      // must NOT flag:
      'const ok1 = p.heritage?.isHeritage === true;',
      "const ok2 = isHeritage === null ? 'Not checked' : isHeritage ? 'Yes' : 'No'; // unknown-ok: null handled first",
      'const ok3 = heritage !== false;',
    ].join('\n');
    expect(scan(fixture).map((f) => f.line)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });

  it('the not-checked list is read only through wasNotChecked (lib/fact-answer.ts)', () => {
    // A direct read forgets that a payload with NO list cannot show anything was checked.
    const direct = /constraints\??\.notChecked\??\.(?:includes|some|indexOf)|Array\.isArray\([\w.?]*constraints\??\.notChecked\)/;
    const found = DIRS.flatMap((d) => files(join(ROOT, d)))
      .filter((f) => !/lib[\\/]fact-answer\.ts$/.test(f))
      .flatMap((f) => readFileSync(f, 'utf-8').split('\n').map((code, i) => ({ f, i, code }))
        .filter(({ code }) => direct.test(code))
        .map(({ f, i, code }) => `${relative(ROOT, f).replace(/\\/g, '/')}:${i + 1}  ${code.trim().slice(0, 140)}`));
    expect(found).toEqual([]);
  });

  it('no source file turns an unknown fact into "No", false or a pass', () => {
    const found = DIRS.flatMap((d) => files(join(ROOT, d))).flatMap((f) =>
      scan(readFileSync(f, 'utf-8')).map((h) => `${relative(ROOT, f).replace(/\\/g, '/')}:${h.line}  [${h.kind}]  ${h.code}`));
    expect(found).toEqual([]);
  });
});
