#!/usr/bin/env python3
"""Plant-restore harness for falsifiability proofs.

prior-art-checked: reuse not viable because no shared plant-restore helper
exists anywhere in the repo. Four sweeps, 2026-08-08 against origin/main
704ccb0f: (1) `git ls-files scripts/ | grep -iE "falsif|plant|restore|mutat"`
returns only mutation_health.py and run_mutation_tests.sh, which drive mutmut
and never edit a file in place; (2) `git grep -n -iE "plant(ed|ing)? (a|the)?
(defect|bug|mutation)"` over py/ts/tsx/sh/md/json returns ZERO; (3)
`git grep -nE "def (plant|restore|prove_falsif|assert_restored)"` returns ZERO;
(4) the only implementation on disk is the throwaway
`<scratchpad>/prove_it_fails.py` from PR #883, never committed. The guard's
suggested files are an error page, two error trackers, a SEPP extractor and a
report page -- none plants or restores anything.

WHY THIS EXISTS
---------------
Every "falsifiability proven" claim this fortnight uses the same technique:
plant a defect, confirm the test goes red, restore the file. Until now it was
open-coded per session, and it failed in both directions:

  * A plant that did not take.  The anchor string was written with LF newlines
    and the working tree is CRLF (``core.autocrlf=true``, verified on this
    repo), so ``find not in original`` -- the file was never modified, the test
    stayed green for the ordinary reason, and the run reported success. A proof
    that never planted anything proves nothing.

  * A restore that did not complete.  The script raised before reaching its
    restore line and left the planted defect in the working tree. It was caught
    by a later grep. It could have shipped.

Even the best of the open-coded versions (``prove_it_fails.py``, PR #883) fails
open on BOTH counts: a missing anchor prints ``!! SKIPPED`` and continues, and
the final byte-identity comparison is a ``print``, not an assert -- it reports
``BYTE-IDENTICAL TO BASELINE: False`` and still exits 0.

So this module enforces the two rules that were missing, and enforces them by
raising, never by warning. A safety check that fails open is not a safety check
(the #880 / #885 lesson).

  RULE 1 -- the plant must demonstrably take.  The file is hashed before and
           after the edit and the hashes must DIFFER, and the bytes on disk
           must be exactly the bytes we meant to write. Anything else raises
           ``PlantDidNotTake``.

  RULE 2 -- the restore must demonstrably complete.  In a ``finally`` block the
           original bytes are written back and the file is re-hashed; the hash
           must equal the original. Anything else raises ``RestoreFailed`` and
           leaves a recovery sidecar on disk.

Newlines are handled explicitly rather than hopefully: everything is bytes
(``read_bytes``/``write_bytes``), never ``read_text``, so there is no decode to
crash on and no newline translation to silently defeat the anchor. The anchor is
matched against the file's own dominant line ending, and the replacement is
rewritten to match it.

CRASH SAFETY
------------
``finally`` covers an exception. It does not cover ``os._exit``, a SIGKILL, or a
power cut. So the original bytes are also written to a sidecar file
(``<file>.falsifiability-bak``) BEFORE the plant and deleted only after a
verified restore. A stale sidecar is therefore hard evidence that a previous run
died mid-plant:

    python scripts/falsifiability.py --check     # exit 1 if any sidecar exists
    python scripts/falsifiability.py --recover   # restore from sidecars

``--check`` runs in .githooks/pre-push, so a planted defect cannot be pushed.

USAGE
-----
    from falsifiability import planted, prove, ProofCase

    with planted(SOLAR, "return round(az, 1)", "return round(az + 5.0, 1)"):
        assert run_tests() != 0        # the test must go RED

or, for a table of cases:

    outcomes = prove([
        ProofCase("DST ignored", SOLAR, "tzinfo=tz", "tzinfo=timezone.utc"),
        ProofCase("inside tolerance", SOLAR, "+ 180.0", "+ 180.15", expect="green"),
    ], run=run_tests)

Output is deliberately ASCII-only. A proof harness that crashes while printing
its own result is the failure it exists to prevent.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterator, Sequence

SIDECAR_SUFFIX = ".falsifiability-bak"

RECOVER_HINT = "python scripts/falsifiability.py --recover"

_CRLF = b"\r\n"
_LF = b"\n"


class FalsifiabilityError(AssertionError):
    """Base class. Subclasses AssertionError so a bare pytest run reports it."""


class PlantDidNotTake(FalsifiabilityError):
    """Rule 1 violated: the file was not changed the way the caller asked."""


class RestoreFailed(FalsifiabilityError):
    """Rule 2 violated: the file was not returned to its original bytes."""


class StalePlantFound(FalsifiabilityError):
    """A sidecar from an earlier run is still on disk -- damage may be live."""


# --- hashing ----------------------------------------------------------------


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


# --- newline handling -------------------------------------------------------
#
# The CRLF no-op is not a rare edge case here: `git config core.autocrlf` is
# `true` on this repo, so every checked-out .py/.ts/.md file has CRLF line
# endings while every anchor typed into a Python source literal has LF. A
# multi-line anchor therefore matches NOTHING unless it is translated first.


def dominant_newline(blob: bytes) -> bytes:
    """The line ending the file actually uses. Ties and empties resolve to LF."""
    crlf = blob.count(_CRLF)
    lf = blob.count(_LF) - crlf
    return _CRLF if crlf > lf else _LF


def _retype_newlines(chunk: bytes, newline: bytes) -> bytes:
    return chunk.replace(_CRLF, _LF).replace(_LF, newline)


def _as_bytes(value: str | bytes) -> bytes:
    return value if isinstance(value, bytes) else value.encode("utf-8")


def _anchor_candidates(find: bytes, newline: bytes) -> list[tuple[str, bytes]]:
    """The anchor exactly as written, then translated to the file's newline."""
    out: list[tuple[str, bytes]] = [("as-written", find)]
    translated = _retype_newlines(find, newline)
    if translated != find:
        style = "CRLF-translated" if newline == _CRLF else "LF-translated"
        out.append((style, translated))
    return out


