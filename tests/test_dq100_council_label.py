"""A served DCP row with no council is invisible to every council-scoped check.

Measured 2026-09-21: 1,336 served provisions whose document_id names a DCP carry
`source_council IS NULL` -- every one an Inner West Ashfield DCP 2016 chapter --
while 2,041 rows of the SAME document family correctly say 'ashfield'. One
document set, labelled two ways.

It matters more than its size. Those rows are skipped by the DQ-70 staleness join,
the plan-in-force confirmation, per-council coverage counts, and DQ-33 -- which was
narrowed to `source_council IS NOT NULL` on 2026-09-19 for the sound reason that a
statewide instrument has no council config to resolve against. Right for real
statewide rows, wrong for these, so that ratchet is quietly excluding council data.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dq_probe_live  # noqa: E402


def _sql(entry) -> str:
    return next(x for x in entry if isinstance(x, str) and "SELECT" in x.upper())


class TestTheProbeExistsAndAsksTheRightThing:
    def test_dq100_is_registered(self):
        assert "DQ-100" in dq_probe_live.PROBES

    def test_it_counts_served_rows_only(self):
        sql = _sql(dq_probe_live.PROBES["DQ-100"])
        assert "is_current" in sql and "v2_is_actionable" in sql, (
            "a superseded or non-actionable row is not something we serve")

    def test_it_looks_for_a_DCP_with_no_council(self):
        sql = _sql(dq_probe_live.PROBES["DQ-100"])
        assert "source_council IS NULL" in sql
        assert "DCP" in sql, "the signature is a DCP document, which always has a council"

    def test_percent_signs_are_escaped(self):
        """psycopg2 reads a lone %% as a parameter placeholder even with an empty
        parameter tuple, and raises IndexError before the query runs. The first
        version of this probe did exactly that."""
        sql = _sql(dq_probe_live.PROBES["DQ-100"])
        import re
        assert not re.search(r"(?<!%)%(?!%)", sql), (
            "an unescaped % will make this probe raise IndexError instead of counting")

    def test_it_does_not_silently_swallow_the_LEP_question(self):
        """554 served LEP rows also carry no council. Whether an LEP belongs to its
        council is a real question with a defensible answer either way, and folding
        it in would make this count arguable rather than exact."""
        entry = dq_probe_live.PROBES["DQ-100"]
        blob = " ".join(x for x in entry if isinstance(x, str))
        assert "Local_Environmental_Plan" not in _sql(entry), (
            "LEP rows must not be counted here")
        src = (ROOT / "scripts" / "dq_probe_live.py").read_text(encoding="utf-8")
        assert "554 served LEP rows" in src, (
            "the excluded case must stay written down, or it is just missing")
