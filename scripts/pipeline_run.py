"""Tag a database connection with the pipeline run that is writing (migration 121).

prior-art-checked: no existing run tag; verifyops_record.py records a run in its own table,
not on the connection, so the rule tables cannot see it.

    import pipeline_run
    run_id = pipeline_run.tag(conn, "dcp_extract_changed")

Every change to a protected rule column is then logged in rule_write_log with this id, and
in rule_write_guard mode 'enforce' an untagged change is refused.
"""
from __future__ import annotations

import os
import subprocess
import uuid
from pathlib import Path


def _git_sha() -> str:
    """Railway sets RAILWAY_GIT_COMMIT_SHA; locally ask git; 'unknown' rather than fail."""
    sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA")
    if sha:
        return sha[:12]
    try:
        from qa_report_path import git_env   # a hook's GIT_DIR would override cwd
        out = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True,
                             text=True, timeout=10, cwd=Path(__file__).resolve().parent,
                             env=git_env())
        return out.stdout.strip() or "unknown"
    except (OSError, subprocess.SubprocessError, ImportError):
        return "unknown"


def run_id(script: str) -> str:
    """'<script>@<git sha>:<uuid>' -- names the code and the one run."""
    if not script or not script.strip():
        raise ValueError("pipeline_run.run_id needs the script name")
    return f"{script.strip()}@{_git_sha()}:{uuid.uuid4().hex[:12]}"


ENV = "PIPELINE_RUN_ID"


def tag(conn, script: str) -> str:
    """Set app.pipeline_run for the whole session; returns the id. Survives commits.

    One id per run: the first call stores it in PIPELINE_RUN_ID, so a reconnect in the same
    process and a child process it starts (dcp_commit_approved -> council_quote.py) log under
    the same run. Measured 2026-11-03: the Supabase pooler drops startup options (PGOPTIONS),
    so each connection must set it itself.
    """
    rid = os.environ.get(ENV) or run_id(script)
    os.environ[ENV] = rid
    try:
        import psycopg2.extensions as _ext
        real = isinstance(conn, _ext.connection)
    except ImportError:
        real = False
    if not real:
        return rid                        # a test double is not a database; nothing to tag
    idle = conn.get_transaction_status() == _ext.TRANSACTION_STATUS_IDLE
    cur = conn.cursor()
    cur.execute("SELECT set_config('app.pipeline_run', %s, false)", (rid,))
    cur.close()
    if idle and not conn.autocommit:
        # End the transaction this SELECT opened, or a caller's next `conn.autocommit = ...`
        # raises (psycopg2 refuses set_session inside a transaction). The setting is
        # session-level, so it survives the commit. Nothing of the caller's is pending.
        conn.commit()
    return rid