def _locate(blob: bytes, find: bytes, tag: str) -> tuple[str, bytes]:
    """Return (style, anchor) for the one unambiguous match, or raise.

    A missing anchor and an ambiguous anchor are BOTH failures. The open-coded
    versions skipped on a miss; a skip inside a long run reads as success, and
    an ambiguous anchor plants the defect somewhere the caller did not choose,
    which makes the red result describe a different bug.
    """
    newline = dominant_newline(blob)
    tried: list[str] = []
    for style, candidate in _anchor_candidates(find, newline):
        count = blob.count(candidate)
        tried.append(f"{style}={count}")
        if count == 1:
            return style, candidate
        if count > 1:
            raise PlantDidNotTake(
                f"{tag}: anchor is AMBIGUOUS -- it occurs {count} times "
                f"({style}). A plant must land where the caller intended, so "
                f"widen the anchor until it is unique."
            )
    raise PlantDidNotTake(
        f"{tag}: anchor NOT FOUND -- nothing was planted, so a green result "
        f"would have meant nothing. Match attempts: {', '.join(tried)}. The "
        f"file's dominant line ending is "
        f"{'CRLF' if newline == _CRLF else 'LF'}; if the anchor spans lines, "
        f"that is the usual cause. Anchor was: {find[:120]!r}"
    )


# --- the context manager ----------------------------------------------------


