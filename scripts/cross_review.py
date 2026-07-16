#!/usr/bin/env python3
"""Cross-family code review: audit Claude-authored changes with GPT-5.6 Sol.

An *independent* reviewer that never shares the primary agent's context. It sends
a git diff (local branch vs a base, or a GitHub PR) to a non-Anthropic frontier
model together with this repo's own pre-PR-review checklist, and prints ranked
findings. It is advisory: it reads git + calls the OpenAI API and writes nothing
except an optional JSON report. Suggestions are a worklist to verify, never an
auto-applied change and never (by default) a merge gate.

Why a separate provider: a second Claude reviewing Claude shares training priors
and the same blind spots. A different model family decorrelates them. GPT-5.6 Sol
is (as of 2026-07) the top-ranked coding model, so this buys diversity without
trading down the reviewer.

Usage:
    # Review the current branch vs origin/main:
    python scripts/cross_review.py

    # Review a GitHub PR by number (uses `gh pr diff`):
    python scripts/cross_review.py --pr 729

    # Only the staged diff, write a JSON report, fail if a high finding appears:
    python scripts/cross_review.py --staged --out review.json --fail-on high

The OpenAI key is read from OPENAI_API_KEY, or from the repo-root .env if unset.
Never hardcode a key here (see scripts/openai_semantic_processor.py for what not
to do — it has a committed key that must be rotated).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CHECKLIST_PATH = _REPO_ROOT / ".claude" / "rules" / "pre-pr-review.md"
_DEFAULT_MODEL = "gpt-5.6-sol"  # alias "gpt-5.6" also routes here
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _candidate_env_paths() -> list[Path]:
    """.env locations to try: this checkout, and the main worktree's root.

    .env is git-ignored, so a worktree checkout does not contain one — it lives in
    the main checkout. `git --git-common-dir` points at <main>/.git, whose parent is
    the main worktree root.
    """
    paths = [_REPO_ROOT / ".env"]
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=_REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        if common.returncode == 0 and common.stdout.strip():
            main_env = Path(common.stdout.strip()).parent / ".env"
            if main_env not in paths:
                paths.append(main_env)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return paths


def load_api_key() -> str:
    """Return the OpenAI key from env, falling back to a parse of a repo .env.

    Raises SystemExit with a clear message if no key is found — never guesses.
    """
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key.strip()

    for env_path in _candidate_env_paths():
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "OPENAI_API_KEY":
                return value.strip().strip('"').strip("'")

    sys.exit(
        "No OPENAI_API_KEY found in the environment or a repo .env.\n"
        "Set it before running: export OPENAI_API_KEY=sk-..."
    )


def get_diff(args: argparse.Namespace) -> str:
    """Collect the unified diff to review, or exit if it is empty/too large."""
    if args.pr:
        cmd = ["gh", "pr", "diff", str(args.pr)]
    elif args.staged:
        cmd = ["git", "diff", "--staged"]
    else:
        # Everything on this branch that is not yet on the base.
        cmd = ["git", "diff", f"{args.base}...HEAD"]

    try:
        proc = subprocess.run(
            cmd, cwd=_REPO_ROOT, capture_output=True, text=True, timeout=60
        )
    except FileNotFoundError:
        sys.exit(f"Command not found: {cmd[0]} (is it installed / on PATH?)")
    except subprocess.TimeoutExpired:
        sys.exit(f"Timed out collecting the diff: {' '.join(cmd)}")

    if proc.returncode != 0:
        sys.exit(f"Failed to collect diff ({' '.join(cmd)}):\n{proc.stderr.strip()}")

    diff = proc.stdout
    if not diff.strip():
        sys.exit("Empty diff — nothing to review.")

    max_bytes = args.max_diff_kb * 1024
    if len(diff.encode("utf-8")) > max_bytes:
        sys.exit(
            f"Diff is {len(diff.encode('utf-8')) // 1024} KB, over the "
            f"--max-diff-kb limit of {args.max_diff_kb} KB. Narrow the scope "
            "(review a subset of files, or raise the limit deliberately)."
        )
    return diff


def load_checklist() -> str:
    """Load the repo's pre-PR-review rubric, or a compact fallback if absent."""
    if _CHECKLIST_PATH.exists():
        return _CHECKLIST_PATH.read_text(encoding="utf-8", errors="ignore")
    return (
        "1. DB query filters — every SELECT has correct WHERE (is_active, council "
        "scope, no missing filters).\n"
        "2. Unguarded nulls — DB rows / API responses / optional fields null-checked.\n"
        "3. Type assumptions — types match at every boundary (DB->API->component).\n"
        "4. Silent failure modes — does failure surface visibly or serve wrong data "
        "silently? Silent is always worse.\n"
        "5. Liability language — user-facing text avoids safe/compliant/guaranteed/"
        "recommend etc. unless it is a regulatory quotation."
    )


