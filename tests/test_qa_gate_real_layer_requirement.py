"""Tests for check_real_layer_test_exists (Layer 9.5, scripts/qa_gate.py).

Session origin (2026-09-04): every other layer in qa_gate.py checks that a
CLAIM was written down correctly; none of them independently verify that a
database or HTTP call was actually exercised for the specific file that
changed. This layer closes that -- generically, for any future file, not
one hand-picked file wired into CI by name (which is what the rest of this
session did for services/drawdown_verify.py, and which does not protect the
next file with the same class of bug).

The first version of this check had a real bug, found by forcing it to fail
against the REAL file that motivated it (not a synthetic example): it only
inspected each changed function's OWN body text, and
services/drawdown_verify.py's submit_drawdown_verify delegates to a local
helper (_insert_audit) that is the one which actually touches the database
-- the function itself never does. TestAgainstTheRealFileThatMotivatedThis
reproduces that exact scenario so it can never regress silently.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from qa_gate import check_real_layer_test_exists  # noqa: E402

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")


class TestSyntheticCases:
    """Fast, isolated cases using files written to tmp_path -- no dependency
    on any real file in this repo, so these can never be broken by someone
    else editing services/drawdown_verify.py later."""

    def _write(self, tmp_path, rel_path: str, content: str) -> None:
        full = tmp_path / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    def test_direct_db_call_with_no_test_file_is_flagged(self, tmp_path):
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "def save(x):\n"
            "    conn = psycopg2.connect('...')\n"
            "    cur = conn.cursor()\n"
            "    cur.execute('INSERT INTO widgets VALUES (%s)', (x,))\n"
        ))
        errors = check_real_layer_test_exists(
            {}, ["services/widget.py"], str(tmp_path), {"services/widget.py": {2, 3, 4, 5}}
        )
        assert len(errors) == 1
        assert "services/widget.py" in errors[0]

    def test_direct_db_call_with_matching_real_layer_test_is_clean(self, tmp_path):
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "def save(x):\n"
            "    conn = psycopg2.connect('...')\n"
            "    cur = conn.cursor()\n"
            "    cur.execute('INSERT INTO widgets VALUES (%s)', (x,))\n"
        ))
        self._write(tmp_path, "tests/test_widget_real_db.py", (
            "import pytest\n"
            "pytestmark = pytest.mark.database\n"
            "def test_save_writes_a_real_row():\n"
            "    pass\n"
        ))
        errors = check_real_layer_test_exists(
            {}, ["services/widget.py"], str(tmp_path), {"services/widget.py": {2, 3, 4, 5}}
        )
        assert errors == []

    def test_one_level_delegation_to_a_local_helper_is_still_caught(self, tmp_path):
        """The exact shape that broke the first version of this check:
        the CHANGED function calls a local helper, and the helper -- not
        the changed function itself -- is the one that touches the DB."""
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "def _save_helper(x):\n"
            "    conn = psycopg2.connect('...')\n"
            "    cur = conn.cursor()\n"
            "    cur.execute('INSERT INTO widgets VALUES (%s)', (x,))\n"
            "\n"
            "def public_entry_point(x):\n"
            "    validate(x)\n"
            "    return _save_helper(x)\n"
        ))
        # Only public_entry_point's lines changed -- _save_helper is untouched,
        # pre-existing code. The finding must still fire, because the CHANGED
        # function's behaviour now depends on DB-touching code either way.
        errors = check_real_layer_test_exists(
            {}, ["services/widget.py"], str(tmp_path), {"services/widget.py": {7, 8, 9}}
        )
        assert len(errors) == 1

    def test_no_db_or_http_call_anywhere_is_never_flagged(self, tmp_path):
        self._write(tmp_path, "services/widget.py", (
            "def add(a, b):\n"
            "    return a + b\n"
        ))
        errors = check_real_layer_test_exists(
            {}, ["services/widget.py"], str(tmp_path), {"services/widget.py": {1, 2}}
        )
        assert errors == []

    def test_explicit_exemption_suppresses_the_finding(self, tmp_path):
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "def save(x):\n"
            "    conn = psycopg2.connect('...')\n"
            "    conn.cursor().execute('INSERT INTO widgets VALUES (%s)', (x,))\n"
        ))
        report = {"real_layer_exempt": {"services/widget.py": "no real test possible, external sandbox only"}}
        errors = check_real_layer_test_exists(
            report, ["services/widget.py"], str(tmp_path), {"services/widget.py": {2, 3, 4}}
        )
        assert errors == []

    def test_empty_or_non_string_exemption_is_rejected(self, tmp_path):
        """Sol cross-review (2026-09-04): membership in real_layer_exempt was
        being treated as sufficient on its own -- an empty string or `true`
        (no actual reason written) must NOT suppress the finding."""
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "def save(x):\n"
            "    conn = psycopg2.connect('...')\n"
            "    conn.cursor().execute('INSERT INTO widgets VALUES (%s)', (x,))\n"
        ))
        changed = {"services/widget.py": {2, 3, 4}}
        for bad_value in ("", "   ", True, None):
            report = {"real_layer_exempt": {"services/widget.py": bad_value}}
            errors = check_real_layer_test_exists(
                report, ["services/widget.py"], str(tmp_path), changed
            )
            assert len(errors) == 1, f"bad_value={bad_value!r} was wrongly accepted as an exemption"

    def test_duplicate_function_names_in_one_file_do_not_hide_a_db_touching_sibling(self, tmp_path):
        """Sol cross-review (2026-09-04): {name: fn} silently dropped
        earlier same-named definitions -- two functions named `helper` in
        different scopes, where the CHANGED caller resolves (by name) to
        whichever one this dict happened to keep last. Must be treated as
        touching if ANY same-named definition touches directly."""
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "class A:\n"
            "    def helper(self):\n"
            "        return 1  # unrelated, no DB\n"
            "\n"
            "class B:\n"
            "    def helper(self):\n"
            "        psycopg2.connect('...').cursor().execute('SELECT 1')\n"
            "\n"
            "def public_entry_point():\n"
            "    return helper()\n"
        ))
        # Only public_entry_point changed. Ambiguous which `helper` it
        # actually calls at runtime -- must err toward flagging.
        errors = check_real_layer_test_exists(
            {}, ["services/widget.py"], str(tmp_path), {"services/widget.py": {10, 11}}
        )
        assert len(errors) == 1

    def test_unchanged_lines_in_a_db_touching_function_are_not_flagged(self, tmp_path):
        """A PR touching an unrelated part of the file, not the DB-touching
        function itself, should not be forced to add a test for code it
        never went near."""
        self._write(tmp_path, "services/widget.py", (
            "import psycopg2\n"
            "def save(x):\n"
            "    conn = psycopg2.connect('...')\n"
            "    conn.cursor().execute('INSERT INTO widgets VALUES (%s)', (x,))\n"
            "\n"
            "def unrelated(y):\n"
            "    return y * 2\n"
        ))
        errors = check_real_layer_test_exists(
            {}, ["services/widget.py"], str(tmp_path), {"services/widget.py": {6, 7}}
        )
        assert errors == []

    def test_test_files_themselves_are_never_the_target(self, tmp_path):
        self._write(tmp_path, "tests/test_something.py", (
            "import psycopg2\n"
            "def helper():\n"
            "    psycopg2.connect('...').cursor().execute('SELECT 1')\n"
        ))
        errors = check_real_layer_test_exists(
            {}, ["tests/test_something.py"], str(tmp_path), {"tests/test_something.py": {1, 2, 3}}
        )
        assert errors == []

    def test_files_outside_services_and_scripts_are_not_scanned(self, tmp_path):
        self._write(tmp_path, "src/models/widget.py", (
            "import psycopg2\n"
            "def save(x):\n"
            "    psycopg2.connect('...').cursor().execute('INSERT INTO w VALUES (%s)', (x,))\n"
        ))
        errors = check_real_layer_test_exists(
            {}, ["src/models/widget.py"], str(tmp_path), {"src/models/widget.py": {1, 2, 3}}
        )
        assert errors == []


class TestAgainstTheRealFileThatMotivatedThis:
    """Not a synthetic example -- the actual file and function
    (services/drawdown_verify.py::submit_drawdown_verify) whose delegation
    to a local helper broke the first version of this check. Renames the
    two real test files out of the way, confirms the check fires, restores
    them, confirms it goes clean again -- reproducing the exact force-fail
    proof run manually in session before this was written up as a test."""

    def test_real_file_is_flagged_when_its_real_tests_are_hidden_then_clean_when_restored(self):
        real_test_1 = os.path.join(REPO_ROOT, "tests", "test_drawdown_verify_real_db.py")
        real_test_2 = os.path.join(REPO_ROOT, "tests", "test_drawdown_verify_audit_failclosed.py")
        hidden_1 = real_test_1 + ".hidden_for_test"
        hidden_2 = real_test_2 + ".hidden_for_test"

        # submit_drawdown_verify's real line range as of this session -- see
        # services/drawdown_verify.py:489 (approximately; a few lines of
        # slack either side keeps this from breaking on trivial reformatting).
        changed = {"services/drawdown_verify.py": set(range(495, 530))}

        os.rename(real_test_1, hidden_1)
        os.rename(real_test_2, hidden_2)
        try:
            errors = check_real_layer_test_exists(
                {}, ["services/drawdown_verify.py"], REPO_ROOT, changed
            )
            assert len(errors) == 1, (
                "Expected exactly 1 finding with the real test files hidden -- "
                f"got {errors}"
            )
            assert "services/drawdown_verify.py" in errors[0]
        finally:
            os.rename(hidden_1, real_test_1)
            os.rename(hidden_2, real_test_2)

        # Restored: must be clean again.
        errors_after = check_real_layer_test_exists(
            {}, ["services/drawdown_verify.py"], REPO_ROOT, changed
        )
        assert errors_after == []