def _write_sidecar(sidecar: Path, original: bytes, tag: str) -> None:
    """Claim the sidecar atomically and leave it complete, or not at all.

    Two properties, and both were earned:

    COMPLETE -- a plain ``write_bytes`` leaves a window in which a kill
    produces a SHORT sidecar, and ``--recover`` would then overwrite the target
    with truncated bytes and report 'restored'. A backup that can be silently
    wrong is worse than no backup, because it is trusted. So the bytes are
    written to a private temp file and fsynced BEFORE the sidecar name exists.

    EXCLUSIVE -- ``sidecar.exists()`` followed by a create is check-then-act.
    Two concurrent plants on the same file (pytest-xdist is installed, though
    not enabled by default) would both see no sidecar, both proceed, and the
    first restore would delete the evidence of the second. ``os.link`` is
    atomic and raises FileExistsError, so the claim and the check are one
    operation.
    """
    tmp = sidecar.with_name(f"{sidecar.name}.{os.getpid()}.tmp")
    with open(tmp, "wb") as handle:
        handle.write(original)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        try:
            os.link(tmp, sidecar)
        except FileExistsError:
            raise StalePlantFound(
                f"{tag}: {sidecar.name} was claimed by another run between the "
                f"start of this one and now. Two proofs are planting into the "
                f"same file concurrently, or an earlier one died mid-plant. "
                f"Refusing to proceed: {RECOVER_HINT}"
            ) from None
        except (OSError, NotImplementedError) as exc:
            # Filesystems without hard links (some network and FAT volumes).
            # os.replace would keep COMPLETE but NOT EXCLUSIVE, and a weaker
            # guarantee that looks like the strong one is precisely the pattern
            # this module exists to remove. Fail closed and say why.
            raise FalsifiabilityError(
                f"{tag}: cannot claim {sidecar.name} atomically -- os.link is "
                f"unavailable on this filesystem ({exc}). Continuing would mean "
                f"two concurrent plants could overwrite each other's recovery "
                f"evidence and leave a mutation on disk with no sidecar to find "
                f"it. Run the proof from a filesystem that supports hard links."
            ) from exc
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass
    _fsync_dir(sidecar.parent)


def _fsync_dir(directory: Path) -> None:
    """Best effort: make the sidecar's directory entry durable.

    Only matters for real power loss. The failure that actually occurred was a
    process dying, and the page cache serves the file to the next process
    regardless, so the guard works without this. Windows cannot open a
    directory for fsync at all, so this is a no-op there -- recorded rather
    than implied away.
    """
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


@dataclass(frozen=True)
class PlantInfo:
    """What was actually done to the file, for the record."""

    label: str
    path: Path
    sha_before: str
    sha_planted: str
    anchor_style: str


@contextmanager
def planted(
    path: str | Path,
    find: str | bytes,
    replace: str | bytes,
    *,
    label: str = "",
) -> Iterator[PlantInfo]:
    """Plant a defect, run the caller's body, restore -- both rules enforced.

    Raises ``PlantDidNotTake`` before the body runs if the edit did not change
    the file's hash to exactly the intended value, and ``RestoreFailed`` after
    it if the file did not come back to its original hash.

    If the body raises AND the restore fails, ``RestoreFailed`` is what
    propagates -- damage left on disk outranks a failed assertion. The body's
    exception is preserved on ``__context__``, so nothing is lost.
    """
    path = Path(path)
    tag = label or path.name

    if not path.is_file():
        raise PlantDidNotTake(f"{tag}: {path} does not exist -- nothing to plant into.")

    sidecar = path.with_name(path.name + SIDECAR_SUFFIX)
    if sidecar.exists():
        raise StalePlantFound(
            f"{tag}: {sidecar.name} already exists. An earlier run died mid-plant "
            f"and {path} may still hold a planted defect. Refusing to start -- "
            f"resolve it first: {RECOVER_HINT}"
        )

    original = path.read_bytes()
    sha_before = sha256_bytes(original)

    style, anchor = _locate(original, _as_bytes(find), tag)
    newline = dominant_newline(original)
    replacement = _retype_newlines(_as_bytes(replace), newline)
    mutated = original.replace(anchor, replacement, 1)
    sha_planted = sha256_bytes(mutated)

    if sha_planted == sha_before:
        raise PlantDidNotTake(
            f"{tag}: the replacement is byte-identical to the anchor, so the "
            f"file would not change. sha256 stays {sha_before[:12]}. This is a "
            f"no-op dressed as a mutation."
        )

    # Sidecar FIRST. If the process is killed between here and the restore,
    # the original bytes still exist on disk and --recover can put them back.
    _write_sidecar(sidecar, original, tag)

    try:
        path.write_bytes(mutated)

        # RULE 1. Read back from disk -- not from the buffer we just built.
        # An editor, a filesystem, or a newline-translating layer can turn the
        # write into something other than what was asked for, and the whole
        # point is that we do not take "it probably worked" for an answer.
        on_disk = sha256_file(path)
        if on_disk == sha_before:
            raise PlantDidNotTake(
                f"{tag}: the write did NOT take -- {path} still hashes to its "
                f"original {sha_before[:12]}. A test run now would be "
                f"meaningless, not reassuring."
            )
        if on_disk != sha_planted:
            raise PlantDidNotTake(
                f"{tag}: the bytes on disk are not the bytes we meant to write "
                f"(disk {on_disk[:12]}, intended {sha_planted[:12]}). Some layer "
                f"rewrote the content; an unknown mutation cannot prove anything "
                f"about a known one."
            )

        yield PlantInfo(
            label=tag,
            path=path,
            sha_before=sha_before,
            sha_planted=sha_planted,
            anchor_style=style,
        )
    finally:
        _restore(path, original, sha_before, sidecar, tag)


