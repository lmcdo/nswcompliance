"""Count fabricated citations on origin/main and in the working tree, with ONE
set of patterns, so the two numbers are comparable.

The existing counter reads origin/main and reported 10 citations; the working-tree
counter found 2 more in the same file that the first had missed. Rather than guess
why they disagreed, this runs the same code over both revisions.

RUN FROM THE REPOSITORY ROOT — ROOT below is os.getcwd():

    python scripts/count_citation_fallbacks.py

KNOWN BLIND SPOTS, stated rather than implied by a number. Two shapes do not
match these patterns at all, so this is a floor and not a count:
  - a DEFAULT PARAMETER (`legislativeClause = 'Clause 2.3'`), because the
    literal sits in the component that RECEIVES the value, not the one passing
    it;
  - a hardcoded instrument in JSX text, which is not a fallback expression.
Both shapes were present and both were found by the test ratchet in
frontend-nextjs/__tests__/components/compliance/no-fabricated-citations.test.tsx,
which asserts all three shapes. Treat that suite, not this script, as the gate.
"""
import os
import re
import subprocess
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.getcwd()
ENV = {**os.environ, 'MSYS_NO_PATHCONV': '1'}

PREFIXES = ('frontend-nextjs/components/compliance/', 'frontend-nextjs/components/tod/')
EXTRA = (
    'frontend-nextjs/app/assessment/page.tsx',
    'frontend-nextjs/lib/nsw-planning-portal.ts',
    'frontend-nextjs/lib/see/seeBuilders.ts',
)
STR = re.compile(r"(\?\?|\|\|)\s*'((?:Clause|Section|SEPP|s\d|Part |Schedule)[^']*)'")


def strip_comments(src):
    code = re.sub(r"\{\s*/\*[\s\S]*?\*/\s*\}", ' ', src)
    code = re.sub(r"/\*[\s\S]*?\*/", ' ', code)
    code = re.sub(r"^\s*//.*$", ' ', code, flags=re.M)
    return code


def file_list(rev):
    """Every candidate file at `rev` (or on disk when rev is None)."""
    if rev is None:
        out = []
        for p in PREFIXES:
            d = os.path.join(ROOT, p)
            if os.path.isdir(d):
                out += [p + n for n in sorted(os.listdir(d))]
        out += [f for f in EXTRA if os.path.isfile(os.path.join(ROOT, f))]
    else:
        listing = subprocess.run(
            ['git', 'ls-tree', '-r', '--name-only', rev],
            cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', errors='replace', env=ENV,
        ).stdout.splitlines()
        out = [f for f in listing if f.startswith(PREFIXES) or f in EXTRA]
    return [f for f in out if f.endswith(('.tsx', '.ts')) and '__tests__' not in f]


def read(rev, f):
    if rev is None:
        try:
            return open(os.path.join(ROOT, f), encoding='utf-8', errors='replace').read()
        except OSError:
            return ''
    return subprocess.run(
        ['git', 'show', '%s:%s' % (rev, f)],
        cwd=ROOT, capture_output=True, text=True,
        encoding='utf-8', errors='replace', env=ENV,
    ).stdout


def count(rev, label):
    hits = []
    files = file_list(rev)
    for f in files:
        src = read(rev, f)
        if not src:
            continue
        for ln, line in enumerate(strip_comments(src).splitlines(), 1):
            for m in STR.finditer(line):
                hits.append((f.split('/')[-1], ln, m.group(2)))
    print('=== %s: %d citation fallbacks across %d files ===' % (label, len(hits), len(files)))
    for name, ln, val in hits:
        print('   %-42s L%-6s %s' % (name, ln, val))
    print('')
    return hits


before = count('origin/main', 'origin/main')
after = count(None, 'working tree')

print('origin/main: %d   working tree: %d   removed: %d'
      % (len(before), len(after), len(before) - len(after)))
remaining = sorted({v for _, _, v in after})
print('remaining values: %s' % (remaining or 'none'))
