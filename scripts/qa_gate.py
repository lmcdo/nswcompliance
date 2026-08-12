#!/usr/bin/env python3
"""QA Railguards — executable gate.

Validates a structured QA report JSON file against tier requirements.
Three layers of verification:
  1. Structure — required fields present, non-empty
  2. Grounding — file:line references verified against real code via AST
  3. Depth — minimum word counts, break-it uniqueness, cross-references

The report is per-branch and committed at .qa/reports/<branch-slug>.json. Omit
the path and it is resolved for the current branch by qa_report_path — the one
definition every consumer shares, so the hook, the workflow and this gate cannot
end up checking different files.

Usage:
    python scripts/qa_gate.py
    python scripts/qa_gate.py --diff-files file1.py file2.py
    python scripts/qa_gate.py .qa/reports/fix__thing.json --project-dir /path/to/repo

Exit codes:
    0 = PASSED
    1 = FAILED
"""

import ast
import json
import subprocess
import sys
import os
import re
from pathlib import Path
from typing import Optional

# Same directory, but this file is run as a script from the repo root and is
# also loaded by tests via importlib, so neither cwd nor a package context can
# be relied on to find it.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_report_path  # noqa: E402  (path must be set first)

TIER_REQUIREMENTS = {
    "critical": {
        "pre_impl_fields": ["existing_data", "assumption_mismatch", "new_vs_existing",
                            "external_source_error", "frontend_type", "user_failure_mode"],
        "min_functions": 1,
        "min_break_it": 5,
        "min_words_per_field": 8,
        "sections_required": [1, 2, 3, 4, 5, 6, 7],
        "require_falsifiable_check": True,
    },
    "standard": {
        "pre_impl_fields": ["existing_data", "assumption_mismatch", "new_vs_existing"],
        "min_functions": 1,
        "min_break_it": 3,
        "min_words_per_field": 5,
        "sections_required": [1, 2, 3, 4, 5, 6, 7],
        "require_falsifiable_check": True,
    },
    "minor": {
        "pre_impl_fields": [],
        "min_functions": 0,
        "min_break_it": 1,
        "min_words_per_field": 3,
        "sections_required": [1, 6, 7],
        # Deliberately NOT required at minor tier: a copy tweak has no meaningful
        # falsifiable check, and a gate that fires on every trivial change gets
        # dismissed by muscle memory within a week (DQ-34's alarm-fatigue lesson).
        # Rare and meaningful, or it protects nothing.
        "require_falsifiable_check": False,
    },
}

# ─── Falsifiability gate ─────────────────────────────────────────────────────
# ORIGIN: 2026-08-01. DQ-30 was marked "Fixed" on a "0% drift" check, which
# re-ran the tagger and compared its output to the stored value. That is a
# SELF-COMPARISON: when the code itself is wrong, drift is 0% and the data is
# still broken. It could not fail. 241 rows — 112 live and served — survived it.
# The project already had the rule in writing ("a completion check must be able
# to fail"); it did not prevent this, because a rule in a document is not
# enforcement. This is the enforcement.
#
# It asks the one question a tautological check cannot answer:
#   WHAT COMMAND, AND WHAT MAKES IT GO RED?

_SELF_COMPARISON_RE = re.compile(
    # 1. The word itself.
    r"\bdrift\b"
    # 2. Comparing output explicitly to itself.
    r"|compare[sd]?\s+(?:the\s+)?(?:code|output|result)s?\s+(?:to|against|with)\s+"
    r"(?:it|its|itself|the\s+same)"
    r"|matches?\s+(?:the\s+)?(?:current|existing)\s+(?:code|output)"
    # 3. The DESCRIBED form, which the first version missed and a test caught:
    #    re-run / recompute, then compare the result to what is already stored.
    #    Note this deliberately requires a re-derivation verb — comparing STORED
    #    data against an external AUTHORITY ("stored zone codes absent from
    #    lep_zone_coverage") is the correct pattern and must not be flagged.
    r"|(?:re-?run|re-?comput\w*|re-?generat\w*|re-?derive\w*)"
    r".{0,60}?(?:compare\w*|differs?|diff\b|match\w*|same)"
    r".{0,40}?(?:stored|existing|previous|current|already)",
    re.I | re.S,
)

# `node` and `.js` added 2026-08-12: the CI workflows are now checked by a plain
# node harness (scripts/main_red_alarm_logic_check.js), and the gate rejected a
# genuinely runnable command purely because JS was missing from this list. This
# widens what is RECOGNISED as a command; it does not weaken the check, which is
# still that a description of a check is not a check.
#
# `node` is anchored with \b at BOTH ends and the others are not, which looks
# inconsistent and is deliberate: unanchored, it matches the "nodes" in "inspect
# the graph nodes and confirm the counts look right", so plain prose would have
# been accepted as a runnable command. The test that now guards this line caught
# exactly that on the first run. "nodes" is ordinary vocabulary in this codebase;
# "pythonic" and "npmish" are not, which is why the older entries survive
# unanchored.
_LOOKS_RUNNABLE_RE = re.compile(
    r"(python|pytest|npx|npm|\bnode\b|psql|bash|\./|SELECT\b|\.py\b|\.sh\b|\.ts\b|\.js\b)",
    re.I,
)


def check_falsifiable(report: dict, reqs: dict) -> list[str]:
    """Require a named check plus the condition under which it FAILS.

    This is NOT a tautology detector — that is undecidable in general. It
    enforces the two things whose absence let the original defect through: a
    runnable command, and an explicit red condition stated separately from the
    command itself.
    """
    errors: list[str] = []
    if not reqs.get("require_falsifiable_check"):
        return errors

    fc = report.get("falsifiable_check")
    if not isinstance(fc, dict) or not fc:
        return [
            "Section 1 falsifiable_check: MISSING. Add "
            '"falsifiable_check": {"command": "<what you ran>", '
            '"fails_when": "<what makes it go red>"}. '
            "Ask: if the bug were still present, would this go red? If not, it is "
            "not a verification. (Origin: DQ-30 was marked Fixed on a check that "
            "could not fail.)"
        ]

    command = str(fc.get("command", "")).strip()
    fails_when = str(fc.get("fails_when", "")).strip()

    errors.extend(validate_non_empty(command, "Section 1 falsifiable_check.command"))
    errors.extend(validate_non_empty(fails_when, "Section 1 falsifiable_check.fails_when"))
    if not command or not fails_when:
        return errors

    if not _LOOKS_RUNNABLE_RE.search(command):
        errors.append(
            f"Section 1 falsifiable_check.command ('{command[:60]}') does not look "
            "runnable. Name the actual command or query, not a description of one — "
            "a check nobody can execute is not a check."
        )

    errors.extend(validate_min_words(
        fails_when, "Section 1 falsifiable_check.fails_when", reqs["min_words_per_field"]
    ))

    if _SELF_COMPARISON_RE.search(command) or _SELF_COMPARISON_RE.search(fails_when):
        errors.append(
            "Section 1 falsifiable_check: reads as a SELF-COMPARISON (re-running the "
            "code and checking it agrees with itself). That cannot fail when the code "
            "is wrong — exactly how DQ-30 was marked Fixed while 112 live rows stayed "
            "broken. Compare against an external authority instead (e.g. "
            "lep_zone_coverage for zone codes), or state why this is not self-referential."
        )

    if fails_when.strip().lower() == command.strip().lower():
        errors.append(
            "Section 1 falsifiable_check: fails_when merely repeats command. State the "
            "CONDITION that turns it red, not the command again."
        )

    return errors

FILE_LINE_PATTERN = re.compile(r'([\w/\\._-]+):(\d+)')

# ─── Layer 1: Structure validation ────────────────────────────────────────────


def validate_non_empty(value: str, field_name: str) -> list[str]:
    """Check a field is not empty or placeholder."""
    placeholders = {"", "tbd", "todo", "n/a - skip", "looks fine", "checked",
                    "ok", "fine", "done", "yes", "no issues", "none found"}
    if not value or value.strip().lower() in placeholders:
        return [f"{field_name}: empty or placeholder answer"]
    return []


def validate_min_words(value: str, field_name: str, min_words: int) -> list[str]:
    """Check a field has minimum word count (depth check)."""
    if not value:
        return []  # Caught by non-empty check
    word_count = len(value.strip().split())
    if word_count < min_words:
        return [f"{field_name}: too shallow ({word_count} words, need >= {min_words})"]
    return []


# ─── Layer 2: AST grounding ──────────────────────────────────────────────────