def _restore(
    path: Path, original: bytes, sha_before: str, sidecar: Path, tag: str
) -> None:
    """RULE 2. Write the original back and PROVE it by hash, or raise."""
    last_error: BaseException | None = None
    for _ in range(2):
        try:
            path.write_bytes(original)
        except OSError as exc:  # transient lock (antivirus, indexer) -- retry once
            last_error = exc
            continue
        if sha256_file(path) == sha_before:
            sidecar.unlink(missing_ok=True)
            return

    try:
        now = sha256_file(path)
    except OSError:
        now = "unreadable"
    raise RestoreFailed(
        f"{tag}: RESTORE FAILED -- {path} does not hash to its original value. "
        f"expected {sha_before[:12]}, on disk {now[:12]}. The planted defect may "
        f"still be in the working tree. Original bytes are preserved at "
        f"{sidecar.name}; recover with: {RECOVER_HINT}"
    ) from last_error


# --- the runner -------------------------------------------------------------


@dataclass(frozen=True)
class ProofCase:
    """One planted defect and what the check is expected to do about it."""

    label: str
    path: str | Path
    find: str | bytes
    replace: str | bytes
    expect: str = "red"  # "red" = the check must fail; "green" = must still pass


@dataclass
class ProofOutcome:
    label: str
    expect: str
    returncode: int
    detail: str
    ok: bool
    plant: PlantInfo | None = None


@dataclass
class ProofReport:
    outcomes: list[ProofOutcome] = field(default_factory=list)
    baseline_returncode: int = 0
    final_returncode: int = 0

    @property
    def ok(self) -> bool:
        return (
            bool(self.outcomes)
            and all(o.ok for o in self.outcomes)
            and self.baseline_returncode == 0
            and self.final_returncode == 0
        )

    def table(self) -> str:
        width = max([len(o.label) for o in self.outcomes] + [8])
        lines = [
            f"{'case':<{width}}  {'expect':<6}  {'rc':>4}  {'verdict':<18}  detail",
            "-" * (width + 48),
        ]
        for o in self.outcomes:
            verdict = "CAUGHT" if o.expect == "red" else "STAYED GREEN"
            if not o.ok:
                verdict = "*** MISSED ***" if o.expect == "red" else "*** FALSE ALARM ***"
            lines.append(
                f"{o.label:<{width}}  {o.expect:<6}  {o.returncode:>4}  "
                f"{verdict:<18}  {o.detail[:60]}"
            )
        return "\n".join(lines)


