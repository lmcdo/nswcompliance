"""DQ-111: the ledger probe counts with the gate's own proof, and names what it cannot judge.

The proof rules themselves are pinned in tests/test_citation_proof.py. What is
pinned here is the probe's side of the contract: the ref parser it shares, and
that a verdict is reduced to its REASON without its evidence, so the report
groups "not_nearest" rows together instead of listing one bucket per heading.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import citation_proof as cp  # noqa: E402
import dq_probe_section_code_not_in_source as p  # noqa: E402


def secs(tail):
    sections, item, reason = cp.split_ref("Doc__chapter__" + tail)
    return [cp.render(g) for g in sections], (cp.render(item) if item else None), reason


class TestSplitRef:
    def test_section_and_item(self):
        assert secs("C4_9 C5") == (["C4.9"], "C5", None)

    def test_item_joined_by_underscore(self):
        assert secs("8_2_4_7_controls_C57") == (["8.2.4.7"], "C57", None)

    def test_parenthetical_subclause_is_not_part_of_the_code(self):
        assert secs("C2_2_1_2(a) C1") == (["C2.2.1.2"], "C1", None)  # noqa: zone-codes -- DCP section keys, not zones

    def test_two_section_groups_are_both_kept(self):
        assert secs("G9 G8_10_1 O2") == (["G9", "G8.10.1"], "O2", None)

    def test_bare_integer_is_declared_not_dropped(self):
        assert secs("6")[2] == "bare integer section (not discriminating)"

    def test_words_only_is_declared_not_dropped(self):
        assert secs("height_objectives")[2] == "no clause number in the ref"


class TestKindOf:
    def test_reason_without_its_evidence(self):
        v = {"status": "not_proven", "detail": "8.2.31.6: not_nearest:8.2.39.6 applicable"}
        assert p.kind_of(v) == "not_nearest"

    def test_first_of_several_reasons(self):
        v = {"status": "not_proven", "detail": "G8: cross_ref_only; G7.7.5: item_missing"}
        assert p.kind_of(v) == "cross_ref_only"

    def test_other_statuses_pass_through(self):
        assert p.kind_of({"status": "text_not_found", "detail": "x"}) == "text_not_found"
        assert p.kind_of({"status": "proven", "detail": None}) == "proven"
