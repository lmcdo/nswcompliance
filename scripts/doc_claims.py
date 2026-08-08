#!/usr/bin/env python3
"""Doc-claim check -- the tractable half of "is this document still true?".

prior-art-checked: reuse not viable because nothing in the repo checks a
document's claims against code. Four sweeps, 2026-08-08 against origin/main
704ccb0f: (1) `git ls-files scripts/ | grep -iE "doc|claim|lint"` yields
lint_hardcoded_zone_codes.py, lint_hardcoded_confidence.py and
lint_fabricated_verdicts.py -- all three lint CODE, none reads a doc;
(2) `git grep -niE "doc.?claim|stale doc|doc decay|documentation drift"` over
py/sh/yml returns ZERO; (3) scripts/check_dcp_as_at_coverage.py,
check_satellite_manifests.py and check_ts_dcp_readers.py check DATA and code
readers, not prose; (4) the plan doc's own section 4i says of this exact idea
"Noted, not yet machinery." This is the machinery.

WHY
---
Four times in two days a session acted on a false premise that came from a
DOCUMENT rather than from code:

  * services/CLAUDE.md claimed Threat Radar shares the Sentinel-2 pipeline. It
    never has -- zero references in threat_radar.py. Three sessions inherited
    the false premise and one shipped a wrong surface list (#886, section 4i).
  * "13/16 human confirmations" that were, on measurement, zero.
  * A pre-written APRA correlation test that did not exist in any branch (#887).
  * A "v1.2 changelog entry" for a module whose only version entry is 1.1.

Code is checked six ways in scripts/qa_gate.py alone. The documents describing
the code are not checked at all. This closes the part of that gap a machine can
actually decide.

WHAT IT CATCHES -- and, just as importantly, what it does not
------------------------------------------------------------
  PATH        a file, test or module path named in a doc or QA report that does
              not resolve.  (Would have caught the APRA test that never existed.)
  VERSION     a version literal on a line that names a code version identifier,
              where the identifier does not hold that value in code.
              (Would have caught v1.2, and v1.1 beside a v1.0 disclaimer.)
  DEPENDENCY  a requirements file no installer reads, and a package that tests
              import but CI never installs.  (Would have caught #880: icontract
              declared only in scripts/requirements-maintenance.txt, which the
              service container and CI both ignore, so four liability-critical
              postconditions were decorative for as long as they existed.)

It will NOT catch "Threat Radar uses this pipeline", "13 people confirmed", or
any other semantic claim about behaviour or provenance. Those need a reader, not
a parser. Three of the four incidents above are only PARTLY covered, and the
Threat Radar one is not covered at all. Do not read a green run as "the docs are
true" -- read it as "no path, version or dependency claim is decidably false".

Anything it cannot decide is reported as a NOTE, never counted as a pass. An
unmapped import name, an unreadable file and a missing git index are all
"unknowable", which is a reportable outcome and not a clean bill of health.

OBSERVATION MODE
----------------
Reports; blocks nothing. `--strict` exists but is wired into no hook and no
gate. A lint that blocked a routine merge on day one is already in this
project's incident log (DQ-34, alarm fatigue); blocking status is earned with an
observed false-positive rate, not assumed.

    python scripts/doc_claims.py                     # scan the default doc set
    python scripts/doc_claims.py --docs a.md b.md    # scan specific files
    python scripts/doc_claims.py --init              # write the baseline
    python scripts/doc_claims.py --compare           # only what is NEW vs baseline
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

BASELINE_PATH = Path("scripts/baselines/doc-claim-baseline.json")

# Archived narrative. It describes a repo that no longer exists and is meant to;
# checking it would produce hundreds of findings about deliberate history.
EXCLUDED_DOC_PREFIXES = (".claude/docs/history/",)

DEFAULT_DOC_GLOBS = (
    "docs/**/*.md",
    "CLAUDE.md",
    "*/CLAUDE.md",
    ".claude/rules/*.md",
    ".claude/DATA_QUALITY_TRACKER.md",
)

DEFAULT_REPORTS = (".qa_report.json",)

# Extensions worth resolving. .md and .json are deliberately out of scope: doc
# to doc links are a different problem with a different failure mode, and prose
# mentions of "report.json" would swamp the signal.
_PATH_EXTS = "py|ts|tsx|js|jsx|mjs|sql|sh|yml|yaml|txt|toml|cfg|ini"

_PATH_RE = re.compile(
    # Three boundary rules, each earned by a false positive in the first run:
    #  - no leading '-', or a markdown bullet is absorbed ("-paywall.test.ts");
    #  - no leading '>', '}', ']', '*' or '?', or the tail of a placeholder or
    #    glob becomes a claim ("<council>_config.py" was reported as
    #    "_config.py", "scripts/insert_*_parking.py" as "_parking.py");
    #  - a trailing boundary, or `shapely.geometry.shape` matches as a `.sh`
    #    file and `ShadowTool.tsx` matches as `ShadowTool.ts` (the ext
    #    alternation is first-match, so `ts` wins over `tsx` without it).
    r"(?<![\w./>}\]*?-])((?:[A-Za-z0-9_.+-]+/)*[A-Za-z0-9_+][A-Za-z0-9_.+-]*"
    r"\.(?:" + _PATH_EXTS + r"))(?![A-Za-z0-9_])(?::(\d+))?"
)

# Product names that happen to be shaped like files. Matching these is a defect
# in the check, not a claim in the document.
_NOT_PATHS = {
    "next.js", "node.js", "react.js", "vue.js", "d3.js", "chart.js",
    "express.js", "three.js", "next.config.js", "socket.io",
}

# A token that is an illustration, not a claim.
_PLACEHOLDER_RE = re.compile(
    r"[*?<>{}$\\]|\.\.\.|path/to/|your[-_/]|example\.|foo\.|bar\."
    r"|\b(?:XXX|NNN|YYY|ZZZ)\b|/(?:XXX|NNN)"
)

# When a claimed path fails, try these swaps before reporting. A doc that says
# `.ts` for a `.tsx` file is still wrong -- a grep for it finds nothing -- but
# the finding is only actionable if it says what the real extension is.
_EXT_ALTERNATIVES = {
    ".ts": (".tsx",),
    ".tsx": (".ts",),
    ".js": (".jsx", ".mjs", ".ts"),
    ".yml": (".yaml",),
    ".yaml": (".yml",),
}

_URL_RE = re.compile(r"https?://\S+|\bwww\.\S+")

# `NAME = "1.2"`, `methodology_version: str = "1.1"`, `const X_VERSION = '2.0'`.
# The (?:VERSION|Version|version) alternation is load-bearing: `[Vv]ersion`
# missed every SCREAMING_CASE constant, which is how this repo writes most of
# them (ENRICHMENT_VERSION, PIPELINE_VERSION, METHODOLOGY_VERSION). A test
# caught it; the first live baseline was taken with lowercase names only.
_CODE_VERSION_RE = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:VERSION|Version|version))\s*"
    r"(?::\s*[A-Za-z_][A-Za-z0-9_.\[\]\"' ]*\s*)?"
    r"=\s*[\"'](?P<value>v?\d+(?:\.\d+)+)[\"']"
)

# The trailing guard is `(?!\.\d)`, not `(?![\w.])`: the latter refuses to match
# a version that ends a sentence ("documents v1.2.") because the full stop looks
# like another segment. It must still refuse the PREFIX of a longer version, so
# only a dot FOLLOWED BY A DIGIT disqualifies.
_VERSION_VALUE_RE = re.compile(r"\d+(?:\.\d+)+")

_TS_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
_TS_LINE_COMMENT_RE = re.compile(r"(?<!:)//[^\n]*")

_DOC_VERSION_RE = re.compile(r"(?<![\w.])v?(\d+(?:\.\d+)+)(?!\w)(?!\.\d)")

# How far from the named identifier a version literal still counts as a claim
# about it. Chosen so `methodology_version is '1.1'` and `the changelog
# documents v1.2, methodology_version is '1.1'` both bind, while a threshold
# two sentences away does not.
_VERSION_WINDOW = 90

# A bare `-r file.txt` is not an installation. `test -r requirements-extra.txt`
# checks readability and installs nothing, and counting it would suppress the
# orphan finding for that file. So the line must carry a real pip invocation
# first, and both `-r` and `--requirement` (with space or =) are accepted --
# the long form was silently missed.
_PIP_INSTALL_RE = re.compile(
    r"\b(?:pip[\d.]*|python[\d.]*\s+-m\s+pip|uv\s+pip)\s+install\b", re.I
)
_PIP_INSTALL_R_RE = re.compile(r"(?:-r|--requirement)[=\s]+([A-Za-z0-9_./-]+\.txt)")

_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")

# Import name -> distribution name, for the cases where they differ in THIS
# repo's requirements files. Anything absent from this table and not matching a
# declared distribution is reported as unknowable, never as a violation.
_IMPORT_ALIASES = {
    "fitz": "pymupdf",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "psycopg2": "psycopg2-binary",
    "PIL": "pillow",
    "osgeo": "gdal",
    "dateutil": "python-dateutil",
    "bs4": "beautifulsoup4",
}


@dataclass(frozen=True)
class Violation:
    kind: str  # "path" | "version" | "dependency"
    doc: str
    line: int
    claim: str
    detail: str

    def fingerprint(self) -> str:
        """Stable across line moves -- identifies a claim, not a location."""
        return f"{self.kind}|{self.doc}|{self.claim}"

    def render(self) -> str:
        where = f"{self.doc}:{self.line}" if self.line else self.doc
        return f"[{self.kind}] {where}: {self.claim} -- {self.detail}"


def _count_kinds(violations: Sequence["Violation"]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in violations:
        out[v.kind] = out.get(v.kind, 0) + 1
    return out


@dataclass
class ScanResult:
    violations: list[Violation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    docs_scanned: int = 0

    def by_kind(self) -> dict[str, int]:
        return _count_kinds(self.violations)


# --- repo facts -------------------------------------------------------------


def git_env() -> dict[str, str]:
    """The environment with git's per-invocation variables removed.

    A git hook exports GIT_DIR, GIT_INDEX_FILE and friends, and they OVERRIDE
    cwd. Without this, running the check from .githooks/pre-push makes
    `git ls-files` answer about the hook's repository rather than the one being
    scanned -- a silently wrong file list, which is the whole class of defect
    this module exists to find. Discovered by the pre-push hook itself.
    """
    return {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("GIT_")
        or k in ("GIT_ASKPASS", "GIT_SSH", "GIT_SSH_COMMAND")
    }


def tracked_files(project_dir: Path) -> set[str] | None:
    """Every tracked path, POSIX-separated. None if git cannot answer."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env=git_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def _read(path: Path) -> str | None:
    """Bytes then decode-with-replace. A mojibake byte must not crash a check."""
    try:
        return path.read_bytes().decode("utf-8", errors="replace")
    except OSError:
        return None


