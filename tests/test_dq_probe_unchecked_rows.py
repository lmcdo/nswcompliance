"""The five checks written for the rows that had none — proven able to FAIL.

A probe that reads 0 is worthless until you have seen it read something else.
`.claude/dq_checks.json`'s own README says it outright: "An invented check that
cannot fail is what produced DQ-30's '0% drift' verification — worse than no
check." DQ-53's probe reads 0 on this repo today, so most of this file exists to
show that number is a measurement and not a shape.

Every detector here gets a CONFUSABLE NEGATIVE beside its positive — the case
that looks the same and must NOT fire. That pairing is
`feedback-detect-a-guard-by-forcing-its-failure`, and it is not theoretical
here: the first version of the DQ-53 detector reported three false positives on
this very suite, because it asked "is there a `.to_dict(`-shaped call?" instead
of "does this test call into the project at all?". Enumerating call shapes is a
way of missing one, and it failed in the direction that sends someone to repair
a working test. The three it wrongly accused are pinned by name below.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import dq_probe_unchecked_rows as probe  # noqa: E402


# ── DQ-53 ────────────────────────────────────────────────────────────────────
FIXTURE_ONLY = '''
import json
from services.flood_truth import _normalise_outputs

def test_climate_contract_matches_keys():
    """Compares two STORED things. Never calls the producer."""
    contract = json.loads(open("contract.json").read())
    golden = json.loads(open("golden.json").read())
    assert set(contract) == set(golden)
'''

CALLS_A_PLAIN_FUNCTION = '''
import json
from services.flood_truth import _normalise_outputs

def test_db_contract_normalise_roundtrip():
    """The real shape of a working contract test: a stored input, a LIVE call."""
    stored = json.loads(open("golden.json").read())
    out = _normalise_outputs(stored)
    assert out["ses_flood_class"] == "medium"
'''

CALLS_A_MODEL_METHOD = '''
from services.brief_models import StrataServiceOutput

def test_strata_contract_accepts_registration_date():
    """Also working — the live call is a classmethod, not `.to_dict()`."""
    cad = _golden("strata_cadastre")
    out = StrataServiceOutput.model_validate(cad)
    assert out.lot_total == 77
'''


def _run_53_over(tmp_path, monkeypatch, *sources: str) -> dict:
    tests = tmp_path / "tests"
    tests.mkdir()
    for i, src in enumerate(sources):
        (tests / f"test_synthetic_{i}.py").write_text(src, encoding="utf-8")
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    _count, hits = probe.probe_53()
    return {name for _f, name in hits}


class TestDQ53CanActuallyFire:
    def test_it_catches_a_contract_test_that_never_calls_the_producer(
            self, tmp_path, monkeypatch):
        """The positive. Without this the 0 on the real repo means nothing."""
        assert _run_53_over(tmp_path, monkeypatch, FIXTURE_ONLY) == {
            "test_climate_contract_matches_keys"}

    @pytest.mark.parametrize("src,name", [
        (CALLS_A_PLAIN_FUNCTION, "test_db_contract_normalise_roundtrip"),
        (CALLS_A_MODEL_METHOD, "test_strata_contract_accepts_registration_date"),
    ])
    def test_it_does_not_fire_on_a_test_that_does_call_the_producer(
            self, tmp_path, monkeypatch, src, name):
        """The confusable negatives, and both are REAL false positives the first
        detector produced. One calls a plain function, one a classmethod; an
        enumerate-the-call-shapes detector misses both and accuses them."""
        assert _run_53_over(tmp_path, monkeypatch, src) == set()

    def test_the_positive_and_the_negatives_together(self, tmp_path, monkeypatch):
        """Run as one suite: exactly the fixture-only test is named."""
        got = _run_53_over(tmp_path, monkeypatch, FIXTURE_ONLY,
                           CALLS_A_PLAIN_FUNCTION, CALLS_A_MODEL_METHOD)
        assert got == {"test_climate_contract_matches_keys"}

    def test_the_three_real_tests_it_once_accused_are_clean(self):
        """Against the REAL suite, not a fixture. These three exercise live code
        and must never be reported again."""
        _count, hits = probe.probe_53()
        accused = {name for _f, name in hits}
        for name in ("test_db_contract_normalise_roundtrip",
                     "test_db_contract_normalise_empty_roundtrip",
                     "test_strata_contract_accepts_registration_date"):
            assert name not in accused, f"{name} calls into the project; it is not the defect"


# ── DQ-31 ────────────────────────────────────────────────────────────────────
#: One implementation, in the language the backend actually uses. It BRANCHES
#: on the gate, which is what makes it a decision rather than a mention.
PY_IMPLEMENTATION = (
    "def evaluate_eligibility(in_lmr_area):\n"
    "    if in_lmr_area:\n"
    "        return {'is_eligible': True}\n"
    "    return {'is_eligible': False}\n"
)

#: A second, independent implementation in the frontend's spelling.
TS_IMPLEMENTATION = (
    "const eligibleTypes = [];\n"
    "const inLMRArea = isLMRArea === true;\n"
)

#: Confusable negative 1 — forwards to the service and destructures the reply.
TS_FORWARDS = (
    "const r = await fetch('/api/housing-sepp/eligibility');\n"
    "const { eligibleTypes, isLMRArea } = await r.json();\n"
)

#: Confusable negative 2 — a prop DECLARATION. `isLMRArea?: boolean` is one
#: character away from a ternary and was miscounted as a decision.
TSX_PROP_ONLY = (
    "interface Props { assessmentStatus: string; isLMRArea?: boolean }\n"
    "export function Card({ assessmentStatus, isLMRArea }: Props) {\n"
    "  return <div>{assessmentStatus}</div>;\n"
    "}\n"
)


def _run_31_over(tmp_path, monkeypatch, files: dict) -> int:
    (tmp_path / "services").mkdir(exist_ok=True)
    (tmp_path / "frontend-nextjs").mkdir(exist_ok=True)
    for rel, src in files.items():
        (tmp_path / rel).write_text(src, encoding="utf-8")
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    return probe.probe_31()[0]


class TestDQ31CountsDecisionsNotMentions:
    def test_a_single_implementation_reads_zero(self, tmp_path, monkeypatch):
        """The target state. `max(len - 1, 0)` is the whole contract: one copy
        of a regulated decision is consolidation, two is the defect."""
        assert _run_31_over(tmp_path, monkeypatch, {
            "services/housing_sepp_eligibility.py": PY_IMPLEMENTATION}) == 0

    def test_a_second_implementation_reads_one(self, tmp_path, monkeypatch):
        """The positive, and the state this repo is actually in."""
        assert _run_31_over(tmp_path, monkeypatch, {
            "services/housing_sepp_eligibility.py": PY_IMPLEMENTATION,
            "frontend-nextjs/route.ts": TS_IMPLEMENTATION}) == 1

    def test_a_caller_that_forwards_is_not_a_second_implementation(
            self, tmp_path, monkeypatch):
        """A file that names the same fields while DELEGATING is not a copy.
        Counting it would make consolidation unreachable — the count could never
        fall to zero however much was merged, which is a ratchet that measures
        nothing."""
        assert _run_31_over(tmp_path, monkeypatch, {
            "services/housing_sepp_eligibility.py": PY_IMPLEMENTATION,
            "frontend-nextjs/caller.ts": TS_FORWARDS}) == 0

    def test_a_prop_declaration_is_not_an_implementation(self, tmp_path, monkeypatch):
        """`isLMRArea?: boolean` — TypeScript's optional-property marker. A bare
        `\\?` in the pattern reads it as a ternary, and that single character
        made a presentational component count as an implementation of the
        eligibility decision. This is the regression, pinned."""
        assert _run_31_over(tmp_path, monkeypatch, {
            "services/housing_sepp_eligibility.py": PY_IMPLEMENTATION,
            "frontend-nextjs/Card.tsx": TSX_PROP_ONLY}) == 0

    def test_the_two_files_it_reports_on_the_real_repo_are_the_two_that_decide(self):
        """Against the real tree. `services/housing_sepp_eligibility.py` names
        the route as "the only prior implementation" in its own docstring, and
        those are the two that must appear — no component, no comment."""
        _count, hits = probe.probe_31()
        assert {f for f, _ in hits} == {
            "frontend-nextjs/app/api/housing-sepp/eligibility/route.ts",
            "services/housing_sepp_eligibility.py"}


# ── the runner contract, shared by all five ──────────────────────────────────
class TestTheRunnerContract:
    def test_every_row_that_had_no_check_now_has_one(self):
        """The point of the exercise. A row declared open with `check: null` is
        the single state the ledger's two-way ratchet cannot see."""
        import json

        checks = json.loads(
            (ROOT / ".claude" / "dq_checks.json").read_text(encoding="utf-8"))["checks"]
        for dq in ("DQ-31", "DQ-42", "DQ-43", "DQ-53", "DQ-58"):
            assert checks[dq].get("check"), f"{dq} still has no check"

    def test_each_probe_is_reachable_by_the_id_the_ledger_calls_it(self):
        for dq in ("DQ-31", "DQ-42", "DQ-43", "DQ-53", "DQ-58"):
            assert dq in probe.PROBES

    def test_the_static_probes_need_no_database(self):
        """DQ-31 and DQ-53 must stay runnable in CI's python job, which has no
        DATABASE_URL. A probe that cannot run is a check that does not exist."""
        for dq in ("DQ-31", "DQ-53"):
            assert probe.PROBES[dq][3] is False, f"{dq} was marked as needing a DB"
