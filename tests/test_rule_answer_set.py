"""The sorting step ("is this a rule?") scored against real council text with known answers.

tests/fixtures/rule_answer_set.json is built by scripts/build_rule_answer_set.py from the
live R2 PDFs: the hand-made answer key of 2026-10-14 plus real waiting table rows labelled
2026-11-04. Plan: docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md §5.3 Tier 1.

Each call is the one enrichment/pipeline.py makes -- with the row's document id.

The floors are today's measured scores. They are a ratchet: raise them when the sorting step
gets better; a change that lowers either fails here before it merges.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from enrichment.extractors.actionable_classifier import classify_provision  # noqa: E402

_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "rule_answer_set.json")
ROWS = json.load(open(_PATH, encoding="utf-8"))

# Measured 2026-11-04 after the parking-space fix: 572 of 782 rules, 49 of 75 non-rules.
# Most of the 210 missed rules are list items cut from their lead-in -- a known gap.
RULES_FOUND_FLOOR = 572
NON_RULES_AS_RULES_CEILING = 49


def _is_rule(row):
    return classify_provision(row["text"], row["document_id"])[0]


def test_the_answer_set_is_the_size_it_was_built_at():
    """A shrunken fixture would pass every floor below by having fewer rows to miss."""
    assert len(ROWS) == 857
    assert sum(r["is_rule"] for r in ROWS) == 782


def test_every_waiting_table_row_with_a_value_is_a_rule():
    """The 92 real queue rows -- setbacks, parking rates, shade cover -- in pipeline shape."""
    missed = [r["id"] for r in ROWS if r["source"] == "queue" and not _is_rule(r)]
    assert missed == []


def test_rules_found_does_not_fall():
    found = sum(1 for r in ROWS if r["is_rule"] and _is_rule(r))
    assert found >= RULES_FOUND_FLOOR, f"{found} rules found, floor {RULES_FOUND_FLOOR}"


def test_non_rules_called_rules_does_not_rise():
    wrong = sum(1 for r in ROWS if not r["is_rule"] and _is_rule(r))
    assert wrong <= NON_RULES_AS_RULES_CEILING, f"{wrong}, ceiling {NON_RULES_AS_RULES_CEILING}"