def find_file(filename: str, project_dir: str) -> Optional[str]:
    """Find a file in the project directory, handling partial paths."""
    # Try exact path first
    exact = os.path.join(project_dir, filename)
    if os.path.exists(exact):
        return exact

    # Try searching
    for root, _dirs, files in os.walk(project_dir):
        # Skip venv, node_modules, .git
        if any(skip in root for skip in ("venv", "node_modules", ".git", "__pycache__")):
            continue
        for f in files:
            full = os.path.join(root, f)
            if full.endswith(filename) or f == os.path.basename(filename):
                return full
    return None


def verify_python_function(filepath: str, line_num: int, func_name: str) -> tuple[bool, str]:
    """Verify a Python function exists at the claimed location via AST."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=filepath)
    except (SyntaxError, FileNotFoundError, UnicodeDecodeError) as e:
        return False, f"Cannot parse {filepath}: {e}"

    # Find all function/method definitions
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                # Allow +/- 5 lines tolerance (edits shift lines)
                if abs(node.lineno - line_num) <= 5:
                    return True, f"Found {func_name} at line {node.lineno}"
                else:
                    return False, (
                        f"Function '{func_name}' exists but at line {node.lineno}, "
                        f"not {line_num} (off by {abs(node.lineno - line_num)})"
                    )

    return False, f"Function '{func_name}' not found in {filepath}"


def ast_ground_functions(functions: list[dict], project_dir: str) -> list[str]:
    """Verify all claimed function references against actual code."""
    errors = []
    for i, fn in enumerate(functions):
        name = fn.get("name", "")
        file_line = fn.get("file_line", "")
        if not file_line or not name:
            continue

        match = FILE_LINE_PATTERN.search(file_line)
        if not match:
            continue

        filename, line_str = match.group(1), int(match.group(2))
        filepath = find_file(filename, project_dir)

        if not filepath:
            errors.append(f"Section 3 functions[{i}]: file '{filename}' not found in project")
            continue

        # Only AST-verify Python files
        if filepath.endswith(".py"):
            ok, msg = verify_python_function(filepath, line_str, name)
            if not ok:
                errors.append(f"Section 3 functions[{i}]: AST verification failed — {msg}")

    return errors


# ─── Layer 3: Depth enforcement ───────────────────────────────────────────────


def check_diff_coverage(report_files: list[str], diff_files: list[str]) -> list[str]:
    """Check that changed files appear in the report."""
    errors = []
    if not diff_files:
        return errors

    # Filter to substantive files (not config, not gitignore)
    substantive_diff = [
        f for f in diff_files
        if not f.startswith(".") and not f.endswith((".json", ".md", ".txt", ".yml", ".yaml"))
        and "config" not in f.lower()
    ]

    if not substantive_diff:
        return errors

    report_basenames = {os.path.basename(f) for f in report_files}
    report_files_set = set(report_files)

    uncovered = []
    for df in substantive_diff:
        basename = os.path.basename(df)
        if basename not in report_basenames and df not in report_files_set:
            # Check partial match
            if not any(df.endswith(rf) or rf.endswith(df) for rf in report_files):
                uncovered.append(df)

    if uncovered and len(uncovered) > len(substantive_diff) * 0.5:
        errors.append(
            f"Diff coverage: {len(uncovered)}/{len(substantive_diff)} changed files "
            f"not referenced in report: {', '.join(uncovered[:5])}"
        )

    return errors


def check_break_it_uniqueness(scenarios: list[dict]) -> list[str]:
    """Check that break-it scenarios are genuinely different."""
    errors = []
    if len(scenarios) < 2:
        return errors

    # Extract scenario text and check for structural duplication
    texts = [s.get("scenario", "").lower().strip() for s in scenarios]

    # Check for near-duplicates (same words, different order doesn't count)
    word_sets = [frozenset(t.split()) for t in texts]
    for i in range(len(word_sets)):
        for j in range(i + 1, len(word_sets)):
            if not word_sets[i] or not word_sets[j]:
                continue
            overlap = len(word_sets[i] & word_sets[j])
            union = len(word_sets[i] | word_sets[j])
            if union > 0 and overlap / union > 0.7:
                errors.append(
                    f"Section 6: break-it scenarios [{i}] and [{j}] are too similar "
                    f"({overlap}/{union} word overlap)"
                )

    # Check for generic filler
    generic_patterns = [
        r"\bserver crash",
        r"\bnetwork (timeout|error|fail)",
        r"\bdisk (full|space)",
        r"\bmemory (leak|full|overflow)",
        r"\bpython crash",
        r"\bprocess (die|kill|crash)",
    ]
    for i, text in enumerate(texts):
        for pattern in generic_patterns:
            if re.search(pattern, text):
                errors.append(
                    f"Section 6 break_it[{i}]: scenario looks generic ('{pattern.strip(chr(92)+'b')}'). "
                    f"Use domain-specific failure modes, not infrastructure failures."
                )

    return errors


def check_cross_references(report: dict) -> list[str]:
    """Check internal consistency: queries should have break-it coverage."""
    errors = []
    queries = report.get("queries", [])
    break_it = report.get("break_it", [])

    if isinstance(queries, str) or not queries:
        return errors

    # Each query should have at least one break-it that references its failure
    break_texts = " ".join(
        f"{s.get('scenario', '')} {s.get('what_happens', '')}"
        for s in break_it
    ).lower()

    for i, q in enumerate(queries):
        purpose = q.get("purpose", "").lower()
        # Extract key terms from the query purpose
        key_terms = [w for w in purpose.split() if len(w) > 3 and w not in ("this", "that", "from", "with")]
        if key_terms and not any(term in break_texts for term in key_terms[:3]):
            errors.append(
                f"Section 6 cross-ref: query [{i}] ('{purpose[:50]}') has no corresponding "
                f"break-it scenario addressing its failure mode"
            )

    return errors


# ─── Layer 4: DB query guard column scanner ─────────────────────────────────

# Tables that MUST have specific WHERE guards in any SELECT
# {table_name: [required_guard_columns]}
GUARDED_TABLES = {
    "regulatory_provisions": ["is_current", "v2_is_actionable"],
    "dcp_setback_controls": ["is_current"],
    "lga_registry": ["is_active"],
}


def changed_line_numbers(diff_files: list[str], project_dir: str) -> dict[str, set[int]]:
    """Map each changed file -> the set of line numbers the change actually touched.

    Used to diff-scope the scanners below: a finding on a line the change did not
    touch is dropped, so brushing a pre-existing file (e.g. removing a hardcoded
    secret from one line of an old script) no longer forces fixing every unrelated
    issue elsewhere in that file. Computed from `git diff --unified=0 <base>..HEAD`.

    Returns {} when git cannot determine a base — callers then keep ALL findings
    (safe full-scan fallback). The gate only ever RELAXES when it is confident a
    flagged line is pre-existing, never when uncertain.
    """
    def _git(args: list[str]) -> Optional[str]:
        try:
            # cwd decides the repo, per this function's contract. Git hooks
            # export GIT_DIR (absolute when pushing from a worktree), which
            # would silently redirect these queries to the hook's repo even
            # when cwd is not a repository at all — scrub it.
            env = os.environ.copy()
            for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
                env.pop(var, None)
            r = subprocess.run(
                ["git", *args], capture_output=True, text=True,
                timeout=10, cwd=project_dir, env=env,
            )
            return r.stdout if r.returncode == 0 else None
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None

    base = None
    for ref in ("origin/main", "origin/master", "main"):
        mb = _git(["merge-base", "HEAD", ref])
        if mb and mb.strip():
            base = mb.strip()
            break
    if not base:
        return {}

    result: dict[str, set[int]] = {}
    for f in diff_files:
        out = _git(["diff", "--unified=0", base, "HEAD", "--", f])
        if out is None:
            continue
        added: set[int] = set()
        for ln in out.splitlines():
            if ln.startswith("@@"):
                m = re.search(r"\+(\d+)(?:,(\d+))?", ln)
                if m:
                    start = int(m.group(1))
                    count = int(m.group(2)) if m.group(2) is not None else 1
                    added.update(range(start, start + count))
        result[f] = added
    return result


def filter_to_changed_lines(errors: list[str], changed: dict[str, set[int]]) -> list[str]:
    """Drop scanner findings whose file:line is NOT a line the change touched.

    Keeps any error with no parseable file:line, any error for a file not present in
    `changed`, and — when `changed` is empty — ALL errors. So the gate relaxes only
    when it is certain a flagged line was pre-existing, never when uncertain.
    """
    if not changed:
        return errors
    kept: list[str] = []
    for e in errors:
        m = re.search(r"([\w./\\-]+\.[A-Za-z0-9]+):(\d+)", e)
        if not m:
            kept.append(e)
            continue
        path, line = m.group(1), int(m.group(2))
        allowed = None
        for f, lines_set in changed.items():
            if f == path or f.endswith(path) or path.endswith(f):
                allowed = lines_set
                break
        if allowed is None or line in allowed:
            kept.append(e)
    return kept


def scan_diff_for_unguarded_queries(
    diff_files: list[str], project_dir: str
) -> list[str]:
    """Scan changed files for SELECT queries against guarded tables missing WHERE guards.

    Reads each changed file, finds references to guarded table names,
    then checks whether the required guard column appears within the same
    query block (within 10 lines).
    """
    errors = []
    if not project_dir:
        return errors

    for filepath in diff_files:
        full_path = os.path.join(project_dir, filepath)
        if not os.path.exists(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError):
            continue

        # Pre-compute docstring regions for Python files
        in_docstring = [False] * len(lines)
        if filepath.endswith(".py"):
            inside = False
            for idx, ln in enumerate(lines):
                s = ln.strip()
                if s.startswith('"""') or s.startswith("'''"):
                    # Toggle: opening or closing docstring
                    delim = s[:3]
                    count = s.count(delim)
                    if count == 1:
                        inside = not inside
                    # Single-line docstring ("""...""") stays outside
                in_docstring[idx] = inside or s.startswith('"""') or s.startswith("'''")

        for table_name, guard_cols in GUARDED_TABLES.items():
            for i, line in enumerate(lines):
                line_lower = line.lower()
                # Look for exact table references (not substrings like regulatory_provisions_canonical)
                if table_name not in line_lower:
                    continue
                # Ensure this is the exact table, not a derived/canonical variant
                if not re.search(rf'\b{re.escape(table_name)}\b', line_lower):
                    continue
                # Skip comments, imports, and non-query lines
                stripped = line.strip()
                if stripped.startswith(("#", "//", "*", "/*", "import ", "from ")):
                    continue
                # Skip lines inside docstrings or string literals
                if in_docstring[i]:
                    continue
                if stripped.startswith(('"""', "'''", '"', "'")):
                    continue
                # Skip test files — they mock DB calls
                if "/test" in filepath.lower() or "\\test" in filepath.lower():
                    continue

                # Check if this looks like a query context (SQL keywords nearby)
                query_window = "".join(lines[max(0, i - 3):min(len(lines), i + 10)]).lower()
                if not any(kw in query_window for kw in ("select", "from", "where", "join")):
                    continue

                # Now check if at least one required guard column appears in the query window
                if not any(guard_col in query_window for guard_col in guard_cols):
                    errors.append(
                        f"DB guard: {filepath}:{i + 1} references '{table_name}' "
                        f"but none of {guard_cols} found in query (within ±10 lines). "
                        f"Add a currency filter (e.g. WHERE {guard_cols[0]} = TRUE) to prevent stale data."
                    )

    return errors


