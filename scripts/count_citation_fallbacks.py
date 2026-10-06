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
A third is narrower but real: the scan is PER LINE, so a fallback whose literal
sits on the line after the `||` is not matched. Quote style is handled -- single,
double and backtick all count -- but a line break between the operator and the
literal is not.
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_report_path import git_env  # noqa: E402

# git_env() is called AT each git call site below rather than hoisted into a
# constant here. A git hook exports GIT_DIR and GIT_INDEX_FILE and they OVERRIDE
# cwd, so without the scrub this would read the hook's repository instead of
# ROOT -- silently, with a confident wrong count (DQ-54). The ratchet in
# tests/test_git_env_ratchet.py requires the literal call and rejects a constant,
# deliberately: `env=os.environ.copy()` would satisfy a looser check while
# scrubbing nothing.

PREFIXES = ('frontend-nextjs/components/compliance/', 'frontend-nextjs/components/tod/')
EXTRA = (
    'frontend-nextjs/app/assessment/page.tsx',
    'frontend-nextjs/lib/nsw-planning-portal.ts',
    'frontend-nextjs/lib/see/seeBuilders.ts',
)
# All three quote styles, closed by backreference so the closing quote matches
# the opening one. Single quotes alone missed `|| "Clause 5.10"` -- the same
# fabricated citation spelled differently -- and this tree uses double quotes in
# places. Still per-line, which the docstring states as a blind spot.
STR = re.compile(
    r"(\?\?|\|\|)\s*(['\"`])((?:Clause|Section|SEPP|s\d|Part |Schedule)[^'\"`]*)\2"
)


def strip_comments(src):
    code = re.sub(r"\{\s*/\*[\s\S]*?\*/\s*\}", ' ', src)
    code = re.sub(r"/\*[\s\S]*?\*/", ' ', code)
    code = re.sub(r"^\s*//.*$", ' ', code, flags=re.M)
    return code


def file_list(rev):
    """Every candidate file at `rev` (or on disk when rev is None).

    os.walk, not os.listdir. git ls-tree -r is RECURSIVE, so listing only the
    immediate children on the working-tree side made the two numbers describe
    different file sets: a fallback in a subdirectory would count on origin/main,
    vanish from the working-tree scan, and be reported as removed when it was
    still there. No such subdirectory exists today, which is exactly why this was
    invisible. Cross-review found it.
    """
    if rev is None:
        out = []
        for p in PREFIXES:
            d = os.path.join(ROOT, p)
            if not os.path.isdir(d):
                continue
            for dirpath, _dirnames, filenames in os.walk(d):
                rel_dir = os.path.relpath(dirpath, ROOT).replace(os.sep, '/')
                out += ['%s/%s' % (rel_dir, n) for n in sorted(filenames)]
        out += [f for f in EXTRA if os.path.isfile(os.path.join(ROOT, f))]
    else:
        listing = _git(['ls-tree', '-r', '--name-only', rev]).splitlines()
        out = [f for f in listing if f.startswith(PREFIXES) or f in EXTRA]
    return [f for f in out if f.endswith(('.tsx', '.ts')) and '__tests__' not in f]


def _git(args):
    """Run git, or stop. A failed git read must not look like an empty result.

    Without the returncode check, `git ls-tree -r origin/main` in a shallow or
    freshly initialised clone exits 128, its empty stdout is read as "no files",
    and the script cheerfully prints `origin/main: 0` -- i.e. claims every
    fabricated citation was removed, which is the exact class of confident wrong
    answer this script exists to detect.
    """
    r = subprocess.run(
        ['git'] + args, cwd=ROOT, capture_output=True, text=True,
        encoding='utf-8', errors='replace', env=git_env(),
    )
    if r.returncode != 0:
        sys.stderr.write('git %s failed (exit %d): %s\n'
                         % (' '.join(args), r.returncode, r.stderr.strip()))
        raise SystemExit(2)
    return r.stdout


def read(rev, f):
    if rev is None:
        try:
            return open(os.path.join(ROOT, f), encoding='utf-8', errors='replace').read()
        except OSError:
            return ''
    return _git(['show', '%s:%s' % (rev, f)])


def count(rev, label):
    hits = []
    files = file_list(rev)
    for f in files:
        src = read(rev, f)
        if not src:
            continue
        for ln, line in enumerate(strip_comments(src).splitlines(), 1):
            for m in STR.finditer(line):
                value = m.group(3)
                # A template literal that INTERPOLATES is not a hardcoded
                # citation -- `Part ${provision.v2_part}` names whatever the data
                # said. Adding backtick support without this turned
                # ExemptComplyingProvisions.tsx:99 into a false positive, and a
                # gate that fires on correct code is one somebody switches off.
                # A backtick literal with no ${ IS hardcoded and still counts.
                if '${' in value:
                    continue
                hits.append((os.path.basename(f), ln, value))
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

# A check that cannot fail is not a check. This printed its numbers and exited 0
# whatever they were, while the QA report chained it after && as though a
# regression would stop the command. A second fabricated citation would have
# printed "working tree: 2" and still passed. Cross-review found it.
#
# ALLOWED states the absence instead of filling it, which is the distinction this
# whole script is about, so it is named rather than counted.
ALLOWED = {'Clause Reference Not Available'}
unexpected = sorted({v for _, _, v in after} - ALLOWED)
if unexpected:
    print('')
    print('FAILED: %d fabricated citation(s) in the working tree: %s'
          % (len(unexpected), ', '.join(unexpected)))
    print('  A clause or instrument substituted when the source carried none.')
    raise SystemExit(1)
print('OK: nothing in the working tree substitutes a citation.')
