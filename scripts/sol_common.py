"""Shared helpers for the GPT-5.6 Sol developer tools (cross_review, ask_sol).

Key resolution and the OpenAI call live here so the tools don't duplicate them.
Read-only with respect to the repo; only touches the OpenAI API.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_report_path import git_env  # noqa: E402  (DQ-54)

DEFAULT_MODEL = "gpt-5.6-sol"  # alias "gpt-5.6" also routes here

# .env-style files to search, relative to a repo root, in priority order. The live
# OPENAI_API_KEY commonly lives in frontend-nextjs/.env.local (git-ignored), so it
# is searched in addition to the backend .env.
_ENV_RELPATHS = (".env", ".env.local", "frontend-nextjs/.env.local")


def _main_worktree_root(repo_root: Path) -> Path | None:
    """The main checkout root (parent of the shared .git), or None if unavailable.

    .env / .env.local are git-ignored, so a worktree checkout may not contain them
    even though the main checkout does. `git --git-common-dir` points at
    <main>/.git, whose parent is the main worktree root.
    """
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            # DQ-54: the answer here locates the .env holding the API key.
            cwd=repo_root, env=git_env(), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if common.returncode == 0 and common.stdout.strip():
        return Path(common.stdout.strip()).parent
    return None


def candidate_env_paths(repo_root: Path) -> list[Path]:
    """.env-style files to try, across this checkout and the main worktree root."""
    roots = [repo_root]
    main_root = _main_worktree_root(repo_root)
    if main_root is not None and main_root != repo_root:
        roots.append(main_root)
    paths: list[Path] = []
    for root in roots:
        for rel in _ENV_RELPATHS:
            p = root / rel
            if p not in paths:
                paths.append(p)
    return paths


def load_api_key(repo_root: Path) -> str:
    """Return the OpenAI key from the environment, else a repo .env-style file.

    Exits with a clear message if none is found - never guesses. NOTE: an exported
    OPENAI_API_KEY always wins, so a stale shell export shadows the .env files.
    """
    key = os.environ.get("OPENAI_API_KEY")
    if key and key.strip():
        return key.strip()
    for env_path in candidate_env_paths(repo_root):
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, _, value = line.partition("=")
            if name.strip() == "OPENAI_API_KEY":
                val = value.strip().strip('"').strip("'")
                if val:  # skip an empty `OPENAI_API_KEY=` and keep searching
                    return val
    sys.exit(
        "No OPENAI_API_KEY found in the environment or a repo .env / .env.local.\n"
        "Set it: export OPENAI_API_KEY=sk-...  (a stale exported key will shadow .env)"
    )


def force_utf8_output() -> None:
    """Make stdout/stderr UTF-8 so model text with Unicode can't crash the console
    (Windows cp1252 raises UnicodeEncodeError otherwise)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def chat(messages: list[dict], model: str, api_key: str, json_mode: bool = False) -> str:
    """Call the OpenAI Chat Completions API and return the message text.

    gpt-5.6 reasoning models only accept the default temperature, so it is omitted.
    Exits with a clear message on any API/import error.
    """
    try:
        import openai
    except ImportError:
        sys.exit("The `openai` package is not installed. pip install openai")

    # BOUNDED, and it says so while it waits.
    #
    # This call is reached from .githooks/pre-push step 7, which BLOCKS the push.
    # It previously ran with the client's defaults - a 600 second timeout and two
    # retries - so a revoked key, a network stall and a slow reasoning response
    # were indistinguishable from one another and from a hang, for up to half an
    # hour, with no output at all. Observed 2026-08-13: a push sat on the single
    # line "reviewing a652c6b8..HEAD" and printed nothing further.
    #
    # A blocking gate that cannot say what it is doing gets bypassed with
    # --no-verify, and that is how a gate stops existing. The progress line goes
    # to stderr so it cannot be mistaken for the tool's JSON on stdout.
    timeout_s = float(os.getenv("SOL_TIMEOUT_SECONDS", "180"))
    print(f"  calling {model} (timeout {timeout_s:.0f}s, no retries)...",
          file=sys.stderr, flush=True)

    client = openai.OpenAI(api_key=api_key, timeout=timeout_s, max_retries=0)
    kwargs: dict = {"model": model, "messages": messages}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # network / auth / model-name / timeout
        name = type(exc).__name__
        hint = ""
        if "Authentication" in name or "PermissionDenied" in name:
            hint = ("\nThe key was rejected. Check OPENAI_API_KEY in the repo-root "
                    ".env or frontend-nextjs/.env.local - a rotated or revoked key "
                    "lands here.")
        elif "Timeout" in name or "APIConnection" in name:
            hint = (f"\nNo response within {timeout_s:.0f}s. Raise it with "
                    f"SOL_TIMEOUT_SECONDS=600, or check network access to the API.")
        sys.exit(f"OpenAI API call failed ({name}): {exc}{hint}")
    return (response.choices[0].message.content or "").strip()
