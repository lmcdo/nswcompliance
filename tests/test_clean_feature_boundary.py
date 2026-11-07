"""scripts/check_clean_feature_boundary.py must pass on the real feature files AND fail when broken.

A boundary check that has never failed proves nothing, so every rule has a case that must trip it,
and the real files are re-checked with a council read deliberately injected.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_clean_feature_boundary as boundary  # noqa: E402


def rules(text: str, suffix: str = ".py") -> set[str]:
    return {rule for _, rule, _ in boundary.find_violations(text, suffix)}


# ---- the real feature files ------------------------------------------------------------------


def test_real_feature_files_are_clean():
    assert boundary.check_manifest() == []


def test_manifest_is_not_empty_and_files_exist():
    files = boundary.listed_files()
    assert len(files) >= 6
    assert [f for f in files if not (ROOT / f).is_file()] == []


@pytest.mark.parametrize("rel", boundary.listed_files())
def test_injected_council_read_is_caught_in_each_real_file(rel):
    """Mutation: append a council read to the real file's text. The scanner must flag it."""
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    injected = (
        text + "\nSELECT * FROM regulatory_provisions WHERE source_council = 'woollahra'\n"
        if path.suffix == ".py"
        else text + "\nconst q = `SELECT * FROM regulatory_provisions WHERE source_council = $1`\n"
    )
    assert boundary.find_violations(text, path.suffix) == []
    assert "R4-council-filter" in rules(injected, path.suffix)
    assert "R5-unpinned-table" in rules(injected, path.suffix)


# ---- each rule trips on its own case ---------------------------------------------------------


def test_r1_view_of_rules_table():
    assert "R1-view" in rules("SELECT 1 FROM regulatory_provisions_canonical")
    assert "R1-view" in rules("SELECT 1 FROM regulatory_provisions_clean")


def test_r2_council_plan_table_or_reader():
    assert "R2-council-table" in rules("SELECT * FROM dcp_setback_controls")
    assert "R2-council-table" in rules("rows = fetch_dcp_setbacks(council)")
    assert "R2-council-table" in rules("from dcp_review_queue import x")


def test_r3_council_mixed_routes():
    assert "R3-mixed-route" in rules("await fetch('/api/provisions/for-property?x=1')", ".ts")
    assert "R3-mixed-route" in rules("useSWR('/api/dcp/structured-controls')", ".ts")


def test_r4_council_filter():
    assert "R4-council-filter" in rules("WHERE source_council = $1")
    assert "R4-council-filter" in rules("WHERE source_council IN ('a','b')")
    assert "R4-council-filter" in rules("WHERE source_council IS NOT NULL")
    assert "R4-council-filter" in rules("WHERE former_council = $1")


def test_r5_table_read_must_be_pinned_to_state_law():
    assert "R5-unpinned-table" in rules("SELECT * FROM regulatory_provisions WHERE is_current")
    assert rules("SELECT * FROM regulatory_provisions WHERE is_current AND source_council IS NULL") == set()


def test_r5_one_pinned_query_does_not_hide_a_second_unpinned_one():
    """The hole the first version had: a pinned query elsewhere in the file masked an unpinned one."""
    two = (
        "a = `SELECT x FROM regulatory_provisions WHERE is_current AND source_council IS NULL`\n"
        "b = `SELECT y FROM regulatory_provisions WHERE is_current`\n"
    )
    found = boundary.find_violations(two, ".ts")
    assert [(line, rule) for line, rule, _ in found] == [(2, "R5-unpinned-table")]


def test_r5_pin_must_be_in_the_same_statement():
    assert "R5-unpinned-table" in rules(
        "SELECT x FROM regulatory_provisions WHERE is_current;\nSELECT y FROM t WHERE source_council IS NULL;"
    )


# ---- things that must NOT trip it ------------------------------------------------------------


def test_comments_may_name_what_a_file_avoids():
    assert rules("# never reads dcp_setback_controls or source_council = x\nx = 1\n") == set()
    assert rules("// avoids /api/dcp/ and regulatory_provisions_canonical\nconst a = 1\n", ".ts") == set()
    assert rules("/* dcp_x\n source_council = 1 */\nconst a = 1\n", ".ts") == set()


def test_urls_in_ts_are_not_treated_as_comments():
    assert "R3-mixed-route" in rules("fetch('https://x.test/api/dcp/y')", ".ts")


def test_state_law_table_names_do_not_trip_it():
    assert rules("SELECT * FROM housing_sepp_standards WHERE clause = $1") == set()


def test_line_numbers_survive_comment_stripping():
    text = "# one\n# two\nSELECT * FROM dcp_x\n"
    assert boundary.find_violations(text, ".py")[0][0] == 3
    ts = "/* a\nb */\n// c\nconst q = 'dcp_x'\n"
    assert boundary.find_violations(ts, ".ts")[0][0] == 4


# ---- the manifest itself fails closed --------------------------------------------------------


def test_missing_listed_file_is_a_failure(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"files": ["services/does_not_exist.py"]}), encoding="utf-8")
    assert boundary.check_manifest(m, tmp_path) == ["services/does_not_exist.py: listed but missing"]


def test_empty_manifest_is_a_failure(tmp_path):
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"files": []}), encoding="utf-8")
    assert boundary.check_manifest(m, tmp_path) != []


def test_violation_in_a_listed_file_is_reported_with_its_line(tmp_path):
    (tmp_path / "f.py").write_text("x = 1\nq = 'SELECT 1 FROM dcp_review_queue'\n", encoding="utf-8")
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"files": ["f.py"]}), encoding="utf-8")
    problems = boundary.check_manifest(m, tmp_path)
    assert len(problems) == 1 and problems[0].startswith("f.py:2: R2-council-table")