# ─── Layer 5: Unguarded null access scanner ──────────────────────────────────

# Pattern: .rows[0]. without a preceding length/existence check
ROWS_ACCESS_PATTERN = re.compile(r'\.rows\[0\]')
# Patterns that indicate the access IS guarded
NULL_GUARD_PATTERNS = [
    re.compile(r'\.rows\.length'),
    re.compile(r'\.rows\?\['),
    re.compile(r'\.rowCount'),
    re.compile(r'COUNT\s*\(\s*\*\s*\)', re.IGNORECASE),
    re.compile(r'INSERT\s+INTO\b.*\bRETURNING\b', re.IGNORECASE | re.DOTALL),
    re.compile(r'if\s*\(\s*!?\s*\w+\.rows'),
    re.compile(r'rows\[0\]\?\.'),
]


def scan_diff_for_unguarded_nulls(
    diff_files: list[str], project_dir: str
) -> list[str]:
    """Scan changed TS/JS files for .rows[0]. access without null guards.

    Checks a ±10 line window around each .rows[0] access for evidence of
    a prior length check, COUNT(*) query, INSERT RETURNING, or optional chaining.
    """
    errors = []
    if not project_dir:
        return errors

    for filepath in diff_files:
        # Only scan TypeScript/JavaScript files (where .rows[0] is used)
        if not filepath.endswith(('.ts', '.tsx', '.js', '.jsx')):
            continue
        # Skip test files
        if '/test' in filepath.lower() or '\\test' in filepath.lower():
            continue

        full_path = os.path.join(project_dir, filepath)
        if not os.path.exists(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError):
            continue

        for i, line in enumerate(lines):
            if not ROWS_ACCESS_PATTERN.search(line):
                continue
            # Skip comments
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue

            # Guard window: scan BACK to the start of the enclosing function (capped
            # at 60 lines) so a COUNT(*) inside a Promise.all, or an
            # `if (rows.length === 0) return` guard higher up the handler, still
            # counts; plus a few lines FORWARD.
            window_start = max(0, i - 10)
            for b in range(i - 1, max(-1, i - 60), -1):
                window_start = b
                if re.search(r'\bfunction\b|=>\s*\{|\basync\s+\w', lines[b]):
                    break
            window_text = "".join(lines[window_start:min(len(lines), i + 6)])

            guarded = any(p.search(window_text) for p in NULL_GUARD_PATTERNS)

            # Also safe: `const X = <...>.rows[0]` where X is then read via X?.
            # (assign-then-optional-chain is a common, correct pattern).
            if not guarded:
                m = re.search(r'(\w+)\s*=\s*[\w.]+\.rows\[0\]', line)
                if m:
                    forward = "".join(lines[i:min(len(lines), i + 10)])
                    if re.search(rf'\b{re.escape(m.group(1))}\?\.', forward):
                        guarded = True

            if not guarded:
                errors.append(
                    f"Null guard: {filepath}:{i + 1} accesses .rows[0] without "
                    f"a prior length check, COUNT(*), INSERT RETURNING, or "
                    f"optional chaining (?.) in the surrounding code."
                )

    return errors


# ─── Layer 6: Type boundary heuristics ───────────────────────────────────────

# Heuristic A: {value && <JSX>} where value could be 0 or ""
# This silently renders nothing when value is falsy but non-null (0, "", NaN)
FALSY_JSX_PATTERN = re.compile(
    r'\{(\w+(?:\.\w+)*)\s*&&\s*[<(]'
)
# Known safe: boolean-only variables
BOOLEAN_HINTS = re.compile(
    r'\b(?:is[A-Z_]|has[A-Z_]|show[A-Z_]|can[A-Z_]|should[A-Z_]|loading|error|open|visible|active|disabled|checked|selected|expanded)',
)

# Heuristic B: === null without also checking undefined
STRICT_NULL_ONLY = re.compile(
    r'===\s*null(?!\s*\|\|\s*\w+\s*===\s*undefined)')
# Patterns that show undefined is also handled
UNDEFINED_ALSO_CHECKED = [
    re.compile(r'===?\s*null\s*\|\|\s*\w+\s*===?\s*undefined'),
    re.compile(r'===?\s*undefined\s*\|\|\s*\w+\s*===?\s*null'),
    re.compile(r'(?<!=)==\s*null\b'),   # == null (not ===) catches both null and undefined
    re.compile(r'(?<!!)!=\s*null\b'),  # != null (not !==) catches both
    re.compile(r'\?\?'),              # nullish coalescing handles both
    re.compile(r'\?\.\w'),            # optional chaining handles both
]


