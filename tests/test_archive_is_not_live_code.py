"""scripts/archive/ is exempt from the QA gate's content scanners. This is the
guard that stops that exemption becoming a way to smuggle live code past them.

WHY THE EXEMPTION EXISTS. Backing up 797 scripts that lived on one laptop and
nowhere else tripped three gates in turn — the zone-code lint on 31 files, the
Python adversarial scanner on 74, the DB currency guard on 134. Every finding
was real and every one was in a years-old throwaway script. The gates cannot
tell "newly written" from "newly tracked", and for a backup those are opposite
things. So archive/ holds retired one-off scripts, and the scanners skip it.

WHY THIS TEST. An exemption nobody polices is an invitation. If live code can
be parked in archive/ and then imported, the exemption stops being about dead
scripts and starts being a hole in every content scanner at once. So the rule
that makes the exemption safe — nothing outside archive/ depends on anything
inside it — is asserted here rather than written in a comment.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ARCHIVE = _ROOT / "scripts" / "archive"

# `from scripts.archive.x import y`, `import scripts.archive.x`,
# `from archive.x import y` and a bare `import archive` — plus the string form
# a subprocess call would use.
_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+(?:scripts\.)?archive[\s.]", re.M),
    re.compile(r"^\s*import\s+(?:scripts\.)?archive\b", re.M),
]
_PATH_PATTERN = re.compile(r"scripts[/\\]archive[/\\]")

_SEARCH_DIRS = ("scripts", "services", "enrichment", "src", "tests", ".githooks")
_SKIP_PARTS = {"__pycache__", "node_modules", ".git", "venv_linux", "archive"}


def _candidate_files() -> list[Path]:
    out: list[Path] = []
    for d in _SEARCH_DIRS:
        root = _ROOT / d
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if p.suffix not in (".py", ".sh", ".yml", ".yaml"):
                continue
            if _SKIP_PARTS & set(p.parts):
                continue
            out.append(p)
    return out


def test_nothing_outside_archive_imports_from_it():
    """The rule that makes the scanner exemption safe."""
    offenders: list[str] = []
    for p in _candidate_files():
        text = p.read_text(encoding="utf-8", errors="replace")
        if any(pat.search(text) for pat in _IMPORT_PATTERNS):
            offenders.append(f"{p.relative_to(_ROOT)} imports from scripts/archive/")
    assert not offenders, (
        "scripts/archive/ is exempt from the QA gate's content scanners because "
        "it holds retired scripts nothing runs. Importing from it makes that "
        "exemption a hole in every scanner at once:\n  " + "\n  ".join(offenders)
    )


def test_nothing_outside_archive_shells_out_to_it():
    """Same rule, second route in. An exemption that only covers `import` is
    trivially walked around with subprocess."""
    # These NAME the path in order to EXCLUDE it — the definition sites of the
    # rule, not dependencies on it. Listed by exact filename rather than by
    # pattern so a new file cannot quietly inherit the exemption: this test
    # correctly failed when lint_hardcoded_zone_codes.py became the second
    # definition site and had not been added here.
    definition_sites = {
        "qa_gate.py",                     # content scanners skip the archive
        "lint_hardcoded_zone_codes.py",   # zone lint skips it, same reasoning
        "liability_language_check.py",    # language scan skips it, same reasoning
        Path(__file__).name,
    }
    offenders: list[str] = []
    for p in _candidate_files():
        if p.name in definition_sites:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if _PATH_PATTERN.search(text):
            offenders.append(f"{p.relative_to(_ROOT)} references a scripts/archive/ path")
    assert not offenders, (
        "a scripts/archive/ path is referenced outside the archive. If something "
        "needs to RUN it, it is not retired and belongs in scripts/ under the "
        "guards:\n  " + "\n  ".join(offenders)
    )


def test_the_search_actually_looks_at_files():
    """Control case.

    Both assertions above are `not offenders`, which an empty candidate list
    satisfies completely — a broken glob or a wrong root would make this file
    pass while checking nothing. So assert the search finds a corpus, and that
    it finds a file known to exist in it.
    """
    files = _candidate_files()
    assert len(files) > 50, f"only {len(files)} files searched - the glob is broken"
    names = {f.name for f in files}
    assert "qa_gate.py" in names, "qa_gate.py not in the searched set"


def test_archive_is_excluded_by_the_gate_not_merely_absent():
    """If scripts/archive/ does not exist yet, the exemption is untested rather
    than proven. Assert the gate carries the filter regardless, so deleting the
    directory cannot silently retire this rule."""
    gate = (_ROOT / "scripts" / "qa_gate.py").read_text(encoding="utf-8")
    assert "scripts/archive/" in gate, (
        "qa_gate.py no longer filters scripts/archive/ - either the exemption "
        "was removed (then delete this test) or it was renamed (then update it)"
    )
    assert "live_files" in gate, "the filtered list is no longer passed to the scanners"
