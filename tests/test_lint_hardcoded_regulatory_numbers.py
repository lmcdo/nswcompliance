"""scripts/lint_hardcoded_regulatory_numbers.py catches the figures that actually leaked.

Each case is a real line from 2026-10-09/10: the typed 450 m2 granny-flat
minimum and the typed SEPP table. A check that misses its own origin proves
nothing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import lint_hardcoded_regulatory_numbers as lint  # noqa: E402

LEAKED = [
    "lot_area: `Lot area ${lotArea} m² — minimum 450 m² required under SEPP Housing 2021`,",
    "  { label: 'Max. floor area',  value: '60 m²',           clause: 'cl. 4.18' },",
    "  { label: 'Max. height',      value: '8.5 m',           clause: 'Sch. 3 Subdiv. 4' },",
    "      'Lot is below the 450 m\\u00B2 minimum required under SEPP Housing 2021 for the CDC pathway.',",
]


def test_every_leaked_shape_is_caught():
    for line in LEAKED:
        assert lint.hits_in_text(line), line


def test_plain_jsx_text_is_caught():
    assert lint.hits_in_text("        <p>Minimum lot size is 450 m²</p>") == ["Minimum lot size is 450 m²"]


def test_comments_and_suppressed_lines_are_not_counted():
    assert lint.hits_in_text("// minimum 450 m² lot (old rule)") == []
    assert lint.hits_in_text("x = '3 m clearance'  # noqa: regulatory-number -- engineering buffer") == []


def test_non_planning_numbers_are_not_counted():
    assert lint.hits_in_text("const label = '450 ms timeout';") == []
    assert lint.hits_in_text("print('loaded 12 files')") == []


def test_a_rise_fails_and_a_new_file_counts_from_zero():
    rises, _ = lint.compare({"a.ts": 2}, {"a.ts": 3, "b.ts": 1})
    assert rises == ["a.ts: 2 -> 3", "b.ts: 0 -> 1"]


def test_a_fall_is_reported_not_failed():
    rises, falls = lint.compare({"a.ts": 2}, {"a.ts": 1})
    assert rises == [] and falls == ["a.ts: 2 -> 1"]


def test_planted_figure_in_real_tree_raises_the_count(tmp_path):
    f = tmp_path / "frontend-nextjs" / "lib" / "planted.ts"
    f.parent.mkdir(parents=True)
    f.write_text("export const MIN = 'minimum lot size 450 m²';\n", encoding="utf-8")
    assert lint.scan(tmp_path) == {"frontend-nextjs/lib/planted.ts": ["'minimum lot size 450 m²'"]}
