"""Only a CHANGED verdict is written, and an unknown one is refused, never stored."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dcp_citation_status as S  # noqa: E402


def test_only_changed_verdicts_are_written():
    verdicts = {1: "proven", 2: "not_proven", 3: "proven"}
    current = {1: "proven", 2: None, 3: "not_proven"}
    assert S.plan_updates(verdicts, current) == [(2, "not_proven"), (3, "proven")]


def test_nothing_to_write_when_nothing_changed():
    assert S.plan_updates({1: "unjudged"}, {1: "unjudged"}) == []


def test_an_unknown_verdict_is_refused_not_stored():
    with pytest.raises(ValueError):
        S.plan_updates({1: "maybe"}, {})