def scan_diff_for_type_boundaries(
    diff_files: list[str], project_dir: str
) -> list[str]:
    """Scan changed TS/TSX files for common type boundary issues.

    Heuristic A: {value && <JSX>} with potentially numeric/string values
                 that could be 0 or "" (falsy but valid).
    Heuristic B: === null without also checking undefined, in contexts
                 where the value could be undefined (API responses, optional props).
    """
    errors = []
    if not project_dir:
        return errors

    for filepath in diff_files:
        if not filepath.endswith(('.ts', '.tsx', '.js', '.jsx')):
            continue
        fp_lower = filepath.lower().replace('\\', '/')
        if '/test' in fp_lower or fp_lower.startswith('test'):
            continue
        if 'backup' in fp_lower or 'migrate' in fp_lower:
            continue
        full_path = os.path.join(project_dir, filepath)
        if not os.path.exists(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError):
            continue

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            # Allow suppression with // qa-ignore: type-boundary
            if "qa-ignore" in line and "type-boundary" in line:
                continue

            # --- Heuristic A: falsy JSX guard ---
            if filepath.endswith('.tsx') or filepath.endswith('.jsx'):
                match = FALSY_JSX_PATTERN.search(line)
                if match:
                    var_name = match.group(1)
                    # Skip if the variable name strongly implies boolean
                    if not BOOLEAN_HINTS.search(var_name):
                        # Check surrounding context for type hints that show it's numeric
                        window = "".join(lines[max(0, i - 5):min(len(lines), i + 3)])
                        # If the variable appears with numeric operations or min/max/count
                        if re.search(rf'{re.escape(var_name)}.*(?:number|count|min|max|total|value|amount|price|rate|size|width|height|length\b)', window, re.IGNORECASE):
                            errors.append(
                                f"Type boundary: {filepath}:{i + 1} uses "
                                f"'{{{var_name} && <...>}}' but {var_name} may be "
                                f"numeric (0 is falsy). Use '{{{var_name} != null && <...>}}' "
                                f"or '{{!!{var_name} && <...>}}' instead."
                            )

            # --- Heuristic B: strict null without undefined ---
            if '=== null' in line and '!== null' not in line:
                # Check window for undefined also being handled
                window = "".join(lines[max(0, i - 3):min(len(lines), i + 3)])
                handled = any(p.search(window) for p in UNDEFINED_ALSO_CHECKED)
                if not handled:
                    # Check if this is in a type guard context (function return, not conditional)
                    if re.search(r'if\s*\(|[?:]|\|\|', line):
                        errors.append(
                            f"Type boundary: {filepath}:{i + 1} uses '=== null' but "
                            f"API/DB values can also be undefined. Use '== null' "
                            f"(catches both) or add explicit undefined check."
                        )

    return errors


# ─── Layer 7: Silent failure mode heuristics ─────────────────────────────────

# Heuristic C: empty or swallowing catch blocks
CATCH_PATTERN = re.compile(r'\bcatch\s*\(\s*\w*\s*\)\s*\{')

# Heuristic D: catch blocks returning 200 with empty data
CATCH_SUCCESS_PATTERNS = [
    re.compile(r'NextResponse\.json\s*\(\s*\{'),
    re.compile(r'res\.(?:json|send|status\s*\(\s*200\s*\))'),
    re.compile(r'return\s+\{'),
    re.compile(r'return\s+\[\s*\]'),
    re.compile(r'return\s+null\b'),
]


def scan_diff_for_silent_failures(
    diff_files: list[str], project_dir: str
) -> list[str]:
    """Scan changed TS/JS files for silent failure patterns.

    Heuristic C: empty catch blocks or catch blocks that only log
                 without rethrowing or returning an error response.
    Heuristic D: catch blocks that return 200/success with empty data,
                 masking the error from the caller.
    """
    errors = []
    if not project_dir:
        return errors

    for filepath in diff_files:
        if not filepath.endswith(('.ts', '.tsx', '.js', '.jsx', '.py')):
            continue
        fp_lower = filepath.lower().replace('\\', '/')
        if '/test' in fp_lower or fp_lower.startswith('test'):
            continue
        if 'backup' in fp_lower or 'migrate' in fp_lower:
            continue

        full_path = os.path.join(project_dir, filepath)
        if not os.path.exists(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                lines = content.split('\n')
        except (FileNotFoundError, PermissionError):
            continue

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*", "#")):
                continue
            if "qa-ignore" in line and "silent-failure" in line:
                continue

            # --- Heuristic C: empty/swallowing catch blocks ---
            if CATCH_PATTERN.search(line):
                # Find the catch block's opening { and track from there.
                # The line may start with } from the try block (e.g. "} catch (e) {"),
                # so we locate the catch keyword's { specifically.
                match = CATCH_PATTERN.search(line)
                # Start brace depth at 1 (we found the opening {)
                # and scan from the next line forward.
                brace_depth = 1
                body_lines = []
                for j in range(i + 1, min(len(lines), i + 20)):
                    for ch in lines[j]:
                        if ch == '{':
                            brace_depth += 1
                        elif ch == '}':
                            brace_depth -= 1
                            if brace_depth == 0:
                                break
                    if brace_depth == 0:
                        break
                    body_lines.append(lines[j])

                body_text = "\n".join(body_lines)
                body_stripped = body_text.strip()

                # Empty catch block — only flag in API routes where silence = user impact
                if not body_stripped or body_stripped == '}':
                    if 'route' in fp_lower or 'api' in fp_lower:
                        errors.append(
                            f"Silent failure: {filepath}:{i + 1} has an empty catch block. "
                            f"Errors are swallowed silently. Add error logging, rethrow, "
                            f"or return an error response."
                        )
                    continue

                # Catch block that only logs (no throw, no error return)
                has_throw = bool(re.search(r'\bthrow\b', body_text))
                has_error_response = bool(re.search(
                    r'status\s*\(\s*[45]\d\d\s*\)|(?<!console)\.error\s*\(|NextResponse\.json\s*\([^)]*\{[^}]*error',
                    body_text
                ))
                has_rethrow = has_throw or has_error_response
                has_log_only = bool(re.search(
                    r'console\.\w+|logger\.\w+|logging\.\w+|print\s*\(', body_text
                ))
                # A catch that logs AND returns an explicit fallback value
                # is graceful degradation, not a silent failure — the caller
                # receives a defined value and is responsible for the response.
                has_explicit_return = bool(re.search(
                    r'\breturn\s+\[|return\s+\[\s*\]|return\s+null\b'
                    r'|return\s+\{|return\s+""|return\s+0\b'
                    r'|return\s+false\b|return\s+None\b'
                    # A catch that returns ANY value (e.g. return NextResponse.json(...),
                    # return res, return fallback) is handled, not silent. Returning a 200
                    # ack is the correct idiom in webhooks/best-effort handlers; Heuristic D
                    # separately flags exported handlers that return success instead of error.
                    r'|return\s+[A-Za-z_$]',
                    body_text
                ))

                if has_log_only and not has_rethrow and not has_explicit_return:
                    # Check if this is in an API route (where silent = user sees nothing).
                    # Webhook routes are exempt: returning 200 on a handler error is the
                    # REQUIRED idiom (Stripe/etc. retry the whole webhook on a non-2xx).
                    if ('route' in fp_lower or 'api' in fp_lower) and 'webhook' not in fp_lower:
                        errors.append(
                            f"Silent failure: {filepath}:{i + 1} catch block only logs "
                            f"but doesn't return an error response or rethrow. "
                            f"In API routes, this means the user gets no indication of failure."
                        )

            # --- Heuristic D: catch returning success with empty data ---
            # Only flag in route/API files where this pattern matters, and only in
            # exported handler functions (not helper functions where returning a
            # fallback value is graceful degradation). Webhook routes are exempt:
            # returning a 200 ack on a handler error is the required webhook idiom.
            if ('route' in fp_lower or 'api' in fp_lower) and 'webhook' not in fp_lower:
                if CATCH_PATTERN.search(line):
                    # Check if this catch is inside an exported function (the handler)
                    # by scanning backwards for the nearest function declaration.
                    in_exported_fn = False
                    for scan_back in range(i - 1, max(-1, i - 50), -1):
                        scan_line = lines[scan_back].strip()
                        if re.search(r'^export\s+(async\s+)?function\b', scan_line):
                            in_exported_fn = True
                            break
                        if re.search(r'^(async\s+)?function\b|^\w+\s*=\s*(async\s+)?\(', scan_line):
                            break  # non-exported function — stop
                    if not in_exported_fn:
                        continue  # helper function — fallback returns are valid
                    # Reuse body_text from Heuristic C if we already parsed it
                    catch_body_d = body_text if CATCH_PATTERN.search(line) and body_text else ""
                    if not catch_body_d:
                        catch_body_d = "\n".join(lines[i + 1:min(len(lines), i + 10)])
                    for sp in CATCH_SUCCESS_PATTERNS:
                        if sp.search(catch_body_d):
                            # Check it's not already returning an error status
                            if not re.search(r'status\s*\(\s*[45]\d\d\s*\)', catch_body_d):
                                if not re.search(r'\berror\b.*:', catch_body_d):
                                    errors.append(
                                        f"Silent failure: {filepath}:{i + 1} catch block "
                                        f"returns success/data instead of an error response. "
                                        f"Callers won't know the operation failed."
                                    )
                                    break

    return errors


# ─── Layer 8: Python adversarial scanner ─────────────────────────────────────

# 8a: .split()[N] without prior emptiness guard
PY_SPLIT_INDEX = re.compile(r'\.split\s*\([^)]*\)\s*\[')

# 8b: float(x) / int(x) where x could be None
PY_UNSAFE_CAST = re.compile(r'\b(float|int)\s*\(\s*(\w+)\s*\)')

# 8c: .get(key, default) null trap — key exists with value None, default is skipped
PY_GET_FALSY_DEFAULT = re.compile(r'\.get\s*\(\s*["\'][^"\']+["\']\s*,\s*(0|0\.0|\[\]|\{\}|"")\s*\)')

# 8d: psycopg2 connection opened without close in finally
PY_CONN_OPEN = re.compile(r'\bpsycopg2\.connect\b|\b_get_conn\s*\(')
PY_CONN_CLOSE = re.compile(r'\.close\s*\(|finally\s*:')

# Guards that make .split()[N] safe
PY_SPLIT_GUARDS = [
    re.compile(r'\.strip\s*\(\s*\)\.split'),       # .strip().split()
    re.compile(r'if\s+\w+.*\.strip\s*\(\s*\)'),    # if x.strip()
    re.compile(r'if\s+\w+\s+and\s+\w+\.strip'),    # if x and x.strip()
    re.compile(r'or\s+["\']'),                       # .split()[0] or "default"
    re.compile(r'\.split\s*\([^)]*\)\s*\[\s*0\s*\]\s+if\s+'),  # conditional expression
]


def scan_diff_for_python_adversarial(
    diff_files: list[str], project_dir: str
) -> list[str]:
    """Scan changed Python files for adversarial edge cases.

    8a: .split()[N] on strings that could be empty/whitespace → IndexError
    8b: float(x)/int(x) where x could be None → TypeError
    8c: .get(key, falsy_default) where key can exist with value None → null trap
    8d: psycopg2 connection opened without close/finally → connection leak
    """
    errors = []
    if not project_dir:
        return errors

    for filepath in diff_files:
        if not filepath.endswith('.py'):
            continue
        fp_lower = filepath.lower().replace('\\', '/')
        if '/test' in fp_lower or fp_lower.startswith('test'):
            continue

        full_path = os.path.join(project_dir, filepath)
        if not os.path.exists(full_path):
            continue
        # Skip qa_gate.py itself — internal dict reads are not external input
        if os.path.basename(filepath) == 'qa_gate.py':
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError):
            continue

        # Pre-compute docstring regions
        in_docstring = [False] * len(lines)
        inside = False
        for idx, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith('"""') or s.startswith("'''"):
                delim = s[:3]
                count = s.count(delim)
                if count == 1:
                    inside = not inside
            in_docstring[idx] = inside or s.startswith('"""') or s.startswith("'''")

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") or in_docstring[i]:
                continue
            if "qa-ignore" in line:
                continue

            # --- 8a: .split()[N] without strip guard ---
            if PY_SPLIT_INDEX.search(line):
                window = "".join(lines[max(0, i - 3):min(len(lines), i + 2)])
                guarded = any(g.search(window) for g in PY_SPLIT_GUARDS)
                if not guarded:
                    errors.append(
                        f"Python adversarial: {filepath}:{i + 1} uses .split()[N] "
                        f"without a prior .strip() or emptiness check. "
                        f"Empty/whitespace input causes IndexError."
                    )

            # --- 8b: float(x)/int(x) on potentially-None variable ---
            cast_match = PY_UNSAFE_CAST.search(line)
            if cast_match:
                cast_func = cast_match.group(1)
                var_name = cast_match.group(2)
                # Skip safe patterns: literals, len(), constants, loop vars
                if var_name in ('0', '1', '2', 'True', 'False', 'None'):
                    continue
                # Check if var comes from .get(), DB row, or Optional param
                window = "".join(lines[max(0, i - 10):i + 1])
                from_external = any(p in window for p in (
                    f'{var_name} = ', '.get(', f'{var_name}:', 'Optional',
                    'row[', 'fetchone', 'fetchall',
                ))
                if from_external:
                    # Check for None guard
                    guard_window = "".join(lines[max(0, i - 5):i + 1])
                    has_guard = any(p in guard_window for p in (
                        f'if {var_name}', f'{var_name} is not None',
                        f'{var_name} or ', f'{var_name} if ',
                    ))
                    if not has_guard:
                        errors.append(
                            f"Python adversarial: {filepath}:{i + 1} calls "
                            f"{cast_func}({var_name}) but {var_name} may be None "
                            f"(from DB/.get()/Optional). Add a None guard."
                        )

            # --- 8c: .get(key, falsy_default) null trap ---
            get_match = PY_GET_FALSY_DEFAULT.search(line)
            if get_match:
                default_val = get_match.group(1)
                # Only flag if the key's value could legitimately be None
                # (heuristic: if the result feeds into arithmetic or iteration)
                window_after = "".join(lines[i:min(len(lines), i + 5)])
                feeds_into_math = bool(re.search(
                    r'[\+\-\*/]|\.append|for\s+\w+\s+in|len\s*\(',
                    window_after
                ))
                if feeds_into_math:
                    errors.append(
                        f"Python adversarial: {filepath}:{i + 1} uses "
                        f".get(key, {default_val}) but if key exists with value None, "
                        f"the default is NOT used. Use 'val or {default_val}' after."
                    )

        # --- 8d: connection leak check (whole-file) ---
        file_text = "".join(lines)
        if PY_CONN_OPEN.search(file_text):
            if not PY_CONN_CLOSE.search(file_text):
                errors.append(
                    f"Python adversarial: {filepath} opens a psycopg2 connection "
                    f"but no .close() or finally: block found. Connection leak risk."
                )

    return errors


