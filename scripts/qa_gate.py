#!/usr/bin/env python3
"""QA Railguards — executable gate.

Validates a structured QA report JSON file against tier requirements.
Three layers of verification:
  1. Structure — required fields present, non-empty
  2. Grounding — file:line references verified against real code via AST
  3. Depth — minimum word counts, break-it uniqueness, cross-references

Usage:
    python scripts/qa_gate.py .qa_report.json
    python scripts/qa_gate.py .qa_report.json --diff-files file1.py file2.py
    python scripts/qa_gate.py .qa_report.json --project-dir /path/to/repo

Exit codes:
    0 = PASSED
    1 = FAILED
"""

import ast
import json
import sys
import os
import re
from pathlib import Path
from typing import Optional

TIER_REQUIREMENTS = {
    "critical": {
        "pre_impl_fields": ["existing_data", "assumption_mismatch", "new_vs_existing",
                            "external_source_error", "frontend_type", "user_failure_mode"],
        "min_functions": 1,
        "min_break_it": 5,
        "min_words_per_field": 8,
        "sections_required": [1, 2, 3, 4, 5, 6, 7],
    },
    "standard": {
        "pre_impl_fields": ["existing_data", "assumption_mismatch", "new_vs_existing"],
        "min_functions": 1,
        "min_break_it": 3,
        "min_words_per_field": 5,
        "sections_required": [1, 2, 3, 4, 5, 6, 7],
    },
    "minor": {
        "pre_impl_fields": [],
        "min_functions": 0,
        "min_break_it": 1,
        "min_words_per_field": 3,
        "sections_required": [1, 6, 7],
    },
}

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

    if tier in ("standard", "critical"):
        errors.extend(check_cross_references(report))

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


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/qa_gate.py .qa_report.json [--diff-files f1 f2 ...] [--project-dir path]")
        sys.exit(1)

    report_path = sys.argv[1]

    # Parse optional args
    diff_files = None
    project_dir = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--diff-files":
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
        # Walk up from report file to find .git
        check = os.path.dirname(os.path.abspath(report_path))
        for _ in range(10):
            if os.path.isdir(os.path.join(check, ".git")):
                project_dir = check
                break
            parent = os.path.dirname(check)
            if parent == check:
                break
            check = parent

    if not os.path.exists(report_path):
        print(f"QA-GATE: FAILED — report file not found: {report_path}")
        sys.exit(1)

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        print(f"QA-GATE: FAILED — invalid JSON: {e}")
        sys.exit(1)

    passed, errors, summary = validate_report(report, diff_files, project_dir)

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