# --- check A: paths ---------------------------------------------------------


def _resolvable(
    token: str,
    project_dir: Path,
    tracked: set[str],
    basenames: dict[str, list[str]],
    doc: str = "",
) -> tuple[str, bool] | None:
    """Return (resolved repo-relative path, unambiguous), or None.

    The ambiguity flag matters: a doc that writes a bare `route.ts` names one of
    47 files, so the path claim is satisfied but a `route.ts:548` line claim
    cannot be checked against an arbitrary one of them. Reporting a line-count
    finding off the wrong file would be a fabricated finding.
    """
    if token in tracked:
        return token, True

    # `../../frontend-nextjs/x.tsx` in docs/qa/y.md is relative to the DOC.
    if token.startswith("../") and doc:
        rel = (Path(doc).parent / token).as_posix()
        rel = Path(rel).resolve().as_posix() if ".." in rel else rel
        try:
            rel = Path((project_dir / doc).parent.joinpath(token).resolve()).relative_to(
                project_dir
            ).as_posix()
        except (ValueError, OSError):
            rel = ""
        if rel and rel in tracked:
            return rel, True

    suffix = "/" + token
    matches = [c for c in tracked if c.endswith(suffix)]
    if matches:
        return matches[0], len(matches) == 1

    hits = basenames.get(token.rsplit("/", 1)[-1])
    if hits:
        return hits[0], len(hits) == 1
    return None


