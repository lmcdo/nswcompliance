/**
 * #1362 shipped `/^class\b/i` with a real backspace (0x08) in place of `\b`, written by a
 * script that read "\b" as an escape. The regex never matched, so "Class Class 5" stayed live.
 * No source file should hold a control character other than tab, newline or carriage return.
 */
import fs from 'fs';
import path from 'path';

const ROOT = path.join(__dirname, '..', '..');
const DIRS = ['components', 'lib', 'app', 'hooks'];
const BAD = /[\x00-\x08\x0b\x0c\x0e-\x1f]/;

function walk(dir: string, out: string[]) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (/\.(ts|tsx)$/.test(e.name)) out.push(p);
  }
}

it('no control characters in frontend source', () => {
  const files: string[] = [];
  for (const d of DIRS) if (fs.existsSync(path.join(ROOT, d))) walk(path.join(ROOT, d), files);
  const hits = files.filter(f => BAD.test(fs.readFileSync(f, 'utf8'))).map(f => path.relative(ROOT, f));
  expect(hits).toEqual([]);
});