# ─── Layer 9: Untyped method call scanner (TS) ──────────────────────────────

# Methods that crash on wrong types (calling on number, null, undefined)
TS_STRING_METHODS = re.compile(
    r'(\w+)\.(?:toUpperCase|toLowerCase|trim|trimStart|trimEnd|split|replace|replaceAll'
    r'|startsWith|endsWith|includes|match|search|slice|substring|padStart|padEnd)\s*\('
)

# Pattern templates showing the variable's source is untyped external input.
# These are raw strings with {var} placeholder — compiled per-variable at scan time.
TS_UNTYPED_SOURCE_TEMPLATES = [
    r'(?:const|let)\s*\{{[^}}]*\b{var}\b[^}}]*\}}\s*=\s*(?:body|params|query|req\.json|request\.json|data|result|row)',
    r'\b{var}\s*=\s*(?:body|params|query|req|request)\s*\.\s*\w+',
    r'\b{var}\s*=\s*\w+\.get\s*\(',
    r'\b{var}\s*:\s*(?:any|unknown|string\s*\|\s*null|string\s*\|\s*undefined)',
]

# Guard templates that make the method call safe
TS_STRING_GUARD_TEMPLATES = [
    r'typeof\s+{var}\s*===?\s*[\'"]string[\'"]',
    r'{var}\s*\?\.\s*(?:toUpperCase|toLowerCase|trim|split)',
    r'String\s*\(\s*{var}\s*\)',
    r'{var}\s+(?:as|instanceof)\s+string',
    r'if\s*\(\s*typeof\s+{var}',
    r'if\s*\(\s*{var}\s*&&\s*typeof\s+{var}',
    r'if\s*\(\s*!{var}\s*\)',          # if (!var) early return narrows to truthy
    r'if\s*\(\s*{var}\s*\)',           # if (var) block narrows to truthy
    r'{var}\s*=\s*\w+\.match\s*\(',    # regex match reassignment (always string)
]


