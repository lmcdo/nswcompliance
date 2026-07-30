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


PARRA_MAP = {"7": 3, "8": 3, "9.10": 3, "9": 1}
def _parra(ref):
    s = {"type": "ref_components", "components_map": PARRA_MAP, "max_top_digits": 1}
    return derive(s, row(ref_number=ref))


def test_ref_components_mixed_depth_per_part():
    assert _parra("...__7_10_1_3") == "7.10.1"      # Part 7: depth 3
    assert _parra("...__8_2_6_1") == "8.2.6"          # Part 8: depth 3
    assert _parra("...__9_3_5_2") == "9"              # Part 9 default: depth 1
    assert _parra("...__9") == "9"
    assert _parra("...__9_10_2_3") == "9.10.2"        # Part 9's 9.10 sub-group: depth 3
    assert _parra("...__9_10") == "9"                 # not enough components for 9.10's depth -> falls back to "9"
    assert _parra("...__9B_1_1_controls") == "9B"      # letter-suffixed part


def test_ref_components_rejects_bare_chunk_counters():
    """A raw index like '387' must NOT be misread as a real (wrong) precinct number —
    this is the exact failure mode that would silently mis-key a row."""
    assert _parra("...__387") is None
    assert _parra("...__45") is None


def test_ref_components_letter_attaches_to_top_level_part():
    """The letter suffix belongs to the top-level part identity ('9B'), not to
    whichever component happens to be trimmed last. No letter-suffixed part with
    depth>1 exists in Parramatta's corpus today, but the map is general-purpose —
    prove a hypothetical '7B' with depth 3 derives '7B.10.1', not '7.10.1B'."""
    s = {"type": "ref_components",
         "components_map": {"7": 3, "9": 1}, "max_top_digits": 1}
    assert derive(s, row(ref_number="...__7B_10_1_3")) == "7B.10.1"
    assert derive(s, row(ref_number="...__9B")) == "9B"


def test_ref_components_rejects_non_precinct_parts():
    """Parts outside the map (e.g. Parramatta Part 3 'Residential Development' — a
    general topic chapter, not a precinct) must derive None, not the raw heading
    number. Regression guard: an earlier version silently returned the untrimmed
    value here, which would have newly mis-keyed ~142 deliberately-unkeyed rows."""
    assert _parra("...__3") is None
    assert _parra("...__3_2_cont") is None
    assert _parra("...__2_3") is None
    assert _parra("...__1_8") is None


def test_ref_components_no_match_returns_none():
    assert _parra("...__R4__high_density_residential_11") is None
    assert _parra("...__1__bedroom_10_20_of") is None


def test_text_heading_full_and_trimmed():
    s_full = {"type": "text_heading"}
    assert derive(s_full, row(provision_text="# 2.1.1 York Street Special Character Area")) == "2.1.1"
    s2 = {"type": "text_heading", "components": 2}   # area granularity (5.x)
    assert derive(s2, row(provision_text="# 5.1.1.4 Built form massing")) == "5.1"
    s3 = {"type": "text_heading", "components": 3}   # site granularity (6.x.y)
    assert derive(s3, row(provision_text="# 6.1.4.2 Built Form and Design")) == "6.1.4"


def test_text_heading_none_when_no_heading():
    s = {"type": "text_heading"}
    assert derive(s, row(provision_text="Section 5 general text with no leading heading")) is None
    assert derive(s, row(provision_text="")) is None
    assert derive(s, row(provision_text=None)) is None
    # a garbled figure page (no parseable number) yields None -> fall back to another rule
    assert derive(s, row(provision_text="# 1 C O S D y e d ve n l e o y pment")) == "1"


def test_fingerprint_passes_on_matching_structure():
    fp = {"max_page": 169, "min_coverage": 0.95}
    # last page matches, every row derived -> no reasons
    assert mod._fingerprint_reasons(fp, [1, 50, 169], n_none=0, n_total=107) == []


def test_fingerprint_fails_closed_on_repagination():
    """A new amendment that shifts the last page must trip the gate so keys are
    NOT written (fail-closed) rather than mapping shifted pages to old ranges."""
    fp = {"max_page": 169, "min_coverage": 0.95}
    reasons = mod._fingerprint_reasons(fp, [1, 50, 172], n_none=0, n_total=107)
    assert reasons and "re-paginated" in reasons[0]


def test_fingerprint_fails_closed_on_low_coverage():
    """If many re-extracted rows fall outside every span, the structure drifted."""
    fp = {"max_page": 169, "min_coverage": 0.95}
    reasons = mod._fingerprint_reasons(fp, [1, 169], n_none=20, n_total=100)  # 80% covered
    assert any("coverage" in r for r in reasons)


def test_fingerprint_reports_both_failures():
    fp = {"max_page": 169, "min_coverage": 0.95}
    reasons = mod._fingerprint_reasons(fp, [1, 300], n_none=30, n_total=100)
    assert len(reasons) == 2


def test_cos_rules_carry_a_fingerprint():
    """Every CoS page_range rule must ship a fingerprint, else re-extraction could
    silently mis-key when the PDF changes. Guards against adding a 4th CoS rule
    without the gate."""
    cos = [r for r in mod.RULES if r["council"] == "city_of_sydney"]
    assert len(cos) == 3
    for r in cos:
        assert "fingerprint" in r, r["name"]
        assert r["fingerprint"]["max_page"] > 0 and 0 < r["fingerprint"]["min_coverage"] <= 1


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
