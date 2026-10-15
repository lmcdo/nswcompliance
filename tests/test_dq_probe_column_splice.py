"""dq_probe_column_splice.same_row_jumps on synthetic two-column pages (Hornsby DCP 2024 layout: gutter at 298)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "dq_probe_column_splice", Path(__file__).resolve().parent.parent / "scripts" / "dq_probe_column_splice.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)


def _page(lines, cells=()):
    """lines: (x, y, text) per printed line; words get x from the line start."""
    words = []
    for x, y, text in lines:
        for i, w in enumerate(probe.toks(text)):
            words.append((w, x + 6 * i, y))
    return {"words": words, "centre": 298.0, "cells": list(cells)}


LEFT = [(67, 147, "evidence to be dead and is not required as the"), (67, 160, "habitat of native fauna and more")]
RIGHT = [(358, 151, "Land located within 50 metres of and"), (358, 164, "including land that contains native vegetation")]


def test_interleaved_columns_are_a_splice():
    page = _page(LEFT + RIGHT)
    assert probe.same_row_jumps("evidence to be dead and is not required as the\nLand located within 50 metres of and",
                                page) >= 1


def test_one_column_rule_is_not_a_splice():
    page = _page(LEFT + RIGHT)
    assert probe.same_row_jumps("evidence to be dead and is not required as the\nhabitat of native fauna and more",
                                page) == 0


def test_continuation_to_the_head_of_the_next_column_is_not_a_splice():
    page = _page([(67, 780, "development should be designed to reduce"), (337, 72, "the visual bulk of new buildings and")])
    assert probe.same_row_jumps("development should be designed to reduce\nthe visual bulk of new buildings and",
                                page) == 0


def test_table_row_read_across_is_not_a_splice():
    page = _page([(51, 150, "0-2 Bedrooms"), (395, 150, "1 space per dwelling")], cells=[(45, 149, 237, 164)])
    assert probe.same_row_jumps("0-2 Bedrooms\n1 space per dwelling", page) == 0


def test_rule_not_on_its_page_is_unknown_never_clean():
    assert probe.same_row_jumps("words that are not printed\nanywhere on this page at all", _page(LEFT)) is None
