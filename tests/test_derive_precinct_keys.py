"""Precinct-keying derivation strategies — hermetic pure-function tests.

prior-art-checked: backend keying derivation (writes v2_precinct_id), distinct from
the frontend precinct-serving code the guard flags.
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "derive_precinct_keys", Path(__file__).parent.parent / "scripts" / "derive_precinct_keys.py"
)
mod = importlib.util.module_from_spec(spec)
sys.modules.setdefault("derive_precinct_keys", mod)
spec.loader.exec_module(mod)

derive = mod._derive


def row(**kw):
    base = {"document_id": None, "ref_number": None, "pdf_page": None, "source_chapter_key": None}
    base.update(kw)
    return base


def test_doc_regex_marrickville():
    s = {"type": "doc_regex", "pattern": r"__part9_p0*([0-9]+)_", "template": "{0}_"}
    assert derive(s, row(document_id="Marrickville_DCP_2011__part9_p01_lewisham_north")) == "1_"
    assert derive(s, row(document_id="Marrickville_DCP_2011__part9_p48_mary")) == "48_"
    assert derive(s, row(document_id="Marrickville_DCP_2011__part8_heritage")) is None


def test_ref_regex_leichhardt_c2():
    s = {"type": "ref_regex", "pattern": r"__C2((?:_[0-9]+)+)", "template": "C2{dotted}"}
    assert derive(s, row(ref_number="Leichhardt__part_c_s2__C2_2_1_1")) == "C2.2.1.1"
    assert derive(s, row(ref_number="Leichhardt__part_c_s2__C2_1")) == "C2.1"
    assert derive(s, row(ref_number="Leichhardt__part_c_s2__C2_2_1_1(b) C3")) == "C2.2.1.1"


def test_constant():
    assert derive({"type": "constant", "precinct_id": "Haberfield"}, row()) == "Haberfield"


def test_chapter_map():
    s = {"type": "chapter_map", "map": {"section-b-part-14i-killara-golf-club": "14I"}}
    assert derive(s, row(source_chapter_key="section-b-part-14i-killara-golf-club")) == "14I"
    assert derive(s, row(source_chapter_key="section-b-part-14a-st-ives-local-centre")) is None


def test_column_copy_waverley():
    s = {"type": "column_copy", "column": "v2_dcp_part", "match": r"^E[0-9]$"}
    assert derive(s, {**row(), "v2_dcp_part": "E1"}) == "E1"
    assert derive(s, {**row(), "v2_dcp_part": "E7"}) == "E7"
    assert derive(s, {**row(), "v2_dcp_part": "B5"}) is None
    assert derive(s, {**row(), "v2_dcp_part": None}) is None


def test_page_range():
    s = {"type": "page_range", "ranges": [("Part 1", 3, 40), ("Part 6", 107, 155)]}
    assert derive(s, row(pdf_page=20)) == "Part 1"
    assert derive(s, row(pdf_page=120)) == "Part 6"
    assert derive(s, row(pdf_page=200)) is None
    assert derive(s, row(pdf_page=None)) is None


def test_cos_page_ranges_are_contiguous_and_ordered():
    """The City of Sydney sidecar drives 3 validate:True rules; a bad regeneration
    could mis-key a whole area two ways, so guard both invariants the generator
    holds. OVERLAP (two spans share a page) -> the first-listed precinct silently
    wins. GAP (a page belongs to no span) -> a re-extracted row there derives None
    and falls back to city-wide serving. The generator folds each span's hi forward
    to next_lo-1, so within a chapter the spans are strictly contiguous
    (lo == prev_hi + 1) — assert exactly that, which rules out both failures."""
    ranges = mod._COS_RANGES
    assert set(ranges) == {
        "Sydney_DCP_2012__section_2_locality_statements",
        "Sydney_DCP_2012__section_5_specific_areas",
        "Sydney_DCP_2012__section_6_specific_sites",
    }
    for doc, rs in ranges.items():
        assert rs, doc
        prev_hi = None
        for pid, lo, hi in rs:
            assert lo <= hi, f"{doc}: {pid} inverted range {lo}>{hi}"
            if prev_hi is not None:
                assert lo == prev_hi + 1, (
                    f"{doc}: {pid} not contiguous with previous "
                    f"(lo={lo}, expected {prev_hi + 1}) — overlap or gap")
            prev_hi = hi