def scan_diff_for_untyped_method_calls(
    diff_files: list[str], project_dir: str
) -> list[str]:
    """Scan changed TS/JS files for string method calls on untyped input.

    Detects .toUpperCase(), .trim(), .split() etc. on variables that come
    from req.json(), body destructuring, or other untyped sources, without
    a typeof guard or optional chaining.
    """
    errors = []
    if not project_dir:
        return errors

    for filepath in diff_files:
        if not filepath.endswith(('.ts', '.tsx', '.js', '.jsx')):
            continue
        fp_lower = filepath.lower().replace('\\', '/')
        if '/test' in fp_lower or fp_lower.startswith('test'):
            continue

        full_path = os.path.join(project_dir, filepath)
        if not os.path.exists(full_path):
            continue

        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError):
            continue

        # Track which (variable, function_scope) pairs have already been reported
        # to avoid duplicate warnings for the same var in a chain of calls
        reported_vars: set[str] = set()

        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*")):
                continue
            if "qa-ignore" in line and "untyped-method" in line:
                continue

            match = TS_STRING_METHODS.search(line)
            if not match:
                continue

            var_name = match.group(1)

            # Deduplicate: only report first unguarded use per variable per file
            if var_name in reported_vars:
                continue
            # Skip obvious safe patterns: string literals, 'this', well-known objects
            if var_name in ('this', 'JSON', 'Math', 'console', 'window', 'document',
                            'Object', 'Array', 'Date', 'RegExp', 'process', 'String',
                            'Buffer', 'Error', 'Promise', 'path'):
                continue
            # Skip if it's a string literal method call like "hello".toUpperCase()
            if re.search(rf'["\'][^"\']*["\']\.(?:toUpperCase|toLowerCase)', line):
                continue
            # Skip if already using optional chaining on this specific call
            if re.search(rf'{re.escape(var_name)}\?\.', line):
                continue

            # Check if variable comes from untyped source (look back 30 lines)
            var_escaped = re.escape(var_name)
            lookback = "".join(lines[max(0, i - 30):i + 1])
            from_untyped = any(
                re.search(tmpl.format(var=var_escaped), lookback)
                for tmpl in TS_UNTYPED_SOURCE_TEMPLATES
            )

            if not from_untyped:
                continue

            # Check if there's a type guard in the window. 30 lines back covers
            # function-level null checks before long chains of method calls —
            # e.g. if(!partNumber) early return followed by 25+ .startsWith() branches.
            guard_window = "".join(lines[max(0, i - 30):i + 1])
            has_guard = any(
                re.search(tmpl.format(var=var_escaped), guard_window)
                for tmpl in TS_STRING_GUARD_TEMPLATES
            )

            if not has_guard:
                method_name = re.search(
                    r'\.(\w+)\s*\(', line[match.start():]
                )
                method = method_name.group(1) if method_name else "method"
                reported_vars.add(var_name)
                errors.append(
                    f"Untyped method: {filepath}:{i + 1} calls "
                    f"{var_name}.{method}() but {var_name} comes from "
                    f"untyped input (body/params/query). Add 'typeof {var_name} "
                    f"=== \"string\"' guard or use optional chaining ({var_name}?.{method}())."
                )

    return errors


# ─── Layer 10: Doc-claim check (OBSERVATION MODE — reports, blocks nothing) ──
#
# ORIGIN: 2026-08-07/08. Four times in two days a session acted on a false
# premise that came from a DOCUMENT, not from code: services/CLAUDE.md's Threat
# Radar claim, "13/16 human confirmations" that were zero, a pre-written APRA
# test that never existed, and a v1.2 changelog entry for a module whose only
# version is 1.1. Every layer above this one checks CODE. Nothing checked the
# documents describing it.
#
# Scope is the tractable half only — a resolvable path, a version literal
# attributed to a code constant, a dependency that is actually installed. It
# cannot decide "Threat Radar uses this pipeline" or "13 people confirmed", and
# the messages say so rather than implying broader cover.
#
# OBSERVATION MODE, deliberately. Findings print; `passed` is untouched. This
# project's own incident log holds a lint that blocked a routine merge on day
# one (DQ-34, alarm fatigue), so blocking is earned with an observed
# false-positive rate, not assumed. See the PR body for what would earn it.


