"""manual_intake.py takes in council PDFs a person downloaded by hand (DQ-153).

The rules that matter: a dry run is the default, the hash handed to the intake is
the file's real sha256, a file that matches no blocked chapter is never loaded,
and the DQ-153 probe counts both ways a block shows (old check date, blocked).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import manual_intake  # noqa: E402


def _row(council: str, key: str) -> dict:
    return {"council": council, "chapter_key": key, "chapter_label": key,
            "council_url": "https://example.test/x.pdf", "url_last_checked": None}


def test_file_name_is_council_then_chapter():
    assert manual_intake.file_name_for("waverley", "waverley-dcp-2022") == "waverley__waverley-dcp-2022.pdf"


def test_sha256_is_the_files_real_hash(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF-1.7 hello")
    assert manual_intake.sha256_of(f) == hashlib.sha256(b"%PDF-1.7 hello").hexdigest()


def test_dry_run_is_the_default_and_apply_removes_it(tmp_path):
    pdf = tmp_path / "w.pdf"
    dry = manual_intake.intake_command("waverley", "k", pdf, "ab", apply=False)
    live = manual_intake.intake_command("waverley", "k", pdf, "ab", apply=True)
    assert "--dry-run" in dry
    assert "--dry-run" not in live
    for cmd in (dry, live):
        assert cmd[cmd.index("--council") + 1] == "waverley"
        assert cmd[cmd.index("--chapter-key") + 1] == "k"
        assert cmd[cmd.index("--expect-sha256") + 1] == "ab"
        assert cmd[cmd.index("--from-file") + 1] == str(pdf)


def test_folder_matching_loads_only_blocked_chapters(tmp_path):
    rows = [_row("waverley", "w1"), _row("wollongong", "a1"), _row("wollongong", "b1")]
    (tmp_path / "waverley__w1.pdf").write_bytes(b"x")
    (tmp_path / "blacktown__not-blocked.pdf").write_bytes(b"x")  # right shape, not blocked
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "wollongong__a1.PDF").write_bytes(b"x")  # wrong case of extension: name will not match
    matched, unknown, missing = manual_intake.match_folder(rows, tmp_path)
    assert [(r["council"], r["chapter_key"]) for r, _ in matched] == [("waverley", "w1")]
    assert {p.name for p in unknown} == {"blacktown__not-blocked.pdf", "wollongong__a1.PDF"}
    assert {(r["council"], r["chapter_key"]) for r in missing} == {("wollongong", "a1"), ("wollongong", "b1")}


def test_same_chapter_key_in_two_councils_is_not_confused(tmp_path):
    rows = [_row("a", "intro"), _row("b", "intro")]
    (tmp_path / "a__intro.pdf").write_bytes(b"x")
    matched, _unknown, missing = manual_intake.match_folder(rows, tmp_path)
    assert [r["council"] for r, _ in matched] == ["a"]
    assert [r["council"] for r in missing] == ["b"]


def test_probe_counts_both_signals_and_only_serving_chapters():
    import dq_probe_live

    _headline, sql, params, _means = dq_probe_live.PROBES["DQ-153"]
    flat = " ".join(sql.split())
    assert params == ()
    assert "interval '14 days'" in flat
    assert "url_last_checked IS NULL" in flat  # never checked counts as stale
    assert "= 'waf_blocked'" in flat
    assert "ORDER BY x.checked_at DESC" in flat  # the LATEST result, not any past one
    assert "p.is_current AND p.v2_is_actionable" in flat  # only chapters that serve rules
    assert "r.is_active" in flat


def test_list_sql_and_probe_use_the_same_test():
    """The list a person works from must be the set the red number counts."""
    import dq_probe_live

    probe = " ".join(dq_probe_live.PROBES["DQ-153"][1].split())
    listing = " ".join(manual_intake.BLOCKED_CHAPTERS_SQL.split())
    for piece in ("p.is_current AND p.v2_is_actionable", "= 'waf_blocked'",
                  "ORDER BY x.checked_at DESC, x.id DESC LIMIT 1"):
        assert piece in probe and piece in listing
    assert re.search(r"%s \* interval '1 day'", listing)


def test_print_list_says_nothing_to_do_when_clear(capsys):
    manual_intake.print_list([])
    assert "Nothing to take in" in capsys.readouterr().out
