"""A finding adjudicated once must not block the next push forever.

The gate blocked one branch four times running on 2026-08-10. It kept no record
of what it had already raised, so a finding that had been read, verified and
dealt with could come back on the next run and block again, indistinguishable
from something new.

These tests cover the record itself. The deliberate coarseness of the key
(file + category, no line, no summary text) is the design decision most likely
to be quietly "improved" later into something that matches nothing, so it is
pinned here with the reason.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_SRC = ROOT / "scripts" / "cross_review.py"

pytestmark = pytest.mark.skipif(not _SRC.exists(), reason="cross_review.py not present")


def _mod():
    spec = importlib.util.spec_from_file_location("cross_review_under_test", _SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def cr():
    return _mod()


def test_the_same_defect_reworded_still_matches(cr):
    """The whole point. Sol is non-deterministic prose.

    The identical defect comes back described differently on the next run. If
    the key included the summary text it would match almost nothing and the
    record would be decorative.
    """
    a = {"file": "services/flood.py", "category": "null-guard", "line": 40,
         "summary": "Unguarded null in the flood signal path"}
    b = {"file": "services/flood.py", "category": "null-guard", "line": 118,
         "summary": "A missing overlay yields None and is rendered as a clean negative"}
    assert cr.finding_key(a) == cr.finding_key(b)


def test_a_different_file_or_category_is_a_different_finding(cr):
    base = {"file": "services/flood.py", "category": "null-guard"}
    assert cr.finding_key(base) != cr.finding_key({**base, "file": "services/solar.py"})
    assert cr.finding_key(base) != cr.finding_key({**base, "category": "silent-failure"})


def test_missing_fields_do_not_collapse_everything_into_one_key(cr):
    """A malformed finding must not become a key that matches other malformed
    ones and grants them all amnesty in one go."""
    assert cr.finding_key({}) == "?::?"
    assert cr.finding_key({"file": "a.py"}) != cr.finding_key({"file": "b.py"})


def test_an_absent_record_grants_no_amnesty(cr, tmp_path):
    assert cr.load_adjudicated(None) == set()
    assert cr.load_adjudicated(tmp_path / "nope.json") == set()


def test_a_corrupt_record_grants_no_amnesty(cr, tmp_path, capsys):
    """Fail CLOSED. A truncated or hand-edited file must not silently mean
    'everything has already been adjudicated' — that would disable the gate
    while leaving it looking enabled."""
    p = tmp_path / "broken.json"
    p.write_text("{not json", encoding="utf-8")
    assert cr.load_adjudicated(p) == set()
    assert "unreadable" in capsys.readouterr().out


def test_a_record_round_trips(cr, tmp_path):
    p = tmp_path / "rec.json"
    keys = ["a.py::null-guard", "b.py::db-filter"]
    p.write_text(json.dumps({"keys": keys}), encoding="utf-8")
    assert cr.load_adjudicated(p) == set(keys)


def test_only_fresh_findings_gate(cr, tmp_path):
    """The split that makes the loop terminate.

    Two findings, one already adjudicated. Only the new one may gate; the
    repeat is still reported, because being repeated is not evidence that it is
    fixed — but it must not block a second time on its own.
    """
    known = {"services/flood.py::null-guard"}
    findings = [
        {"file": "services/flood.py", "category": "null-guard", "severity": "high"},
        {"file": "services/solar.py", "category": "silent-failure", "severity": "high"},
    ]
    fresh = [f for f in findings if cr.finding_key(f) not in known]
    repeats = [f for f in findings if cr.finding_key(f) in known]

    assert [f["file"] for f in fresh] == ["services/solar.py"]
    assert [f["file"] for f in repeats] == ["services/flood.py"]

    # And once the new one is adjudicated too, nothing is left to gate.
    known |= {cr.finding_key(f) for f in findings}
    assert [f for f in findings if cr.finding_key(f) not in known] == []
