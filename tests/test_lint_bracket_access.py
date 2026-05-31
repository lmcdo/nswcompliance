"""Tests for scripts/lint_bracket_access.py — bracket access lint."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from lint_bracket_access import check_line


class TestBracketAccessLint:
    """Verify the lint catches unsafe bracket access and allows safe patterns."""

    def test_flags_bare_bracket_access(self):
        violations = check_line("test.py", 1, '    x = response["key"]')
        assert len(violations) == 1
        assert 'response["key"]' in violations[0]

    def test_allows_get(self):
        violations = check_line("test.py", 1, '    x = response.get("key")')
        assert len(violations) == 0

    def test_allows_assignment_target(self):
        violations = check_line("test.py", 1, '    result["key"] = 42')
        assert len(violations) == 0

    def test_allows_safe_var_row(self):
        violations = check_line("test.py", 1, '    x = row["column_name"]')
        assert len(violations) == 0

    def test_allows_safe_var_s(self):
        violations = check_line("test.py", 1, '    dt = s["development_type"]')
        assert len(violations) == 0

    def test_allows_safe_var_controls(self):
        violations = check_line("test.py", 1, '    x = controls["height"]')
        assert len(violations) == 0

    def test_allows_noqa_suppression(self):
        violations = check_line("test.py", 1, '    x = data["key"]  # noqa: bracket-access')
        assert len(violations) == 0

    def test_allows_dunder_access(self):
        violations = check_line("test.py", 1, '    x = obj["__class__"]')
        assert len(violations) == 0

    def test_skips_imports(self):
        violations = check_line("test.py", 1, 'from foo import bar["baz"]')
        assert len(violations) == 0

    def test_skips_comments(self):
        violations = check_line("test.py", 1, '    # data["key"] is dangerous')
        assert len(violations) == 0

    def test_flags_api_response(self):
        violations = check_line("test.py", 10, '    name = api_response["name"]')
        assert len(violations) == 1

    def test_flags_conditional_bracket(self):
        """The exact pattern that caused the lodgement_date bug."""
        line = '    x = d.get("a") or (str(d["b"])[:10] if d.get("b") else None)'
        violations = check_line("test.py", 5, line)
        assert len(violations) == 1
        assert 'd["b"]' in violations[0]

    def test_allows_equality_check(self):
        violations = check_line("test.py", 1, '    if data["key"] == "value":')
        # This IS bracket access — should flag it
        assert len(violations) == 1

    def test_allows_os_environ(self):
        violations = check_line("test.py", 1, '    key = os["API_KEY"]')
        assert len(violations) == 0

    def test_multiple_on_same_line(self):
        violations = check_line("test.py", 1, '    x = data["a"] + data["b"]')
        assert len(violations) == 2