def prove(
    cases: Sequence[ProofCase],
    run: Callable[[], tuple[int, str]],
    *,
    require_green_baseline: bool = True,
) -> ProofReport:
    """Run ``run`` once clean, once per planted defect, and once clean again.

    ``run`` returns ``(returncode, one_line_detail)``. A non-zero return code is
    RED. Every plant is enforced by :func:`planted`, so a case that could not be
    planted raises rather than being recorded as a pass.

    The trailing clean run is not ceremony: it is the only evidence that the
    file the suite saw at the end is the file it saw at the start.
    """
    report = ProofReport()

    report.baseline_returncode, detail = run()
    if require_green_baseline and report.baseline_returncode != 0:
        raise FalsifiabilityError(
            f"the check is already RED before anything was planted (rc="
            f"{report.baseline_returncode}: {detail}). Every subsequent red "
            f"would be unattributable. Fix the baseline first."
        )

    for case in cases:
        with planted(case.path, case.find, case.replace, label=case.label) as info:
            rc, detail = run()
        ok = (rc != 0) if case.expect == "red" else (rc == 0)
        report.outcomes.append(
            ProofOutcome(case.label, case.expect, rc, detail, ok, info)
        )

    report.final_returncode, _ = run()
    return report


def pytest_runner(
    targets: Sequence[str], cwd: str | Path, *, timeout: int = 900
) -> Callable[[], tuple[int, str]]:
    """A ``run`` callable for the common case: some pytest files, quietly."""

    def _run() -> tuple[int, str]:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", *targets, "-q", "--tb=no"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # a decode error must never crash the harness
            timeout=timeout,
        )
        tail = [
            ln for ln in proc.stdout.splitlines() if "passed" in ln or "failed" in ln
        ]
        return proc.returncode, (tail[-1] if tail else proc.stdout.strip()[-160:])

    return _run


# --- sidecar recovery -------------------------------------------------------


def find_sidecars(root: str | Path) -> list[Path]:
    """Every recovery sidecar under ``root``. Each one is unfinished business."""
    return sorted(Path(root).rglob("*" + SIDECAR_SUFFIX))


def recover(root: str | Path, *, apply: bool = False) -> list[tuple[Path, str]]:
    """Report (and optionally undo) every planted defect left on disk.

    Returns (target_path, status) pairs. ``status`` is one of ``restored``,
    ``already-clean``, ``WOULD-RESTORE`` or ``FAILED: ...``.
    """
    results: list[tuple[Path, str]] = []
    for sidecar in find_sidecars(root):
        target = sidecar.with_name(sidecar.name[: -len(SIDECAR_SUFFIX)])
        original = sidecar.read_bytes()
        want = sha256_bytes(original)
        if target.is_file() and sha256_file(target) == want:
            status = "already-clean"
            if apply:
                sidecar.unlink()
        elif not apply:
            status = "WOULD-RESTORE"
        else:
            target.write_bytes(original)
            if sha256_file(target) == want:
                sidecar.unlink()
                status = "restored"
            else:
                status = "FAILED: write did not stick"
        results.append((target, status))
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Falsifiability plant-restore harness -- sidecar tooling."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any planted defect was left on disk by an earlier run",
    )
    parser.add_argument(
        "--recover", action="store_true", help="restore every file from its sidecar"
    )
    parser.add_argument("--root", default=".", help="directory to scan (default: .)")
    args = parser.parse_args(argv)

    if not (args.check or args.recover):
        parser.print_help()
        return 0

    results = recover(args.root, apply=args.recover)
    if not results:
        print("FALSIFIABILITY: clean -- no planted defects left on disk.")
        return 0

    verb = "recovered" if args.recover else "FOUND"
    print(f"FALSIFIABILITY: {verb} {len(results)} planted file(s):")
    for target, status in results:
        print(f"  - {target}: {status}")
    if args.recover:
        return 1 if any(s.startswith("FAILED") for _, s in results) else 0

    print()
    print("A proof run died before restoring its plant. Do NOT commit or push")
    print(f"until this is resolved: {RECOVER_HINT}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