def _near_miss(
    token: str,
    project_dir: Path,
    tracked: set[str],
    basenames: dict[str, list[str]],
    doc: str = "",
) -> str | None:
    """If only the extension is wrong, say which one is right."""
    dot = token.rfind(".")
    if dot < 0:
        return None
    stem, ext = token[:dot], token[dot:]
    for alt in _EXT_ALTERNATIVES.get(ext, ()):
        hit = _resolvable(stem + alt, project_dir, tracked, basenames, doc)
        if hit:
            found = hit[0]
            return (
                f"no such file -- the real path is {found} ({alt}, not {ext}), "
                f"so a grep for the name as written finds nothing"
            )
    return None


def check_paths(
    doc: str,
    text: str,
    project_dir: Path,
    tracked: set[str],
    basenames: dict[str, list[str]],
) -> list[Violation]:
    out: list[Violation] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = _URL_RE.sub(" ", line)
        for match in _PATH_RE.finditer(stripped):
            token, lineref = match.group(1), match.group(2)
            if token.lower() in _NOT_PATHS:
                continue
            if _PLACEHOLDER_RE.search(token) or token.startswith(
                ("node_modules/", "venv", ".venv")
            ):
                continue
            found = _resolvable(token, project_dir, tracked, basenames, doc)
            if found is None:
                # An UNTRACKED file that happens to be on this machine is not a
                # resolved claim: a fresh clone would not have it, so accepting
                # it would make the result depend on whose laptop ran the check.
                # Reported separately rather than silently passing.
                if ".." not in token and (project_dir / token).exists():
                    out.append(
                        Violation(
                            "path",
                            doc,
                            lineno,
                            token,
                            "exists on this machine but is NOT tracked -- a fresh "
                            "clone would not have it, so the doc instructs people "
                            "to use a file they will not receive",
                        )
                    )
                    continue
                out.append(
                    Violation(
                        "path",
                        doc,
                        lineno,
                        token,
                        _near_miss(token, project_dir, tracked, basenames, doc)
                        or "no such file is tracked or on disk -- the doc names "
                        "something that does not exist",
                    )
                )
                continue
            resolved, unambiguous = found
            # A line claim needs ONE file to check against. Against an
            # arbitrary same-named file the finding would be invented.
            if lineref and unambiguous:
                body = _read(project_dir / resolved)
                if body is None:
                    continue
                total = len(body.splitlines())
                if int(lineref) > total:
                    out.append(
                        Violation(
                            "path",
                            doc,
                            lineno,
                            f"{token}:{lineref}",
                            f"{resolved} has only {total} lines -- the cited "
                            f"line does not exist",
                        )
                    )
    return out


