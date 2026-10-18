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


#: Used when OpenAI has no credits (user 2026-10-18): another model family, through OpenRouter.
FALLBACK_MODEL = "deepseek/deepseek-v3.2"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_NO_CREDIT = ("insufficient_quota", "credit_balance_exhausted")
#: The model that actually answered the last chat() call (differs from the one asked for after a fallback).
LAST_MODEL: str | None = None


def env_value(name: str, repo_root: Path | None = None) -> str | None:
    """`name` from the environment, else from the repo .env files (same search as load_api_key)."""
    val = (os.environ.get(name) or "").strip()
    if val:
        return val
    root = repo_root or Path(__file__).resolve().parents[1]
    for env_path in candidate_env_paths(root):
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            k, _, v = raw.strip().partition("=")
            if k.strip() == name and v.strip().strip('"').strip("'"):
                return v.strip().strip('"').strip("'")
    return None


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
    raw = os.getenv("SOL_TIMEOUT_SECONDS", "180")
    try:
        timeout_s = float(raw)
    except (TypeError, ValueError):
        sys.exit(f"SOL_TIMEOUT_SECONDS is not a number: {raw!r}")
    # Reject non-positive and non-finite before handing it to the client, which
    # would otherwise accept nan or -1 with undefined semantics.
    if not (timeout_s > 0) or timeout_s != timeout_s or timeout_s == float("inf"):
        sys.exit(f"SOL_TIMEOUT_SECONDS must be a positive finite number: {raw!r}")
    print(f"  calling {model} (timeout {timeout_s:.0f}s, no retries)...",
          file=sys.stderr, flush=True)

    routed = "/" in model   # an OpenRouter model id ("deepseek/deepseek-v3.2")
    if routed:
        api_key = env_value("OPENROUTER_API_KEY") or sys.exit("OPENROUTER_API_KEY is not set for model " + model)
    client = openai.OpenAI(api_key=api_key, timeout=timeout_s, max_retries=0,
                           **({"base_url": OPENROUTER_BASE_URL} if routed else {}))
    kwargs: dict = {"model": model, "messages": messages}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as exc:  # network / auth / model-name / timeout
        if not routed and any(m in str(exc) for m in _NO_CREDIT) and env_value("OPENROUTER_API_KEY"):
            # Said loudly: the review is still from another model family, but not the one named.
            print(f"  OpenAI has no credits -- falling back to {FALLBACK_MODEL} via OpenRouter.",
                  file=sys.stderr, flush=True)
            return chat(messages, FALLBACK_MODEL, api_key, json_mode)
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
    global LAST_MODEL
    LAST_MODEL = model
    return (response.choices[0].message.content or "").strip()
