"""The scratchpad rule-write hook, driven the way Claude Code drives it (JSON on stdin).

The block case is the real line from write_batch1.py (2026-10-29), the script whose 65
rows were rolled back on 2026-11-03.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "scratchpad-rule-write-guard.py"

BATCH1 = ("import psycopg2\ncur = None\n"
          "cur.execute('update dcp_setback_controls set source_text=%s where id=%s and is_current',"
          "(r['new_quote'],int(r['id'])))\n")
READ_ONLY = "cur.execute(\"select count(*) from dcp_setback_controls where is_current\")\n"


def _run(command: str, cwd: Path) -> subprocess.CompletedProcess:
    payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True,
                          capture_output=True, timeout=30,
                          env={**__import__("os").environ, "CLAUDE_PROJECT_DIR": str(ROOT)})


@pytest.fixture()
def scratch(tmp_path):
    return tmp_path


def test_the_real_batch1_writer_from_a_scratchpad_is_blocked(scratch):
    f = scratch / "write_batch1.py"
    f.write_text(BATCH1, encoding="utf-8")
    r = _run(f"python {f}", scratch)
    assert r.returncode == 2 and "not a tracked repo script" in r.stderr


def test_a_read_only_scratchpad_script_is_allowed(scratch):
    f = scratch / "measure.py"
    f.write_text(READ_ONLY, encoding="utf-8")
    assert _run(f'python "{f}" --dry', scratch).returncode == 0


def test_inline_heredoc_write_is_blocked(scratch):
    cmd = "python - <<'EOF'\ncur.execute(\"UPDATE regulatory_provisions SET council_quote='x' WHERE id=1\")\nEOF"
    assert _run(cmd, scratch).returncode == 2


def test_insert_and_delete_and_registry_are_caught(scratch):
    for sql in ("INSERT INTO dcp_setback_controls (lga) VALUES ('x')",
                "delete from public.regulatory_provisions where id=1",
                "update dcp_chapter_registry set page_start=146"):
        f = scratch / "w.py"
        f.write_text(f'cur.execute("{sql}")\n', encoding="utf-8")
        assert _run(f"python3 {f}", scratch).returncode == 2, sql


def test_a_tracked_pipeline_script_is_allowed():
    assert _run("python scripts/dcp_extract_changed.py --review --council x", ROOT).returncode == 0


def test_grepping_for_the_sql_while_running_unrelated_python_is_allowed(scratch):
    f = scratch / "measure.py"
    f.write_text(READ_ONLY, encoding="utf-8")
    cmd = f"grep -n 'UPDATE dcp_setback_controls' scripts/*.py; python {f}"
    assert _run(cmd, scratch).returncode == 0


def test_the_override_is_allowed_and_logged(scratch):
    f = scratch / "restore.py"
    f.write_text(BATCH1, encoding="utf-8")
    log = ROOT / ".claude" / ".rule-write-overrides.log"
    before = log.read_text(encoding="utf-8") if log.exists() else ""
    try:
        r = _run(f'RULE_WRITE_OK="test restore" python {f}', scratch)
        assert r.returncode == 0
        assert "test restore" in log.read_text(encoding="utf-8")[len(before):]
    finally:
        if before:
            log.write_text(before, encoding="utf-8")
        elif log.exists():
            log.unlink()


def test_git_bash_drive_paths_resolve(scratch):
    f = scratch / "write_batch1.py"
    f.write_text(BATCH1, encoding="utf-8")
    posix = "/" + str(f)[0].lower() + str(f)[2:].replace("\\", "/")
    assert _run(f"python {posix}", scratch).returncode == 2


def test_other_tools_are_ignored():
    payload = {"tool_name": "Edit", "tool_input": {"file_path": "x"}}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True,
                       capture_output=True, timeout=30)
    assert r.returncode == 0


def test_a_writer_second_in_a_chain_is_blocked(scratch):
    """Sol review 2026-11-03: only the first python of a chain was read."""
    ok = scratch / "read.py"
    ok.write_text(READ_ONLY, encoding="utf-8")
    bad = scratch / "write_batch1.py"
    bad.write_text(BATCH1, encoding="utf-8")
    for sep in ("; ", " && ", "\n", " || "):
        assert _run(f"python {ok}{sep}python {bad}", scratch).returncode == 2, repr(sep)