# --- check B: versions ------------------------------------------------------


def code_version_constants(
    project_dir: Path, tracked: set[str]
) -> dict[str, set[str]]:
    """identifier (lowercased) -> every literal value it is assigned in code.

    Values are unioned ACROSS FILES, which is a real weakness: two products can
    both define `methodology_version`, and a doc for one of them naming the
    other's value would be accepted. Resolving which module a document is about
    needs a reader, so instead every multi-valued identifier is reported as
    ambiguous by :func:`ambiguous_identifiers` and the caller emits an
    unknowable note. A literal matching NO file's value is still a finding --
    that case is unaffected by the ambiguity, and it is the v1.2 case.
    """
    out: dict[str, set[str]] = {}
    for rel in tracked:
        if not rel.endswith((".py", ".ts", ".tsx")):
            continue
        if rel.startswith("tests/") or "/__tests__/" in rel or ".test." in rel:
            continue
        body = _read(project_dir / rel)
        if body is None:
            continue
        for name, value in _version_assignments(rel, body):
            out.setdefault(name, set()).add(value)
    return out


def _version_assignments(rel: str, body: str) -> list[tuple[str, str]]:
    """(identifier, value) pairs that are LIVE assignments, not text.

    Python goes through ast, so a constant mentioned in a docstring, a comment
    or an example string is not mistaken for a value the code holds -- which
    would silently accept a document claiming that version. TypeScript has no
    stdlib parser, so comments are stripped and the regex still runs over
    string literals; that residual gap is stated rather than papered over.
    """
    pairs: list[tuple[str, str]] = []
    if rel.endswith(".py"):
        try:
            tree = ast.parse(body)
        except SyntaxError:
            return pairs
        for node in ast.walk(tree):
            targets: list[ast.expr] = []
            if isinstance(node, ast.Assign):
                targets = list(node.targets)
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                continue
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            literal = value.value.lstrip("vV")
            if not _VERSION_VALUE_RE.fullmatch(literal):
                continue
            for target in targets:
                name = getattr(target, "id", None) or getattr(target, "attr", None)
                if name and name.lower().endswith("version"):
                    pairs.append((name.lower(), literal))
        return pairs

    stripped = _TS_BLOCK_COMMENT_RE.sub(" ", body)
    stripped = _TS_LINE_COMMENT_RE.sub(" ", stripped)
    for match in _CODE_VERSION_RE.finditer(stripped):
        pairs.append(
            (match.group("name").lower(), match.group("value").lstrip("vV"))
        )
    return pairs


def ambiguous_identifiers(constants: dict[str, set[str]]) -> list[str]:
    """Identifiers that hold more than one value across the repository."""
    return sorted(name for name, values in constants.items() if len(values) > 1)


