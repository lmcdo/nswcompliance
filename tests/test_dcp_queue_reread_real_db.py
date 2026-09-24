"""Queueing a chapter for re-read, against the real registry -- dry run only.

The script must resolve a name to exactly one active registry row or write
nothing. Checked against the live registry without --apply, so no row changes.

Opt-in, like every real-DB test here:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dcp_queue_reread_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1",
                       reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL"),
]


def run(monkeypatch, *argv):
    import dcp_queue_reread as q
    monkeypatch.setattr(sys, "argv", ["dcp_queue_reread.py", *argv])
    return q.main()


def test_every_named_top_chapter_resolves_to_one_active_row(monkeypatch, capsys):
    assert run(monkeypatch, "--dq111-top", "11") == 0          # dry run: nothing written
    out = capsys.readouterr().out
    assert "DRY RUN" in out and out.count("(id ") == 11


def test_an_unknown_chapter_writes_nothing(monkeypatch, capsys):
    assert run(monkeypatch, "--chapter", "woollahra/no-such-chapter", "--apply") == 2
    assert "matches 0 active registry rows" in capsys.readouterr().out
