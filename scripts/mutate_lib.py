"""Crash-safe mutation harness.

WHY THIS EXISTS. The first version restored each file in a `finally`, which is
useless when the PROCESS is killed: a runner shell timed out at 120 seconds
part-way through a ~10 minute run on 2026-10-06 and left mutation #4 applied to
LandUseZoningCard.tsx. Nothing was committed yet, so `git checkout` would have
destroyed the real work too, and the next run reported a failing baseline that
looked like a broken fix rather than a stranded mutation.

So: before touching anything, every target file is copied to a backup directory
and a marker is written. The marker is removed only after all files are restored.
If a later run finds the marker, it restores from the backups FIRST and says so.
That makes an interrupted run self-healing instead of silently destructive.

Usage:
    from mutate_lib import run
    run(tests=[...], mutations=[(label, path, find, repl, why), ...], tag='cite')
"""
import io
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

# Outside the repo on purpose. The backups below are copies of working-tree
# source, and an interrupted run leaves them on disk; under scripts/ they would
# appear as untracked files during a mutation run, which is exactly when the
# tree has to be readable. Override with MUTATION_STATE_DIR.
_STATE_ROOT = os.environ.get('MUTATION_STATE_DIR') or os.path.join(
    tempfile.gettempdir(), 'plotdetect-mutation-state'
)

# The CHECKOUT this process is mutating. Everything below is namespaced by it.
#
# This directory used to be the repo's own scripts/_mutation_state, which was
# per-checkout for free. Moving it to a machine-wide temp directory took that
# away and created a far worse failure: this repo is routinely worked in several
# git worktrees at once, so an interrupted run in worktree A would leave a marker
# that the next run in worktree B obeys -- restoring A's source files over B's
# legitimate work before the tests even start. Cross-review found it, HIGH.
CHECKOUT = os.getcwd()
_CHECKOUT_KEY = hashlib.sha1(
    os.path.normcase(os.path.abspath(CHECKOUT)).encode('utf-8')
).hexdigest()[:12]
STATE_DIR = os.path.join(_STATE_ROOT, _CHECKOUT_KEY)


def _paths_for(tag):
    base = os.path.join(STATE_DIR, tag)
    return base, os.path.join(base, 'MARKER.json')


def _recover(tag, targets):
    """Restore from a previous interrupted run, if there was one."""
    base, marker = _paths_for(tag)
    if not os.path.isfile(marker):
        return False
    try:
        info = json.load(io.open(marker, encoding='utf-8'))
    except Exception:
        info = {}

    # The hashed STATE_DIR should already make this impossible. Checked anyway:
    # restoring one checkout's source over another's working tree destroys
    # uncommitted work, and a guard against that is worth stating twice. An
    # older marker has no 'checkout' key and is accepted, since it predates the
    # namespacing and cannot have come from elsewhere.
    recorded = info.get('checkout')
    if recorded and os.path.normcase(recorded) != os.path.normcase(os.path.abspath(CHECKOUT)):
        print('!! REFUSING to recover: the marker was written by a different checkout.')
        print('!!   marker: %s' % recorded)
        print('!!   here:   %s' % os.path.abspath(CHECKOUT))
        print('!! Restoring those backups here would overwrite this working tree.')
        raise SystemExit(2)

    print('!! a previous run of this harness did not finish (marker present).')
    print('!! it was interrupted while mutating: %s' % info.get('mutating', 'unknown'))
    restored = []
    for rel in targets:
        backup = os.path.join(base, rel.replace('/', '__'))
        if os.path.isfile(backup):
            shutil.copyfile(backup, rel)
            restored.append(rel)
    print('!! restored %d file(s) from backup: %s' % (len(restored), ', '.join(restored) or 'none'))
    os.remove(marker)
    return True


def _backup(tag, targets):
    base, marker = _paths_for(tag)
    os.makedirs(base, exist_ok=True)
    for rel in targets:
        shutil.copyfile(rel, os.path.join(base, rel.replace('/', '__')))
    _write_marker(marker, None)
    return base, marker


def _write_marker(marker, label):
    """Record WHAT is being mutated and WHICH checkout owns the backups."""
    io.open(marker, 'w', encoding='utf-8').write(json.dumps({
        'mutating': label,
        'checkout': os.path.abspath(CHECKOUT),
    }))


def _note(marker, label):
    _write_marker(marker, label)


def _clear(tag, targets):
    base, marker = _paths_for(tag)
    if os.path.isfile(marker):
        os.remove(marker)
    for rel in targets:
        b = os.path.join(base, rel.replace('/', '__'))
        if os.path.isfile(b):
            os.remove(b)


def _run_tests(tests):
    for test in tests:
        r = subprocess.run(
            ['npx', 'jest', test, '--silent'],
            capture_output=True, text=True,
            # shell only on Windows, where npx is npx.cmd and needs one. On
            # POSIX, shell=True with a LIST passes only the first item as the
            # command and turns the rest into the shell's own positional
            # arguments, so this ran bare `npx` and never ran jest at all.
            # The CI runners are Linux. Cross-review found it.
            shell=(os.name == 'nt'),
            encoding='utf-8', errors='replace',
        )
        if r.returncode != 0:
            return False, test, r.stdout + r.stderr
    return True, None, ''


def run(tests, mutations, tag):
    targets = sorted({m[1] for m in mutations})
    for rel in targets:
        if not os.path.isfile(rel):
            print('ABORT - target not found from this directory: %s' % rel)
            print('        cwd is %s' % os.getcwd())
            return 1

    _recover(tag, targets)

    ok, which, out = _run_tests(tests)
    print('baseline (unmutated): %s' % ('PASSED' if ok else 'FAILED'))
    if not ok:
        print('ABORT - %s does not pass on clean code. Its output:' % which)
        print('\n'.join(out.splitlines()[-25:]))
        return 1

    base, marker = _backup(tag, targets)
    holes = []
    try:
        for label, path, find, repl, why in mutations:
            original = io.open(path, 'rb').read()
            text = original.decode('utf-8')
            if text.count(find) != 1:
                print('  SKIP   %-54s (anchor matched %d times)' % (label, text.count(find)))
                holes.append((label, 'anchor not unique'))
                continue
            _note(marker, label)
            io.open(path, 'wb').write(text.replace(find, repl, 1).encode('utf-8'))
            try:
                passed, _, _ = _run_tests(tests)
            finally:
                io.open(path, 'wb').write(original)
                _note(marker, None)
            print('  %s %-54s  %s' % ('HOLE   ' if passed else 'caught ', label, why))
            if passed:
                holes.append((label, why))
    finally:
        # Belt and braces: re-restore every target from its backup, then drop the marker.
        for rel in targets:
            b = os.path.join(base, rel.replace('/', '__'))
            if os.path.isfile(b):
                shutil.copyfile(b, rel)
        _clear(tag, targets)

    print('')
    print('mutations: %d   caught: %d   holes: %d'
          % (len(mutations), len(mutations) - len(holes), len(holes)))
    for label, why in holes:
        print('  HOLE: %s - %s' % (label, why))

    ok, which, _ = _run_tests(tests)
    print('after restore: %s' % ('PASSED' if ok else 'FAILED (%s)' % which))
    return 1 if (holes or not ok) else 0


if __name__ == '__main__':
    print(__doc__)
    sys.exit(0)