def check_versions(
    doc: str, text: str, constants: dict[str, set[str]]
) -> tuple[list[Violation], list[str]]:
    """A version literal must match the code identifier named beside it.

    Deliberately requires the identifier on the SAME line. A document is allowed
    its own version number ("Version: 1.0 (this document)") -- that has no code
    source and is not a claim about code. Attribution is what makes it checkable,
    and demanding attribution is what keeps this from firing on every date-like
    number in the corpus.
    """
    if not constants:
        return [], []
    out: list[Violation] = []
    notes: list[str] = []
    seen: set[tuple[str, str]] = set()
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Every identifier occurrence on the line, with its position.
        anchors: list[tuple[int, str]] = []
        for identifier in constants:
            for hit in re.finditer(rf"\b{re.escape(identifier)}\b", line, re.I):
                anchors.append(((hit.start() + hit.end()) // 2, identifier))
        if not anchors:
            continue

        # More than one identifier on a line means the binding between name and
        # number is a matter of English, not syntax. "API_VERSION and
        # METHODOLOGY_VERSION are 2.0 and 1.1" pairs them in order; nearest-wins
        # pairs them backwards and reports two mismatches where there are none.
        # A fabricated finding is the worst outcome this check can produce, so
        # the line is reported as undecidable and not checked at all.
        distinct = {name for _, name in anchors}
        if len(distinct) > 1:
            notes.append(
                f"unknowable: {doc}:{lineno} names {len(distinct)} version "
                f"identifiers on one line ({sorted(distinct)}), so which number "
                f"belongs to which cannot be decided syntactically -- NOT checked"
            )
            continue

        for match in _DOC_VERSION_RE.finditer(line):
            at = match.start()
            distance, identifier = min(
                ((abs(pos - at), name) for pos, name in anchors), key=lambda p: p[0]
            )
            # Proximity window, because a QA report stores a whole paragraph as
            # ONE JSON string; without it an unrelated correlation threshold
            # (0.7) was read as a version claim.
            if distance > _VERSION_WINDOW:
                continue
            literal = match.group(1)
            known = constants[identifier]
            if literal in known or (identifier, literal) in seen:
                continue
            seen.add((identifier, literal))
            out.append(
                Violation(
                    "version",
                    doc,
                    lineno,
                    f"{identifier} = {literal}",
                    f"no code assignment holds {literal}; the values "
                    f"actually in code are {sorted(known)}",
                )
            )
    return out, notes


# --- check C: dependencies --------------------------------------------------


def _requirements_files(tracked: set[str]) -> list[str]:
    return sorted(
        rel
        for rel in tracked
        if rel.rsplit("/", 1)[-1].startswith("requirements") and rel.endswith(".txt")
    )


def _join_continuations(body: str) -> list[str]:
    """One logical command per entry, joining shell/Dockerfile backslashes.

    Requiring `pip install` on the same PHYSICAL line as its `-r` argument was
    wrong for the most common real form. Dockerfile.maintenance writes
    `RUN pip install --no-cache-dir \\` and then two `-r` lines, which made two
    genuinely installed requirements files read as orphans nothing installs --
    a false positive introduced by the fix for a false negative.
    """
    out: list[str] = []
    pending = ""
    for line in body.splitlines():
        stripped = line.rstrip()
        if stripped.endswith("\\"):
            pending += stripped[:-1] + " "
            continue
        out.append(pending + line)
        pending = ""
    if pending:
        out.append(pending)
    return out


def _is_executable_installer(rel: str) -> bool:
    """Only things a machine RUNS count as evidence that a file is installed.

    Markdown was counted here in the first version, which meant a README saying
    `pip install -r requirements.txt` was accepted as proof that something
    installs it. That is the precise error this whole module exists to catch --
    believing a document about what the code does -- and it was suppressing
    orphan findings. Docs are claims; workflows, Dockerfiles and shell scripts
    are execution.
    """
    base = rel.rsplit("/", 1)[-1]
    return (
        (rel.startswith(".github/") and rel.endswith((".yml", ".yaml")))
        or base.startswith("Dockerfile")
        or rel.endswith(".sh")
    )


def _installers(
    project_dir: Path, tracked: set[str]
) -> tuple[dict[str, list[str]], list[str]]:
    """key -> the tracked files that pip-install it, plus ambiguity notes.

    The key is the resolved repo-relative path when the `-r` argument names a
    tracked requirements file exactly, and the bare basename otherwise. The
    fallback exists because Dockerfile.python does `COPY services/requirements.txt
    ./requirements.txt` and then installs `requirements.txt`, so the name in the
    install line is not a repo path at all. Every fallback is reported, because
    a basename key cannot tell three different requirements.txt files apart.
    """
    out: dict[str, list[str]] = {}
    ambiguous: set[str] = set()
    for rel in sorted(tracked):
        if not _is_executable_installer(rel):
            continue
        body = _read(project_dir / rel)
        if body is None:
            continue
        for line in _join_continuations(body):
            # A commented-out install line is not an install. "# previously:
            # pip install -r requirements-special.txt" was being counted.
            code = line.partition("#")[0]
            install = _PIP_INSTALL_RE.search(code)
            if not install:
                continue
            for match in _PIP_INSTALL_R_RE.finditer(code[install.end() :]):
                named = match.group(1).lstrip("./")
                if named in tracked:
                    out.setdefault(named, []).append(rel)
                    continue
                base = named.rsplit("/", 1)[-1]
                same_name = [t for t in tracked if t.rsplit("/", 1)[-1] == base]
                if len(same_name) > 1:
                    ambiguous.add(f"{rel} installs '{named}' ({len(same_name)} candidates)")
                out.setdefault(base, []).append(rel)
    notes = (
        [
            "unknowable: "
            + str(len(ambiguous))
            + " install line(s) name a requirements file that is not a repo path "
            "(usually a Dockerfile COPY rename), so they were matched by basename "
            "and cannot distinguish same-named files: " + str(sorted(ambiguous)[:5])
        ]
        if ambiguous
        else []
    )
    return out, notes


def _installer_keys(rel: str) -> tuple[str, str]:
    """The two keys an installer map may hold for a requirements file."""
    return rel, rel.rsplit("/", 1)[-1]


_REQ_INCLUDE_RE = re.compile(r"^\s*(?:-r|--requirement)[=\s]+(\S+)")


def _declared_packages(
    project_dir: Path, rel: str, _seen: frozenset[str] = frozenset()
) -> set[str]:
    """Packages a file declares, following `-r` includes.

    pip resolves `-r other.txt` relative to the INCLUDING file, and a file
    reached only through an include is still installed. Without this, a
    requirements file pulled in by an include would be reported as an orphan
    nothing installs -- a false positive, and worse, its packages would be
    reported as unavailable to CI when pip installs them. No file in this repo
    uses an include today; the check would have been wrong the day one did.
    """
    if rel in _seen:  # cycle guard: a.txt -> b.txt -> a.txt
        return set()
    body = _read(project_dir / rel)
    if body is None:
        return set()
    names: set[str] = set()
    here = Path(rel).parent
    for line in body.splitlines():
        line = line.partition("#")[0].strip()
        if not line:
            continue
        include = _REQ_INCLUDE_RE.match(line)
        if include:
            target = (here / include.group(1)).as_posix().replace("./", "")
            names |= _declared_packages(project_dir, target, _seen | {rel})
            continue
        if line.startswith("-"):
            continue
        match = _REQ_NAME_RE.match(line)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def _included_files(project_dir: Path, rel: str, _seen: frozenset[str] = frozenset()) -> set[str]:
    """Every requirements file reachable from `rel` through `-r` includes."""
    if rel in _seen:
        return set()
    body = _read(project_dir / rel)
    if body is None:
        return set()
    here = Path(rel).parent
    out: set[str] = set()
    for line in body.splitlines():
        include = _REQ_INCLUDE_RE.match(line.partition("#")[0])
        if not include:
            continue
        target = (here / include.group(1)).as_posix().replace("./", "")
        out.add(target)
        out |= _included_files(project_dir, target, _seen | {rel})
    return out


def _test_imports(project_dir: Path, tracked: set[str]) -> dict[str, str]:
    """top-level import name -> the first test file that imports it.

    Parsed with ast, not line-matched. A line regex saw only the first name in
    `import a, b`, missed indented imports inside a try block, and -- the one
    that matters here -- missed `pytest.importorskip("shapely")` entirely.
    That is the exact form this repo's 18 dependency skips use, so the check
    would have been blind to the dependencies most likely to be missing.
    """
    out: dict[str, str] = {}
    for rel in sorted(tracked):
        if not (rel.startswith("tests/") and rel.endswith(".py")):
            continue
        body = _read(project_dir / rel)
        if body is None:
            continue
        try:
            tree = ast.parse(body)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    out.setdefault(alias.name.partition(".")[0], rel)
            elif isinstance(node, ast.ImportFrom):
                if node.module and not node.level:  # skip relative imports
                    out.setdefault(node.module.partition(".")[0], rel)
            elif isinstance(node, ast.Call):
                name = getattr(node.func, "attr", None) or getattr(
                    node.func, "id", None
                )
                if name in ("importorskip", "import_module") and node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        out.setdefault(first.value.partition(".")[0], rel)
    return out


def check_dependencies(
    project_dir: Path, tracked: set[str]
) -> tuple[list[Violation], list[str]]:
    out: list[Violation] = []

    req_files = _requirements_files(tracked)
    installers, notes = _installers(project_dir, tracked)
    declared: dict[str, set[str]] = {
        rel: _declared_packages(project_dir, rel) for rel in req_files
    }

    # Three tracked files are named requirements.txt. Dockerfile.python COPYs
    # services/requirements.txt to ./requirements.txt and installs that, so a
    # strict path match would call services/requirements.txt an orphan when it
    # is the one actually installed. The basename fallback is therefore kept --
    # but a file that ONLY matches by basename, while another tracked file
    # shares that basename, is a case the check cannot resolve, and it says so
    # instead of quietly picking one.
    shared_basename = {
        rel
        for rel in req_files
        if sum(1 for o in req_files if o.rsplit("/", 1)[-1] == rel.rsplit("/", 1)[-1])
        > 1
    }
    conflated: set[str] = set()

    def installed_by(rel: str) -> list[str]:
        exact = list(installers.get(rel, []))
        if exact:
            return exact
        basename_only = list(installers.get(rel.rsplit("/", 1)[-1], []))
        if basename_only and rel in shared_basename:
            conflated.add(rel)
        return basename_only

    ci_packages: set[str] = set()
    for rel, pkgs in declared.items():
        if any(u.startswith(".github/") for u in installed_by(rel)):
            ci_packages |= pkgs  # _declared_packages already followed includes

    # A file reached only through another file's `-r` include IS installed.
    reachable: set[str] = set()
    for rel in req_files:
        if installed_by(rel):
            reachable |= _included_files(project_dir, rel)

    # C1 -- a requirements file nothing installs. Every package it uniquely
    # declares is a package that never reaches any runtime.
    for rel in req_files:
        base = rel.rsplit("/", 1)[-1]
        if installed_by(rel) or rel in reachable:
            continue
        others = [p for r, p in declared.items() if r != rel]
        elsewhere: set[str] = set().union(*others) if others else set()
        orphaned = sorted(declared[rel] - elsewhere)
        out.append(
            Violation(
                "dependency",
                rel,
                0,
                base,
                "no pip install -r names this file, so nothing it declares is "
                "ever installed"
                + (
                    f"; {len(orphaned)} declared here only: {orphaned[:6]}"
                    if orphaned
                    else ""
                ),
            )
        )

    if conflated:
        notes.append(
            f"unknowable: {len(conflated)} requirements file(s) were matched to "
            f"an installer by BASENAME only, because another tracked file shares "
            f"that name -- whether the installer means this one cannot be decided "
            f"from the install line: {sorted(conflated)}"
        )

    # C2 -- a package tests import that CI never installs. The test does not
    # fail; it SKIPS, and a skip renders green (#879, #880).
    test_imports = _test_imports(project_dir, tracked)
    if not ci_packages:
        notes.append(
            "unknowable: no CI workflow was found running `pip install -r`, so "
            "the set of packages available to tests could not be determined and "
            "no test-import check ran"
        )
        return out, notes

    all_declared: set[str] = set().union(*declared.values()) if declared else set()
    for name, test_file in sorted(test_imports.items()):
        dist = _IMPORT_ALIASES.get(name, name.lower().replace("_", "-"))
        if dist not in all_declared:
            continue  # stdlib, first-party, or unmappable -- see the note below
        if dist not in ci_packages:
            holders = sorted(r for r, p in declared.items() if dist in p)
            out.append(
                Violation(
                    "dependency",
                    test_file,
                    0,
                    dist,
                    f"imported by tests but declared only in {holders}, none of "
                    f"which CI installs -- the test skips, and a skip is green",
                )
            )

    unmapped = [
        name
        for name in test_imports
        if name not in _IMPORT_ALIASES
        and name.lower().replace("_", "-") not in all_declared
        and name not in sys.stdlib_module_names
        and not (project_dir / name).is_dir()
        and not (project_dir / f"{name}.py").is_file()
    ]
    if unmapped:
        notes.append(
            f"unknowable: {len(unmapped)} test import(s) could not be mapped to "
            f"a declared distribution and were NOT checked: {sorted(unmapped)[:10]}"
        )
    return out, notes


# --- orchestration ----------------------------------------------------------


def _json_strings(node, path: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from _json_strings(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _json_strings(value, f"{path}[{i}]")


def default_docs(project_dir: Path, tracked: set[str]) -> list[str]:
    out: set[str] = set()
    for pattern in DEFAULT_DOC_GLOBS:
        for path in project_dir.glob(pattern):
            rel = path.relative_to(project_dir).as_posix()
            if rel in tracked and not rel.startswith(EXCLUDED_DOC_PREFIXES):
                out.add(rel)
    return sorted(out)


def scan(
    project_dir: str | Path,
    docs: Sequence[str] | None = None,
    reports: Sequence[str] | None = None,
) -> ScanResult:
    project_dir = Path(project_dir).resolve()
    result = ScanResult()

    tracked = tracked_files(project_dir)
    if tracked is None:
        result.notes.append(
            "unknowable: `git ls-files` did not answer, so no path could be "
            "resolved and NO check ran. This is not a pass."
        )
        return result

    basenames: dict[str, list[str]] = {}
    for rel in tracked:
        basenames.setdefault(rel.rsplit("/", 1)[-1], []).append(rel)

    doc_list = list(docs) if docs is not None else default_docs(project_dir, tracked)
    report_list = (
        list(reports)
        if reports is not None
        else [r for r in DEFAULT_REPORTS if (project_dir / r).is_file()]
    )

    constants = code_version_constants(project_dir, tracked)
    if not constants:
        result.notes.append(
            "unknowable: no version constants were found in code, so NO version "
            "claim could be checked"
        )
    ambiguous = ambiguous_identifiers(constants)
    if ambiguous:
        result.notes.append(
            f"unknowable: {len(ambiguous)} version identifier(s) hold different "
            f"values in different modules, so a doc naming one of the OTHER "
            f"module's values is accepted without being verified: "
            f"{[f'{n}={sorted(constants[n])}' for n in ambiguous[:5]]}"
        )

    for rel in doc_list:
        if rel.startswith(EXCLUDED_DOC_PREFIXES):
            continue
        text = _read(project_dir / rel)
        if text is None:
            result.notes.append(f"unknowable: {rel} could not be read")
            continue
        result.docs_scanned += 1
        result.violations.extend(
            check_paths(rel, text, project_dir, tracked, basenames)
        )
        version_hits, version_notes = check_versions(rel, text, constants)
        result.violations.extend(version_hits)
        result.notes.extend(version_notes)

    for rel in report_list:
        raw = _read(project_dir / rel)
        if raw is None:
            result.notes.append(f"unknowable: {rel} could not be read")
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            result.notes.append(f"unknowable: {rel} is not valid JSON ({exc})")
            continue
        result.docs_scanned += 1
        # Each string value is checked as a one-line document. A line number is
        # meaningless inside JSON, so the JSON path carries the location.
        for jpath, value in _json_strings(payload):
            where = f"{rel}#{jpath}"
            for v in check_paths(where, value, project_dir, tracked, basenames):
                result.violations.append(Violation(v.kind, where, 0, v.claim, v.detail))
            version_hits, version_notes = check_versions(where, value, constants)
            for v in version_hits:
                result.violations.append(Violation(v.kind, where, 0, v.claim, v.detail))
            result.notes.extend(version_notes)

    dep_violations, dep_notes = check_dependencies(project_dir, tracked)
    result.violations.extend(dep_violations)
    result.notes.extend(dep_notes)
    return result


def load_baseline(project_dir: Path) -> dict | None:
    path = project_dir / BASELINE_PATH
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Doc-claim check (observation mode) -- paths, versions, deps."
    )
    parser.add_argument("--project-dir", default=".")
    parser.add_argument("--docs", nargs="*", default=None)
    parser.add_argument("--reports", nargs="*", default=None)
    parser.add_argument("--init", action="store_true", help="write the baseline file")
    parser.add_argument("--compare", action="store_true", help="show only NEW findings")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 on findings. Wired into NO hook and NO gate -- observation "
        "mode is the default until a false-positive rate has been observed.",
    )
    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    result = scan(project_dir, args.docs, args.reports)

    baseline = load_baseline(project_dir)
    # `or []`, not a get() default: a hand-edited baseline with an explicit
    # null would otherwise raise, and a baseline is exactly the kind of file
    # people hand-edit.
    known = set(baseline.get("fingerprints") or []) if baseline else set()
    new = [v for v in result.violations if v.fingerprint() not in known]

    shown = new if args.compare else result.violations

    print(
        f"DOC-CLAIM CHECK (observation mode): {result.docs_scanned} docs, "
        f"{len(result.violations)} finding(s) {result.by_kind()}"
    )
    if args.compare:
        if baseline:
            print(
                f"  baseline {baseline.get('generated_against', '?')}: "
                f"{len(known)} known, {len(new)} new"
            )
        else:
            print("  ? unknowable: no baseline file -- every finding shows as new")
    for v in shown:
        print(f"  - {v.render()}")
    for note in result.notes:
        print(f"  ? {note}")
    if not shown:
        print("  no findings.")

    if args.init:
        # The QA report is rewritten every PR, so its findings are not corpus
        # state and must never enter the baseline: a stale fingerprint from a
        # previous report would suppress the SAME false claim when a future
        # report makes it for real. Docs and requirements files are baselined;
        # the per-change report always reports fresh.
        baselineable = [
            v for v in result.violations if not v.doc.startswith(tuple(DEFAULT_REPORTS))
        ]
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=10,
            env=git_env(),
        ).stdout.strip()
        payload = {
            "generated_against": head,
            "mode": "observation",
            "excluded_from_baseline": list(DEFAULT_REPORTS),
            # Counted from what was actually WRITTEN. Counting all violations
            # here while writing only the baselineable ones gave a header that
            # disagreed with its own findings list.
            "counts": _count_kinds(baselineable),
            "excluded_report_findings": len(result.violations) - len(baselineable),
            "docs_scanned": result.docs_scanned,
            "notes": result.notes,
            "fingerprints": sorted(v.fingerprint() for v in baselineable),
            "findings": [
                {
                    "kind": v.kind,
                    "doc": v.doc,
                    "line": v.line,
                    "claim": v.claim,
                    "detail": v.detail,
                }
                for v in sorted(baselineable, key=lambda x: (x.kind, x.doc, x.claim))
            ],
        }
        out_path = project_dir / BASELINE_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(
            f"  baseline written: {BASELINE_PATH} ({len(baselineable)} findings; "
            f"{len(result.violations) - len(baselineable)} report finding(s) "
            f"deliberately excluded)"
        )

    if not args.strict:
        return 0
    if shown:
        return 1
    # A scan that could not run is not a clean scan. Without this, --strict in
    # an exported tree with no .git exits 0 having checked nothing -- the exact
    # fail-open this whole change exists to remove.
    return 2 if result.notes else 0


if __name__ == "__main__":
    sys.exit(main())
