"""The plant-restore harness must catch BOTH ways the open-coded version failed.

Every "falsifiability proven" claim in this campaign rests on plant -> confirm
red -> restore. Open-coded per session, it failed in both directions within two
days: once a plant silently no-opped on CRLF line endings (the run reported
success without having proved anything), and once a script died before its
restore line and left the planted defect in the working tree.

These tests are the enforcement's own enforcement. If `planted()` ever stops
raising on either failure, this file goes red.

Origin note, verified rather than assumed: `git config core.autocrlf` is `true`
on this repo, so a checked-out source file has CRLF line endings while an anchor
typed into a Python string literal has LF. The no-op is the default outcome of
the naive implementation, not an unlucky edge case -- `test_the_naive_pattern_is
_the_one_that_no_ops` pins exactly that.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE = Path(__file__).resolve().parents[1] / "scripts" / "falsifiability.py"


def _load():
    spec = importlib.util.spec_from_file_location("falsifiability_under_test", _MODULE)
    mod = importlib.util.module_from_spec(spec)
    # Registered BEFORE exec: @dataclass resolves annotations through
    # sys.modules[cls.__module__], which raises AttributeError for a module
    # loaded from a path and never registered.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fz():
    return _load()


CRLF_SOURCE = b"def f():\r\n    return round(az + 180.0, 1)\r\n\r\n\r\nX = 1\r\n"
LF_SOURCE = b"def f():\n    return round(az + 180.0, 1)\n\n\nX = 1\n"


@pytest.fixture
def crlf_file(tmp_path: Path) -> Path:
    p = tmp_path / "target_crlf.py"
    p.write_bytes(CRLF_SOURCE)
    return p


@pytest.fixture
def lf_file(tmp_path: Path) -> Path:
    p = tmp_path / "target_lf.py"
    p.write_bytes(LF_SOURCE)
    return p


# ── The happy path, stated as hashes ─────────────────────────────────────────


def test_plant_changes_the_file_and_restore_returns_the_exact_bytes(fz, crlf_file):
    before = fz.sha256_file(crlf_file)

    with fz.planted(crlf_file, "180.0", "185.0", label="drift") as info:
        during = fz.sha256_file(crlf_file)
        assert during != before, "RULE 1: the plant must change the file"
        assert b"185.0" in crlf_file.read_bytes()
        assert info.sha_before == before
        assert info.sha_planted == during

    assert fz.sha256_file(crlf_file) == before, "RULE 2: restore must be exact"
    assert crlf_file.read_bytes() == CRLF_SOURCE
    assert not crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX).exists()


# ── FAILURE MODE 1 — the plant that did not take ─────────────────────────────


def test_missing_anchor_raises_instead_of_skipping(fz, crlf_file):
    """The open-coded version printed '!! SKIPPED' and carried on at exit 0."""
    before = fz.sha256_file(crlf_file)

    with pytest.raises(fz.PlantDidNotTake, match="anchor NOT FOUND"):
        with fz.planted(crlf_file, "no_such_token_anywhere", "x"):
            pytest.fail("the body must never run when the plant did not take")

    assert fz.sha256_file(crlf_file) == before


def test_the_naive_pattern_is_the_one_that_no_ops(fz, crlf_file):
    """Pins the actual 2026-08 incident: an LF anchor against a CRLF file.

    This is the counterfactual, not the helper. `find in blob` is False, so the
    open-coded `blob.replace(find, repl)` returned the file unchanged, the test
    stayed green for the ordinary reason, and the run reported a proof.
    """
    blob = crlf_file.read_bytes()
    lf_anchor = b"def f():\n    return round(az + 180.0, 1)"

    assert lf_anchor not in blob, "if this fails the repo stopped using CRLF"
    assert blob.replace(lf_anchor, b"BROKEN") == blob, "the silent no-op itself"


def test_multiline_anchor_is_translated_so_the_plant_actually_takes(fz, crlf_file):
    """Same LF anchor, through the helper: it must land, not silently skip."""
    before = fz.sha256_file(crlf_file)
    lf_anchor = "def f():\n    return round(az + 180.0, 1)"

    with fz.planted(crlf_file, lf_anchor, "def f():\n    return 999", label="x") as info:
        assert info.anchor_style == "CRLF-translated"
        assert fz.sha256_file(crlf_file) != before
        # The replacement is rewritten to the file's own line ending, so the
        # plant does not leave a mixed-ending file for a linter to trip over.
        assert b"\n" not in crlf_file.read_bytes().replace(b"\r\n", b"")

    assert fz.sha256_file(crlf_file) == before


def test_lf_file_still_works(fz, lf_file):
    """The translation must not break the ordinary LF case."""
    before = fz.sha256_file(lf_file)
    with fz.planted(lf_file, "def f():\n    return round", "def f():\n    return 0 * round"):
        assert b"0 * round" in lf_file.read_bytes()
        assert b"\r\n" not in lf_file.read_bytes()
    assert fz.sha256_file(lf_file) == before


def test_replacement_identical_to_anchor_is_rejected(fz, crlf_file):
    """A mutation that does not mutate is the failure mode in its purest form."""
    with pytest.raises(fz.PlantDidNotTake, match="byte-identical"):
        with fz.planted(crlf_file, "180.0", "180.0"):
            pytest.fail("unreachable")


def test_ambiguous_anchor_is_rejected(fz, tmp_path):
    """Two matches means the defect lands somewhere the caller did not choose."""
    p = tmp_path / "twice.py"
    p.write_bytes(b"a = 1\r\nb = 1\r\n")
    with pytest.raises(fz.PlantDidNotTake, match="AMBIGUOUS"):
        with fz.planted(p, "= 1", "= 2"):
            pytest.fail("unreachable")
    assert p.read_bytes() == b"a = 1\r\nb = 1\r\n"


def test_missing_file_is_rejected(fz, tmp_path):
    with pytest.raises(fz.PlantDidNotTake, match="does not exist"):
        with fz.planted(tmp_path / "nope.py", "a", "b"):
            pytest.fail("unreachable")


def test_write_that_silently_reverts_is_caught(fz, crlf_file, monkeypatch):
    """A layer that undoes the write must not read as a successful plant."""
    real = Path.write_bytes

    def sabotage(self, data):
        return real(self, CRLF_SOURCE) if self == crlf_file else real(self, data)

    monkeypatch.setattr(Path, "write_bytes", sabotage)
    with pytest.raises(fz.PlantDidNotTake, match="did NOT take"):
        with fz.planted(crlf_file, "180.0", "185.0"):
            pytest.fail("unreachable")


# ── FAILURE MODE 2 — the restore that did not complete ───────────────────────


def _sabotage_restore(monkeypatch, target: Path, corrupt: bytes):
    """Let the plant through, then make the restore write the wrong bytes."""
    real = Path.write_bytes
    state = {"writes": 0}

    def patched(self, data):
        if self == target:
            state["writes"] += 1
            if state["writes"] > 1:  # every restore attempt, plant excluded
                return real(self, corrupt)
        return real(self, data)

    monkeypatch.setattr(Path, "write_bytes", patched)
    return state


def test_restore_that_does_not_complete_raises(fz, crlf_file, monkeypatch):
    """The #889 shape: the plant is live on disk and nothing said so."""
    sidecar = crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX)
    _sabotage_restore(monkeypatch, crlf_file, b"STILL PLANTED\r\n")

    with pytest.raises(fz.RestoreFailed, match="RESTORE FAILED"):
        with fz.planted(crlf_file, "180.0", "185.0", label="drift"):
            pass

    assert crlf_file.read_bytes() == b"STILL PLANTED\r\n"
    assert sidecar.exists(), "the sidecar must survive so --recover can undo it"
    assert sidecar.read_bytes() == CRLF_SOURCE


