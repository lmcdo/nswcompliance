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


def test_planted_figure_in_real_tree_fails_as_unlisted(tmp_path):
    """A new typed figure anywhere in the shipped tree fails the check (it is not in the ledger)."""
    f = tmp_path / "frontend-nextjs" / "lib" / "planted.ts"
    f.parent.mkdir(parents=True)
    f.write_text("export const MIN = 'minimum lot size 450 m²';\n", encoding="utf-8")
    found, bad = lint.scan(tmp_path)
    assert found == {"frontend-nextjs/lib/planted.ts": ["'minimum lot size 450 m²'"]} and bad == []
    assert any("NOT IN LEDGER" in p for p in lint.judge(found, {"max_open": 0, "entries": []}))


# ---- 2026-10-22: widened shapes and the named ledger ------------------------------------------------------------
# Each is a real line found by the 2026-10-22 inventory that the old patterns could not see.
WIDER = [
    ("  { q: 'What parking applies?', a: 'Residential parking rates are typically 1 space per dwelling.' },", ".ts"),
    ("  maxFsr: '0.5:1', // floor space ratio fallback", ".ts"),
    ("    note: 'Visitor parking: 1 space per 5 dwellings under the SEPP',", ".ts"),
    ("DEFAULT_HEIGHT_M = 9.0  # height assumed when the LEP height is missing", ".py"),
    ("  const solar = 'at least 2 hours of direct sunlight to living rooms';", ".ts"),
    ("  label: 'Maximum two storeys under the Housing Code',", ".ts"),
    ('  "note": "minimum lot size 450 m2 for a secondary dwelling"', ".json"),
    ("A granny flat needs a minimum lot size of 450 m² under the SEPP.", ".md"),
]


def test_every_widened_shape_is_caught():
    for line, suffix in WIDER:
        assert lint.hits_in_text(line, suffix), line


def _ledger(entries, max_open=None):
    return {"max_open": max_open if max_open is not None else sum(e["fate"] == "open" for e in entries),
            "entries": entries}


def test_an_unlisted_figure_fails():
    found = {"a.ts": ["'Minimum lot size is 450 m²'"]}
    assert any("NOT IN LEDGER" in p for p in lint.judge(found, _ledger([])))


def test_a_listed_figure_passes_and_a_fixed_one_must_be_pruned():
    e = {"file": "a.ts", "text": "'Minimum lot size is 450 m²'", "fate": "open"}
    assert lint.judge({"a.ts": [e["text"]]}, _ledger([e])) == []
    assert any("GONE" in p for p in lint.judge({}, _ledger([e])))


def test_open_count_cannot_rise():
    es = [{"file": "a.ts", "text": f"'{n} m setback'", "fate": "open"} for n in (3, 4)]
    found = {"a.ts": [e["text"] for e in es]}
    assert any("OPEN COUNT ROSE" in p for p in lint.judge(found, _ledger(es, max_open=1)))


def test_cited_needs_instrument_and_clause_and_not_regulatory_needs_a_reason():
    cited_bad = {"file": "a.ts", "text": "'60 m² floor area'", "fate": "cited", "reason": "it is a quote"}
    cited_ok = dict(cited_bad, reason="verbatim SEPP (Housing) 2021 s 53(1)(a)")
    nr_bad = {"file": "b.ts", "text": "'200 m radius'", "fate": "not_regulatory", "reason": "radius"}
    found = {"a.ts": [cited_bad["text"]], "b.ts": [nr_bad["text"]]}
    problems = lint.judge(found, _ledger([cited_bad, nr_bad]))
    assert any("CITED WITHOUT" in p for p in problems) and any("NOT_REGULATORY WITHOUT" in p for p in problems)
    assert not any("CITED WITHOUT" in p for p in lint.judge({"a.ts": [cited_ok["text"]]}, _ledger([cited_ok])))


def test_a_suppression_needs_a_real_reason():
    assert lint.bad_suppressions("x = '3 m'  # noqa: regulatory-number") 
    assert not lint.bad_suppressions("x = '3 m'  # noqa: regulatory-number -- geographic bounds, not planning")


def test_the_repo_ledger_matches_the_code():
    """The real check, run as a test: 0 unlisted, 0 gone, every reason present."""
    import os
    root = Path(__file__).resolve().parent.parent
    cwd = os.getcwd()
    os.chdir(root)
    try:
        found, bad = lint.scan()
        assert lint.judge(found, lint.load_ledger()) == [] and bad == []
    finally:
        os.chdir(cwd)
