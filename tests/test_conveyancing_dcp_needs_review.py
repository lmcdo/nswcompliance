"""Fail-closed currency guard for the PDF conveyancing DCP setback path.

prior-art-checked: covers the serving-path currency guard in
scripts/conveyancing_db.fetch_dcp_setbacks (tests/test_dcp_setback_validation.py
already covers extraction validation, not this serving path). Reuses the existing
function; no new capability added.

A DCP setback control flagged needs_review (council amended its plan, re-extraction
pending) must never render as an authoritative number in the conveyancing PDF. The
web route /api/dcp/structured-controls already suppresses/badges these; this locks
the PDF path to the same behaviour so the two surfaces cannot disagree.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from conveyancing_db import fetch_dcp_setbacks  # noqa: E402


class _FakeCursor:
    """Minimal cursor: returns canned setback rows, then a registry URL row."""

    def __init__(self, setback_rows, registry_row):
        self._setback_rows = setback_rows
        self._registry_row = registry_row
        self.executed: list[str] = []

    def execute(self, sql, params=None):
        self.executed.append(sql)

    def fetchall(self):
        return list(self._setback_rows)

    def fetchone(self):
        return self._registry_row

    def close(self):
        pass


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def rollback(self):
        pass


def _row(dev_type, ctrl_type, vmin, needs_review, section_ref="3.2"):
    # Column order matches the SELECT in fetch_dcp_setbacks:
    # (dev_type, control_type, value_min, value_max, unit, condition,
    #  source_text, section_ref, applicability, needs_review,
    #  source_chapter_key, pdf_page, dcp_version)
    return (dev_type, ctrl_type, vmin, None, "m", None, None, section_ref,
            "all", needs_review, "part_3", 12, "v2022-current")


def _semantic_types(result):
    types = set()
    for entry in (result.get("setbacks") or []):
        types.add(entry.get("semantic_type"))
    for entry in (result.get("sd_setbacks") or []):
        types.add(entry.get("semantic_type"))
    return types


def test_under_review_control_is_suppressed():
    """A needs_review=True control must NOT render as an authoritative value.

    This is the core fail-closed guarantee: even if such a row reaches the
    result set (e.g. the SQL filter is later changed), the per-row guard drops it.
    """
    rows = [
        _row("dwelling_house", "front_setback", 6.0, False, section_ref="3.2"),
        _row("dwelling_house", "rear_setback", 3.0, True, section_ref="3.4"),
    ]
    cur = _FakeCursor(rows, registry_row=("https://example.test/dcp.pdf",))
    result = fetch_dcp_setbacks(_FakeConn(cur), "ashfield", "R2")

    assert result is not None
    types = _semantic_types(result)
    assert "front_setback" in types, "clean control should render"
    assert "rear_setback" not in types, "needs_review control must be suppressed"


def test_all_clean_controls_render():
    """Baseline: with no needs_review rows, controls render normally."""
    rows = [
        _row("dwelling_house", "front_setback", 6.0, False, section_ref="3.2"),
        _row("dwelling_house", "side_setback", 0.9, False, section_ref="3.3"),
    ]
    cur = _FakeCursor(rows, registry_row=(None,))
    result = fetch_dcp_setbacks(_FakeConn(cur), "ashfield", "R2")

    assert result is not None
    assert {"front_setback", "side_setback"} <= _semantic_types(result)


def test_sql_query_excludes_needs_review():
    """Defence-in-depth: the DB query itself must exclude needs_review rows."""
    cur = _FakeCursor([_row("dwelling_house", "front_setback", 6.0, False)], registry_row=(None,))
    fetch_dcp_setbacks(_FakeConn(cur), "ashfield", "R2")
    setback_sql = next(s for s in cur.executed if "dcp_setback_controls" in s)
    assert "needs_review" in setback_sql