def test_failed_restore_outranks_a_failing_body(fz, crlf_file, monkeypatch):
    """Damage left on disk is worse news than the assertion that found it."""
    _sabotage_restore(monkeypatch, crlf_file, b"STILL PLANTED\r\n")

    with pytest.raises(fz.RestoreFailed) as excinfo:
        with fz.planted(crlf_file, "180.0", "185.0"):
            raise ValueError("the check did not go red")

    assert isinstance(excinfo.value.__context__, ValueError), "body error preserved"


def test_body_exception_propagates_when_the_restore_succeeds(fz, crlf_file):
    before = fz.sha256_file(crlf_file)
    with pytest.raises(ValueError):
        with fz.planted(crlf_file, "180.0", "185.0"):
            raise ValueError("the check did not go red")
    assert fz.sha256_file(crlf_file) == before, "a failed proof still restores"


# ── Crash safety: the sidecar ────────────────────────────────────────────────


def test_stale_sidecar_refuses_to_start(fz, crlf_file):
    """finally cannot run after a hard kill, so the next run must notice."""
    sidecar = crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX)
    sidecar.write_bytes(CRLF_SOURCE)
    crlf_file.write_bytes(b"LEFTOVER PLANT\r\n")

    with pytest.raises(fz.StalePlantFound, match="died mid-plant"):
        with fz.planted(crlf_file, "LEFTOVER", "x"):
            pytest.fail("unreachable")