def build_messages(diff: str, checklist: str) -> list[dict]:
    system = (
        "You are an independent senior code reviewer auditing changes written by a "
        "different AI coding agent for a NSW planning-compliance product. You do NOT "
        "share the author's context or assumptions — your job is to find what they "
        "missed.\n\n"
        "This codebase's worst failure mode is SILENT WRONG DATA served to users "
        "(a missing WHERE clause, an unguarded null coalescing to a plausible-but-"
        "wrong value, a type mismatch at a boundary). Rank those above style or "
        "cosmetic issues. Regulatory/legal-liability wording matters too.\n\n"
        "Review the diff strictly against this project's pre-PR checklist:\n\n"
        f"{checklist}\n\n"
        "Only report real defects you can point to a specific added/changed line for. "
        "Do not invent issues to fill a quota — an empty findings list is a valid, "
        "good result. For each finding give a concrete failure scenario (inputs -> "
        "wrong outcome), not a vague concern.\n\n"
        "Respond with ONLY a JSON object, no prose, of the form:\n"
        '{"findings": [{"file": "path", "line": <int or null>, '
        '"severity": "high|medium|low", "category": "db-filter|null-guard|'
        'type-boundary|silent-failure|liability|correctness|other", '
        '"issue": "one sentence", "failure_scenario": "inputs -> wrong result", '
        '"suggested_fix": "concrete change", "confidence": 0.0-1.0}]}'
    )
    user = f"Here is the unified diff to review:\n\n```diff\n{diff}\n```"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def call_model(messages: list[dict], model: str, api_key: str) -> dict:
    """Call the OpenAI Chat Completions API and parse the JSON findings object."""
    try:
        import openai  # already a repo dependency (see openai_semantic_processor.py)
    except ImportError:
        sys.exit(
            "The `openai` package is not installed in this environment.\n"
            "pip install openai  (or run from the env that has it)."
        )

    client = openai.OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as exc:  # network / auth / model-name errors
        sys.exit(f"OpenAI API call failed: {exc}")

    content = (response.choices[0].message.content or "").strip()
    if content.startswith("```"):
        content = content.split("```", 2)[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        sys.exit(f"Model did not return valid JSON: {exc}\nRaw:\n{content[:1000]}")

    findings = data.get("findings", []) if isinstance(data, dict) else []
    if not isinstance(findings, list):
        findings = []
    return {"findings": findings, "usage": getattr(response, "usage", None), "model": model}


def rank(findings: list[dict]) -> list[dict]:
    return sorted(
        findings,
        key=lambda f: (
            _SEVERITY_ORDER.get(str(f.get("severity", "low")).lower(), 3),
            -float(f.get("confidence", 0) or 0),
        ),
    )


def render(findings: list[dict], model: str) -> None:
    if not findings:
        print(f"\n✓ {model} found no defects in the reviewed diff.\n")
        return
    print(f"\n{model} — {len(findings)} finding(s), most severe first:\n")
    for i, f in enumerate(findings, 1):
        sev = str(f.get("severity", "?")).upper()
        loc = f.get("file", "?")
        if f.get("line"):
            loc += f":{f['line']}"
        conf = f.get("confidence")
        conf_s = f" (confidence {conf})" if conf is not None else ""
        print(f"{i}. [{sev}] {f.get('category', 'other')} — {loc}{conf_s}")
        print(f"   {f.get('issue', '').strip()}")
        if f.get("failure_scenario"):
            print(f"   Scenario: {f['failure_scenario'].strip()}")
        if f.get("suggested_fix"):
            print(f"   Fix: {f['suggested_fix'].strip()}")
        print()
    print("These are review candidates — verify each against the code before acting.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--pr", type=int, help="Review a GitHub PR by number (via gh pr diff).")
    src.add_argument("--staged", action="store_true", help="Review only the staged diff.")
    parser.add_argument("--base", default="origin/main", help="Base ref for the branch diff (default: origin/main).")
    parser.add_argument("--model", default=_DEFAULT_MODEL, help=f"OpenAI model id (default: {_DEFAULT_MODEL}).")
    parser.add_argument("--max-diff-kb", type=int, default=256, help="Refuse diffs larger than this many KB (default: 256).")
    parser.add_argument("--out", type=Path, help="Also write the findings JSON to this path.")
    parser.add_argument("--fail-on", choices=["high", "medium", "low"], help="Exit non-zero if a finding at/above this severity exists.")
    args = parser.parse_args()

    api_key = load_api_key()
    diff = get_diff(args)
    result = call_model(build_messages(diff, load_checklist()), args.model, api_key)
    findings = rank(result["findings"])
    render(findings, args.model)

    if args.out:
        args.out.write_text(json.dumps({"model": args.model, "findings": findings}, indent=2), encoding="utf-8")
        print(f"Report written to {args.out}")

    if args.fail_on:
        threshold = _SEVERITY_ORDER[args.fail_on]
        worst = min((_SEVERITY_ORDER.get(str(f.get("severity", "low")).lower(), 3) for f in findings), default=3)
        if worst <= threshold:
            sys.exit(2)


if __name__ == "__main__":
    main()
