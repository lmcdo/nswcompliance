"""S1 fail-closed: the _unwrap_or_default helper preserves the failure signal,
and the failsoft lint blocks the silent-false-negative anti-pattern.

This is the railguard for the strata/overlay/controls class — a FAILED fetch must
never be re-stamped as a confident AUTHORITATIVE negative.
"""
import os
import subprocess
import sys
import textwrap

from services.intelligence_brief import _unwrap_or_default, DataField, ConfidenceLevel

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINT = os.path.join(REPO, "scripts", "lint_brief_failsoft.py")


# --- _unwrap_or_default: three-state semantics -----------------------------

def test_failed_fetch_is_flagged():
    df = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="x")
    value, failed = _unwrap_or_default(df, {"is_strata": False})
    assert failed is True
    assert value == {"is_strata": False}


def test_success_with_value_not_flagged():
    df = DataField(value={"is_strata": True}, confidence=ConfidenceLevel.AUTHORITATIVE, source="x")
    value, failed = _unwrap_or_default(df, {"is_strata": False})
    assert failed is False
    assert value == {"is_strata": True}


def test_genuine_empty_is_not_a_failure():
    # value=None but confidence is NOT not_available = "queried, genuinely empty".
    # This MUST NOT be flagged as failed (that's the legitimate AUTHORITATIVE-null case).
    df = DataField(value=None, confidence=ConfidenceLevel.AUTHORITATIVE, source="x")
    value, failed = _unwrap_or_default(df, {"is_strata": False})
    assert failed is False
    assert value == {"is_strata": False}


# --- the failsoft lint actually blocks the anti-pattern --------------------

def _run_lint(tmp_path, content: str):
    f = tmp_path / "sample.py"
    f.write_text(textwrap.dedent(content))
    p = subprocess.run([sys.executable, LINT, str(f)], capture_output=True, text=True)
    return p.returncode, p.stdout


def test_lint_blocks_unannotated_anti_pattern(tmp_path):
    code, out = _run_lint(tmp_path, """
        def f(foo_df):
            x = foo_df.value or {"a": 1}
            return x
    """)
    assert code == 1
    assert "fail-soft" in out.lower()


def test_lint_blocks_computed_default(tmp_path):
    code, _ = _run_lint(tmp_path, """
        def f(controls_df):
            c = controls_df.value or parse_controls([])
            return c
    """)
    assert code == 1


def test_lint_passes_with_helper(tmp_path):
    code, _ = _run_lint(tmp_path, """
        def f(foo_df):
            value, failed = _unwrap_or_default(foo_df, {"a": 1})
            return value
    """)
    assert code == 0


def test_lint_passes_with_ok_ack(tmp_path):
    code, _ = _run_lint(tmp_path, """
        def f(foo_df):
            x = foo_df.value or {"a": 1}  # failsoft-ok: degrades correctly
            return x
    """)
    assert code == 0


def test_lint_allows_scalar_default(tmp_path):
    # `or None` / `or 0` / `or False` are harmless scalar defaults, not the
    # container/computed masking shape — they should not trip the lint.
    code, _ = _run_lint(tmp_path, """
        def f(foo_df):
            n = foo_df.value or None
            return n
    """)
    assert code == 0