def test_sidecar_is_written_atomically(fz, crlf_file):
    """A truncated backup is worse than none, because --recover TRUSTS it and
    would overwrite the target with short bytes while reporting 'restored'.
    os.replace means the sidecar name never points at a partial file."""
    sidecar = crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX)
    seen: list[bytes] = []

    with fz.planted(crlf_file, "180.0", "185.0"):
        seen.append(sidecar.read_bytes())

    assert seen == [CRLF_SOURCE], "the sidecar held the complete original"
    assert not sidecar.with_name(sidecar.name + ".tmp").exists()


def test_a_second_plant_is_refused_while_one_is_live(fz, crlf_file):
    """The ordinary sequential case, caught by the up-front existence check."""
    with fz.planted(crlf_file, "180.0", "185.0", label="first"):
        with pytest.raises(fz.StalePlantFound):
            with fz.planted(crlf_file, "185.0", "190.0", label="second"):
                pytest.fail("the second plant must never get inside")
    assert fz.sha256_file(crlf_file) == fz.sha256_bytes(CRLF_SOURCE)
    assert not crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX).exists()


def test_the_claim_survives_a_lost_check_then_act_race(fz, crlf_file, monkeypatch):
    """The one above passes even WITHOUT an atomic claim, because the up-front
    `sidecar.exists()` catches it. That check is check-then-act: two workers can
    both observe no sidecar and both proceed, and the first restore then deletes
    the second's recovery evidence.

    So this test forces the lost race -- exists() reports False for the sidecar
    even though it is there -- and requires the claim itself to refuse. Written
    after a mutation run showed the sequential test could not kill the mutant
    that swapped the atomic os.link for os.replace.
    """
    sidecar = crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX)
    real_exists = Path.exists

    def blind_to_sidecar(self, *args, **kwargs):
        if self == sidecar:
            return False
        return real_exists(self, *args, **kwargs)

    with fz.planted(crlf_file, "180.0", "185.0", label="first"):
        planted_sha = fz.sha256_file(crlf_file)
        monkeypatch.setattr(Path, "exists", blind_to_sidecar)
        with pytest.raises(fz.StalePlantFound, match="claimed by another run"):
            with fz.planted(crlf_file, "185.0", "190.0", label="racing"):
                pytest.fail("the racing plant must never get inside")
        monkeypatch.undo()
        assert sidecar.read_bytes() == CRLF_SOURCE, "first run's evidence intact"
        assert fz.sha256_file(crlf_file) == planted_sha, "target untouched by the race"

    assert fz.sha256_file(crlf_file) == fz.sha256_bytes(CRLF_SOURCE)


