#!/usr/bin/env python3
"""Read-only connection for the DQ live probes.

prior-art-checked: reuse not viable because the existing .env resolvers are
private to their scripts. scripts/sol_common.py and
scripts/validate_schema_contract.py each inline this same git-common-dir lookup
for their OWN purpose (an API key, a schema catalog) and neither exposes a
connection; services/ connects via its own pools with write access. Sweeps
2026-08-12 on origin/main fe7859b6: no shared read-only DB helper exists in
scripts/.

Two things it guarantees, both learned the hard way:

1. READ-ONLY. ``set_session(readonly=True)`` plus a 30s statement timeout. These
   probes measure; repairs are a separate, authorised act.
2. The RIGHT .env. A git worktree carries none of its own, so a naive
   ``load_dotenv('.env')`` silently falls through to localhost defaults and
   fails with a confusing role error -- which happened here once before this
   helper existed. The main checkout is resolved via git, with ``GIT_*``
   scrubbed so a hook's GIT_DIR cannot redirect it (DQ-54).
"""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qa_report_path import git_env  # noqa: E402  (DQ-54: one shared scrub, never a local copy)

_TIMEOUT_MS = 30_000


def main_checkout() -> Path:
    """The repo root that actually holds .env, even from inside a worktree."""
    here = Path(__file__).resolve().parents[1]
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=here, capture_output=True, text=True,
            env=git_env(), timeout=10,
        ).stdout.strip()
        if common:
            return Path(common).parent
    except (OSError, subprocess.SubprocessError):
        pass
    return here


@contextlib.contextmanager
def session():
    """Read-only connection as a context manager -- closes on every path.

    connect() hands the caller a live connection and trusts them to close it.
    Every probe does, but "the caller remembers" is the assumption that leaks
    connections against a pooled production database. Prefer this.
    """
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def connect():
    """A read-only psycopg2 connection, or raise with an actionable message."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        load_dotenv = None
    if load_dotenv:
        load_dotenv(main_checkout() / ".env")

    url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError(
            "No DATABASE_URL. These probes measure the live database; without it "
            "the answer is UNKNOWN, which is not the same as clean."
        )
    import psycopg2

    conn = psycopg2.connect(url, connect_timeout=20)
    conn.set_session(readonly=True)
    cur = conn.cursor()
    cur.execute(f"SET statement_timeout = {_TIMEOUT_MS}")
    return conn