def _load_doc_claims():
    """Load the sibling module by path.

    qa_gate.py is executed both as a script (scripts/ on sys.path) and via
    importlib.util.spec_from_file_location from tests (scripts/ NOT on
    sys.path), so a plain `import doc_claims` works in one case and not the
    other. Returning None on failure is correct here and only here: an
    observation-mode check that cannot load must not break the gate that
    surrounds it.
    """
    try:
        import importlib.util

        path = Path(__file__).resolve().parent / "doc_claims.py"
        spec = importlib.util.spec_from_file_location("qa_gate_doc_claims", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 — observation mode never breaks the gate
        return None


def observe_doc_claims(
    report_path: str | None, diff_files: list[str] | None, project_dir: str | None
) -> list[str]:
    """Return human-readable observations. NEVER returns blocking errors."""
    if not project_dir:
        return ["doc-claim check: SKIPPED — no project dir (unknowable, not a pass)"]

    module = _load_doc_claims()
    if module is None:
        return [
            "doc-claim check: SKIPPED — scripts/doc_claims.py could not be loaded "
            "(unknowable, not a pass)"
        ]

    # Diff-scoped, like every other file scanner here: the whole 124-doc corpus
    # carries inherited findings, and re-printing them on an unrelated change is
    # how a check gets ignored.
    docs = sorted({f for f in (diff_files or []) if f.endswith(".md")})
    reports = [report_path] if report_path else []
    if not docs and not reports:
        return []

    try:
        result = module.scan(project_dir, docs=docs, reports=reports)
    except Exception as exc:  # noqa: BLE001
        return [f"doc-claim check: SKIPPED — scan raised {type(exc).__name__}: {exc}"]

    baseline = module.load_baseline(Path(project_dir))
    known = set(baseline.get("fingerprints") or []) if baseline else set()
    fresh = [v for v in result.violations if v.fingerprint() not in known]

    out: list[str] = []
    for v in fresh:
        out.append(f"doc-claim {v.render()}")  # render() already carries the kind
    for note in result.notes:
        out.append(f"doc-claim ? {note}")
    if fresh:
        carried = len(result.violations) - len(fresh)
        out.append(
            f"doc-claim: {len(fresh)} new finding(s), {carried} already in the "
            f"baseline. Observation mode — nothing is blocked. Scope is paths, "
            f"version literals and dependency declarations only; a semantic "
            f"claim about behaviour is NOT checked and a clean run does not mean "
            f"the doc is true."
        )
    return out


# ─── Commit-hash binding ─────────────────────────────────────────────────────


def _git_query(
    args: list[str], project_dir: str, timeout: int = 5
) -> tuple[Optional[int], str]:
    """Run a git command.

    Returns:
        ``(returncode, stdout)``, or ``(None, "")`` when git could not be run at
        all. The None is load-bearing: "git is unusable" and "git said no" are
        different facts, and collapsing them is how a gate starts failing open
        without anyone noticing.
    """
    try:
        proc = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=project_dir or ".",
            # A hook exports GIT_DIR and it OVERRIDES cwd, so without this the
            # binding would be checked against the hook's repository rather than
            # the one being validated. See qa_report_path.git_env.
            env=qa_report_path.git_env(),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None, ""
    return proc.returncode, proc.stdout.strip()


def _is_ancestor(sha: str, ref: str, project_dir: str) -> Optional[bool]:
    """Whether ``sha`` is an ancestor of ``ref``.

    Returns None when git could not answer. ``merge-base --is-ancestor`` uses 0
    for yes and 1 for no; any other code is an error (a bad ref, a corrupt
    object) and must NOT be read as "no".
    """
    code, _ = _git_query(["merge-base", "--is-ancestor", sha, ref], project_dir)
    if code == 0:
        return True
    if code == 1:
        return False
    return None


def check_commit_hash_binding(report_hash: str, project_dir: str) -> list[str]:
    """Verify the report names one of THIS BRANCH'S OWN commits.

    A branch's own commit is an ancestor of HEAD that is not already an ancestor
    of ``origin/main``. That is the whole test, and it catches every case the
    old rule was written for:

    ==============================  ==========================  ========
    report names                    ancestry                    verdict
    ==============================  ==========================  ========
    a commit on another branch      not an ancestor of HEAD     caught
    a commit already on main        an ancestor of origin/main  caught
    a hash that resolves to nothing does not resolve            caught
    one of this branch's commits    both conditions hold        passes
    ==============================  ==========================  ========

    WHY NOT "the last 5 commits"
    ----------------------------
    The previous rule required the hash to appear in ``git log --format=%h -5``.
    A **squash merge destroys the commit the report names**: the squash is a new
    hash and the branch's own commits never enter main's history. So main
    permanently carried a ``commit_hash`` present in no history, and every
    branch cut from main inherited it and failed the gate before it had done
    anything wrong. Landing five PRs on 2026-08-10 needed a manual re-stamp on
    each, and amending the stamp into the commit it names is self-referential --
    the amend changes the hash just recorded. The rule was unsatisfiable by
    construction; ancestry is satisfiable by construction.

    It is also robust where the old rule was brittle: ``merge-base
    --is-ancestor`` operates on resolved SHAs, so an abbreviation of any length
    works. The old string-compare against ``%h`` broke whenever git chose a
    different abbreviation length on either side.

    Args:
        report_hash: The ``commit_hash`` field from the report.
        project_dir: Repository root.

    Returns:
        Error strings; empty when the binding holds, and empty when git cannot
        answer -- an unusable git or an absent ``origin/main`` is an
        infrastructure fact, not evidence about the report, and blocking on it
        would make the gate red in every environment without a remote.
    """
    code, sha = _git_query(
        ["rev-parse", "--verify", "--quiet", f"{report_hash}^{{commit}}"], project_dir
    )
    if code is None:
        return []
    if code != 0 or not sha:
        return [
            f"Commit hash '{report_hash}' names no commit in this repository. "
            f"Re-stamp it: git rev-parse --short HEAD"
        ]

    # Does this branch have any commits of its own? On main -- or on a branch
    # that is fully merged -- it does not, and the question is unanswerable
    # rather than failed. Not skipping here is what made every push to main red
    # under the old rule, and a gate that can only ever be red teaches people
    # that red means nothing.
    code, own = _git_query(["rev-list", "--count", "origin/main..HEAD"], project_dir)
    if code is None or code != 0 or own.strip() in ("", "0"):
        return []

    on_branch = _is_ancestor(sha, "HEAD", project_dir)
    if on_branch is None:
        return []
    if not on_branch:
        return [
            f"Commit hash '{report_hash}' is not an ancestor of HEAD — this "
            f"report belongs to a different branch. Re-stamp it: "
            f"git rev-parse --short HEAD"
        ]

    already_on_main = _is_ancestor(sha, "origin/main", project_dir)
    if already_on_main is None:
        return []
    if already_on_main:
        return [
            f"Commit hash '{report_hash}' names a commit already on origin/main, "
            f"not one of this branch's own {own} commit(s) — the report is "
            f"inherited or stale. Re-stamp it: git rev-parse --short HEAD"
        ]
    return []


# ─── Main validation ─────────────────────────────────────────────────────────


def validate_report(
    report: dict,
    diff_files: list[str] | None = None,
    project_dir: str | None = None,
) -> tuple[bool, list[str], str]:
    """Validate a QA report against its declared tier.

    Returns (passed, errors, summary_line).
    """
    errors = []
    warnings = []

    # --- Section 1: Tier ---
    tier = report.get("tier", "").lower()
    if tier not in TIER_REQUIREMENTS:
        return False, [f"Invalid tier: '{tier}'. Must be critical/standard/minor."], ""

    reqs = TIER_REQUIREMENTS[tier]
    justification = report.get("justification", "")
    files = report.get("files", [])
    min_words = reqs["min_words_per_field"]

    if not justification.strip():
        errors.append("Section 1: missing tier justification")
    if not files:
        errors.append("Section 1: no files listed")

    errors.extend(check_falsifiable(report, reqs))

    # --- Section 2: Pre-implementation ---
    if 2 in reqs["sections_required"]:
        pre_impl = report.get("pre_impl", {})
        for field in reqs["pre_impl_fields"]:
            val = pre_impl.get(field, "")
            errors.extend(validate_non_empty(val, f"Section 2 pre_impl.{field}"))
            errors.extend(validate_min_words(val, f"Section 2 pre_impl.{field}", min_words))

    # --- Section 3: Functions ---
    if 3 in reqs["sections_required"]:
        functions = report.get("functions", [])
        if isinstance(functions, str) and functions.strip().upper().startswith("N/A"):
            pass
        elif len(functions) < reqs["min_functions"]:
            errors.append(f"Section 3: need >= {reqs['min_functions']} functions documented, got {len(functions)}")
        else:
            for i, fn in enumerate(functions):
                for key in ("name", "file_line", "input", "output", "if_none"):
                    val = fn.get(key, "")
                    errors.extend(validate_non_empty(val, f"Section 3 functions[{i}].{key}"))
                # Depth check on descriptive fields
                for key in ("input", "output", "if_none"):
                    errors.extend(validate_min_words(
                        fn.get(key, ""), f"Section 3 functions[{i}].{key}", min_words
                    ))

            # AST grounding (Python files only)
            if project_dir:
                errors.extend(ast_ground_functions(functions, project_dir))

    # --- Section 4: Values from DB/API/optional ---
    if 4 in reqs["sections_required"]:
        values = report.get("values", [])
        if isinstance(values, str) and values.strip().upper().startswith("N/A"):
            pass
        elif values:
            for i, val in enumerate(values):
                for key in ("value", "read_at", "if_missing"):
                    errors.extend(validate_non_empty(val.get(key, ""), f"Section 4 values[{i}].{key}"))

    # --- Section 5: DB queries ---
    if 5 in reqs["sections_required"]:
        queries = report.get("queries", [])
        if isinstance(queries, str) and queries.strip().upper().startswith("N/A"):
            pass
        elif queries:
            for i, q in enumerate(queries):
                for key in ("purpose", "file_line", "where_clause"):
                    errors.extend(validate_non_empty(q.get(key, ""), f"Section 5 queries[{i}].{key}"))

    # --- Section 6: Break it ---
    break_it = report.get("break_it", [])
    if len(break_it) < reqs["min_break_it"]:
        errors.append(f"Section 6: need >= {reqs['min_break_it']} break-it scenarios, got {len(break_it)}")
    else:
        for i, scenario in enumerate(break_it):
            for key in ("scenario", "what_happens"):
                val = str(scenario.get(key, ""))
                errors.extend(validate_non_empty(val, f"Section 6 break_it[{i}].{key}"))
                errors.extend(validate_min_words(val, f"Section 6 break_it[{i}].{key}", min_words))
            errors.extend(validate_non_empty(
                str(scenario.get("mitigated", "")), f"Section 6 break_it[{i}].mitigated"
            ))
            if scenario.get("mitigated") and not scenario.get("how"):
                errors.append(f"Section 6 break_it[{i}]: marked mitigated but no 'how' explanation")

        # Uniqueness check
        errors.extend(check_break_it_uniqueness(break_it))

    # --- Section 7: Post-merge ---
    if 7 in reqs["sections_required"]:
        post_merge = report.get("post_merge", {})
        for field in ("db_reset", "secrets", "other_repo", "manual_verify"):
            errors.extend(validate_non_empty(post_merge.get(field, ""), f"Section 7 post_merge.{field}"))

    # --- Cross-cutting checks ---
    if diff_files:
        errors.extend(check_diff_coverage(files, diff_files))

        # --- Tier floor: prevent Minor classification on large changes ---
        substantive_diff = [
            f for f in diff_files
            if not f.startswith(".") and not f.endswith((".json", ".md", ".txt", ".yml", ".yaml"))
            and "config" not in f.lower()
        ]
        if tier == "minor" and len(substantive_diff) > 3:
            errors.append(
                f"Tier floor: {len(substantive_diff)} substantive files changed — "
                f"'minor' tier requires <= 3. Reclassify as 'standard' or 'critical'."
            )

    # --- Commit hash binding: detect stale/copied reports ---
    # The report must name one of THIS BRANCH'S OWN commits — an ancestor of
    # HEAD that is not already an ancestor of origin/main. See
    # check_commit_hash_binding for why "within the last 5 commits" was
    # unsatisfiable by construction after a squash merge.
    report_hash = report.get("commit_hash", "")
    if report_hash:
        errors.extend(check_commit_hash_binding(report_hash, project_dir or "."))
    elif tier in ("standard", "critical"):
        errors.append(
            "Missing commit_hash in report. Add \"commit_hash\": \"<short-hash>\" "
            "matching the current HEAD. Run: git rev-parse --short HEAD"
        )

    # --- File-content scanners (DB guard, null guard, type boundaries, silent
    #     failures, Python adversarial, untyped method calls).
    #     DIFF-SCOPED: findings on lines the change did not touch are dropped, so
    #     brushing a pre-existing file does not force fixing its unrelated debt.
    #     filter_to_changed_lines falls back to keeping everything when git cannot
    #     determine the changed lines, so the gate never weakens when uncertain. ---
    if diff_files and project_dir:
        scanner_errors: list[str] = []
        scanner_errors.extend(scan_diff_for_unguarded_queries(diff_files, project_dir))
        scanner_errors.extend(scan_diff_for_unguarded_nulls(diff_files, project_dir))
        scanner_errors.extend(scan_diff_for_type_boundaries(diff_files, project_dir))
        scanner_errors.extend(scan_diff_for_silent_failures(diff_files, project_dir))
        scanner_errors.extend(scan_diff_for_python_adversarial(diff_files, project_dir))
        scanner_errors.extend(scan_diff_for_untyped_method_calls(diff_files, project_dir))
        errors.extend(
            filter_to_changed_lines(
                scanner_errors, changed_line_numbers(diff_files, project_dir)
            )
        )

    if tier in ("standard", "critical"):
        errors.extend(check_cross_references(report))

    # --- Break-it repro field: force specificity ---
    if tier in ("standard", "critical") and break_it:
        missing_repro = [
            i for i, s in enumerate(break_it)
            if not s.get("repro")
        ]
        if missing_repro:
            errors.append(
                f"Section 6: break-it scenarios {missing_repro} missing 'repro' field. "
                f"Each scenario needs a concrete reproduction step (curl, pytest command, "
                f"SQL query, or UI action that would trigger the failure)."
            )

    # --- Build summary ---
    n_functions = len(report.get("functions", [])) if isinstance(report.get("functions"), list) else 0
    n_values = len(report.get("values", [])) if isinstance(report.get("values"), list) else 0
    n_queries = len(report.get("queries", [])) if isinstance(report.get("queries"), list) else 0
    n_break = len(break_it)
    has_post_merge_action = any(
        v.strip().lower().startswith("yes")
        for v in report.get("post_merge", {}).values()
        if isinstance(v, str)
    )

    sections_filled = ",".join(str(s) for s in reqs["sections_required"])
    findings_summary = f"{len(errors)} errors" if errors else "0 findings"
    post_merge_note = " — post-merge action required" if has_post_merge_action else ""
    ast_note = " [AST-verified]" if project_dir else ""

    summary = (
        f"QA: {tier.title()} — sections {sections_filled} — "
        f"{n_functions}fn {n_values}val {n_queries}q {n_break}brk — "
        f"{findings_summary}{post_merge_note}{ast_note}"
    )

    passed = len(errors) == 0
    return passed, errors, summary


# ─── Reachability: will git actually carry this report? ─────────────────────
# ORIGIN: 2026-08-12, branch test/feedback-route-validation. Its report slug was
# .qa/reports/test__feedback-route-validation.json, which matched `test_*.json`
# in .gitignore. `git add` silently did nothing, the commit reported success,
# and THIS GATE PRINTED PASSED — because it validates a file on disk and never
# asked git whether the file would ever leave this machine.
#
# That combination is strictly worse than a missing report. Both enforcing
# callers share one shape:
#     if [ -f "$REPORT" ]; then run the gate; else warn; exit 0; fi
# (.githooks/pre-push:214 and .github/workflows/gates.yml:195). An ignored
# report EXISTS locally, so the gate runs and passes; it is absent from the CI
# checkout, so CI warns and exits 0. Green in both places, enforcing nothing.
# #398 is the same defect and it hid for ten weeks.
#
# Two conditions, deliberately not equally strict:
#   IGNORED     — never legitimate. A report git refuses to stage can never
#                 reach CI, so this fails unconditionally.
#   NOT TRACKED — legitimate right up until the first `git add`, which is
#                 exactly when a human or Claude runs this gate by hand. So it
#                 is gated behind --require-tracked, passed by pre-push, where
#                 the report must already be committed to be pushed at all.
# CI needs no flag: a report present in the checkout is tracked by construction.


def _git(args: list[str], project_dir: str) -> tuple[int, str]:
    """Run a git command against project_dir, returning (returncode, stdout).

    GIT_* is scrubbed from the environment, and that is load-bearing rather
    than tidiness. Git hooks export GIT_DIR and GIT_INDEX_FILE, and those
    OVERRIDE cwd — so this function's main caller, the pre-push hook, would
    otherwise ask about whatever repository git was invoked from instead of
    the one being checked. It is the same trap that once let a test `git init`
    a tmpdir, silently operate on the real repository, and still pass. Caught
    here by test_staged_counts_as_tracked, which passed standalone and failed
    under pre-push until this scrub was added.

    Never raises: a gate that crashes on a missing git binary is a gate that
    gets bypassed.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode, proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        # git absent, or not executable. Reported as "cannot determine" (128)
        # rather than silently as "fine" — the whole point of this section.
        return 128, ""


def check_report_reachable(
    report_path: str, project_dir: str | None, require_tracked: bool
) -> list[str]:
    """Fail when git will not carry this report to CI.

    Returns a list of errors, so it composes with the existing validation.
    """
    errors: list[str] = []
    root = project_dir or "."
    rel = os.path.relpath(os.path.abspath(report_path), os.path.abspath(root))
    rel = rel.replace(os.sep, "/")

    # `git check-ignore -q`: 0 = ignored, 1 = not ignored, 128 = cannot say.
    code, _ = _git(["check-ignore", "-q", "--", rel], root)
    if code == 0:
        _, which = _git(["check-ignore", "-v", "--", rel], root)
        errors.append(
            f"Report is GITIGNORED and can never reach CI: {rel}\n"
            f"    matched by: {which or '(pattern unknown)'}\n"
            "    `git add` will silently do nothing, the commit will report success, "
            "and CI treats an absent report as a warning and exits 0 — so this gate "
            "would pass while enforcing nothing. Add a negation such as "
            "`!.qa/reports/*.json`, or rename the branch."
        )
        return errors  # an ignored file cannot also be tracked; one clear error

    if code == 128 and require_tracked:
        errors.append(
            f"Cannot determine whether {rel} is tracked — `git check-ignore` failed "
            "and --require-tracked was set. Failing closed: an unverifiable report is "
            "not a verified one."
        )
        return errors

    if not require_tracked:
        return errors

    # Tracked OR staged. `ls-files --error-unmatch` covers both, because a
    # staged new file is already in the index.
    code, _ = _git(["ls-files", "--error-unmatch", "--", rel], root)
    if code != 0:
        errors.append(
            f"Report is not tracked and not staged: {rel}\n"
            "    It exists on this machine only. Pushing now sends a branch whose "
            "report CI will never see, and CI treats an absent report as a warning "
            "and exits 0. Run: git add "
            f"{rel}"
        )
    return errors


def main():
    # The report path is optional. Omitted, it is resolved for the current
    # branch by qa_report_path — the single definition every caller shares, so
    # the hook, the workflow and this gate cannot drift onto different files.
    positional = sys.argv[1:2]
    explicit_path = (
        positional[0] if positional and not positional[0].startswith("--") else None
    )

    # Parse optional args
    diff_files = None
    project_dir = None
    require_tracked = False

    args = sys.argv[2:] if explicit_path else sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--require-tracked":
            require_tracked = True
            i += 1
        elif args[i] == "--diff-files":
            # Collect all remaining args until next flag or end
            diff_files = []
            i += 1
            while i < len(args) and not args[i].startswith("--"):
                diff_files.append(args[i])
                i += 1
        elif args[i] == "--project-dir":
            i += 1
            if i < len(args):
                project_dir = args[i]
                i += 1
        else:
            i += 1

    # Auto-detect project dir if not specified
    if not project_dir:
        # Walk up from the report file — or from cwd when the path is still to
        # be resolved — to find .git (dir or file; worktrees use a file)
        check = (
            os.path.dirname(os.path.abspath(explicit_path))
            if explicit_path
            else os.path.abspath(".")
        )
        for _ in range(10):
            if os.path.exists(os.path.join(check, ".git")):
                project_dir = check
                break
            parent = os.path.dirname(check)
            if parent == check:
                break
            check = parent

    resolved = qa_report_path.resolve(project_dir or ".", explicit_path)
    if resolved is None:
        if explicit_path:
            print(f"QA-GATE: FAILED — report file not found: {explicit_path}")
        else:
            try:
                expected = qa_report_path.target_path(project_dir or ".")
                where = os.path.relpath(expected, project_dir or ".")
            except (qa_report_path.BranchUnknown, ValueError) as exc:
                where = f"<undetermined: {exc}>"
            print(
                f"QA-GATE: FAILED — no QA report for this branch.\n"
                f"  Expected: {where}\n"
                f"  Create it from scripts/qa_report_template.json."
            )
        sys.exit(1)
    report_path = str(resolved)

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        print(f"QA-GATE: FAILED — invalid JSON: {e}")
        sys.exit(1)

    passed, errors, summary = validate_report(report, diff_files, project_dir)

    # Reachability is checked AFTER the content validation but folded into the
    # same verdict, so a report that is both wrong and unreachable reports both
    # rather than hiding one behind the other.
    reach_errors = check_report_reachable(report_path, project_dir, require_tracked)
    if reach_errors:
        errors = list(errors) + reach_errors
        passed = False

    # Observation mode. Printed before the verdict so it is visible on a pass
    # too, and deliberately NOT folded into `passed` or `errors`.
    observations = observe_doc_claims(report_path, diff_files, project_dir)
    if observations:
        print("QA-GATE: doc-claim observations (not blocking):")
        for note in observations:
            print(f"  ~ {note}")
        print()

    if passed:
        print("QA-GATE: PASSED")
        print(summary)
    else:
        print(f"QA-GATE: FAILED — {len(errors)} validation errors:")
        for err in errors:
            print(f"  - {err}")
        print()
        print(f"Tier: {report.get('tier', '?')}")
        print("Fix these errors, update the report, and re-run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