def test_no_temp_files_survive_a_plant(fz, crlf_file):
    with fz.planted(crlf_file, "180.0", "185.0"):
        pass
    leftovers = [p.name for p in crlf_file.parent.iterdir() if ".tmp" in p.name]
    assert leftovers == []


def test_recover_restores_and_clears(fz, crlf_file):
    sidecar = crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX)
    sidecar.write_bytes(CRLF_SOURCE)
    crlf_file.write_bytes(b"LEFTOVER PLANT\r\n")

    dry = fz.recover(crlf_file.parent, apply=False)
    assert dry == [(crlf_file, "WOULD-RESTORE")]
    assert crlf_file.read_bytes() == b"LEFTOVER PLANT\r\n", "dry run changes nothing"

    applied = fz.recover(crlf_file.parent, apply=True)
    assert applied == [(crlf_file, "restored")]
    assert crlf_file.read_bytes() == CRLF_SOURCE
    assert not sidecar.exists()


def test_check_cli_is_red_while_a_plant_is_live(fz, crlf_file, capsys):
    sidecar = crlf_file.with_name(crlf_file.name + fz.SIDECAR_SUFFIX)
    sidecar.write_bytes(CRLF_SOURCE)
    crlf_file.write_bytes(b"LEFTOVER PLANT\r\n")

    assert fz.main(["--check", "--root", str(crlf_file.parent)]) == 1
    assert "Do NOT commit or push" in capsys.readouterr().out

    assert fz.main(["--recover", "--root", str(crlf_file.parent)]) == 0
    assert fz.main(["--check", "--root", str(crlf_file.parent)]) == 0


# ── The runner ───────────────────────────────────────────────────────────────


def _runner_for(path: Path, marker: bytes):
    """Green while the file is pristine, red once `marker` is present."""

    def _run():
        return (1, "planted") if marker in path.read_bytes() else (0, "clean")

    return _run


def test_prove_reports_caught_and_restores_between_cases(fz, crlf_file):
    report = fz.prove(
        [
            fz.ProofCase("drift", crlf_file, "180.0", "185.0"),
            fz.ProofCase("second", crlf_file, "X = 1", "X = 185.0"),
        ],
        run=_runner_for(crlf_file, b"185.0"),
    )
    assert report.ok
    assert [o.ok for o in report.outcomes] == [True, True]
    assert report.baseline_returncode == 0 and report.final_returncode == 0
    assert fz.sha256_file(crlf_file) == fz.sha256_bytes(CRLF_SOURCE)
    assert "CAUGHT" in report.table()


def test_prove_marks_a_missed_defect_as_not_ok(fz, crlf_file):
    """A check that stays green under a real defect is the whole point."""
    report = fz.prove(
        [fz.ProofCase("invisible", crlf_file, "180.0", "185.0")],
        run=_runner_for(crlf_file, b"NEVER APPEARS"),
    )
    assert not report.ok
    assert "*** MISSED ***" in report.table()


def test_prove_refuses_an_already_red_baseline(fz, crlf_file):
    with pytest.raises(fz.FalsifiabilityError, match="already RED"):
        fz.prove(
            [fz.ProofCase("x", crlf_file, "180.0", "185.0")],
            run=lambda: (1, "broken before we started"),
        )


def test_expect_green_case_flags_a_false_alarm(fz, crlf_file):
    """A tolerance floor: a drift inside the pass mark must NOT go red."""
    report = fz.prove(
        [fz.ProofCase("inside tolerance", crlf_file, "180.0", "180.1", expect="green")],
        run=_runner_for(crlf_file, b"180.1"),
    )
    assert not report.ok
    assert "*** FALSE ALARM ***" in report.table()
