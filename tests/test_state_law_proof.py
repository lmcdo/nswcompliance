"""state_law_proof: normaliser, verbatim found / partial / not found, clause attribution."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import state_law_proof as S  # noqa: E402
from apply_state_law_proof import check_plan  # noqa: E402
from law_change_diff import paragraphs  # noqa: E402

PAGE = """<html><body>
<h2>Schedule 1 Things</h2>
<p>3A.12 Fences (1) A fence must be no higher than 1.8m , and must be set back 2m ; unless exempt.</p>
<p>(a) the fence is of timber, or</p>
<p>(b) the fence is of metal – painted, or</p>
<p>2.30AB Pool barriers A pool barrier must comply with the Swimming Pools Act and the
standards stated in the fol-
lowing table of requirements for all barriers of every kind in use.</p>
<p>Retaining walls must be built by a licensed builder using approved materials only and inspected by the certifier before any backfilling work starts on the site each year.</p>
<p>s 2.30AB: Am 2022 (349), Sch 1[3].</p>
</body></html>"""


def law():
    return S.Law(paragraphs(PAGE))


def test_normalise_space_before_punct_tags_and_whitespace():
    assert S.normalise("a  <b>fence</b> , and\n\tmore ; ok .") == "a fence, and more; ok."


def test_normalise_unescapes_entities():
    assert S.normalise("Tom &amp; Jerry") == "Tom & Jerry"


def test_squash_joins_hyphen_linebreak_and_folds_dash():
    assert S.squash("the fol-\nlowing – table") == S.squash("the following - table")


def test_strip_heading_removes_only_leading_hash_line():
    assert S.strip_heading("# 3A.12 Fences\n(1) A fence") == "(1) A fence"
    assert S.strip_heading("(1) A fence # not heading") == "(1) A fence # not heading"


def test_verbatim_found_exact_with_clause():
    v = law().prove("(1) A fence must be no higher than 1.8m, and must be set back 2m; unless exempt.")
    assert (v["status"], v["tier"], v["clause"]) == ("proven", "exact", "Schedule 1 cl 3A.12")


def test_heading_line_is_ignored():
    v = law().prove("# 3A.12 Fences\n(a) the fence is of timber, or")
    assert v["status"] == "proven" and v["clause"] == "Schedule 1 cl 3A.12"


def test_relaxed_tier_for_dash_and_whitespace_difference():
    v = law().prove("(b) the fence is of metal - painted,\nor")
    assert v["status"] == "proven" and v["tier"] == "relaxed"


def test_hyphen_linebreak_proves_relaxed():
    v = law().prove("standards stated in the fol-\nlowing table of requirements")
    assert v["status"] == "proven" and v["clause"] == "Schedule 1 cl 2.30AB"


def test_changed_word_is_not_proven():
    v = law().prove("(a) the fence is of brick, or")
    assert v["status"] == "text_not_found"


def test_partial_when_most_runs_present():
    base = ("Retaining walls must be built by a licensed builder using approved materials only and inspected by "
            "the certifier before any backfilling work starts on the site each")
    v = law().prove(base + " decade")
    assert v["status"] == "partial"


def test_garbled_text_not_found_and_empty():
    assert law().prove("Roof solar absorptance rating must be 0.64 or less.")["status"] == "text_not_found"
    assert law().prove("# only a heading")["status"] == "text_not_found"


def test_repeated_text_in_two_clauses_has_no_single_clause():
    page = "<p>1 First Do the thing.</p><p>(a) same words here, or</p><p>2 Second Other.</p><p>(a) same words here, or</p>"
    v = S.Law(paragraphs(page)).prove("(a) same words here, or")
    assert v["status"] == "proven" and v["clause"] == "" and v["candidates"] == ["1", "2"]


def test_instrument_mapping_covers_name_variants_and_leaves_non_sepps():
    for d in ("State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation",
              "State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_27"):
        assert S.instrument_for(d) == "epi-2021-0714"
    assert S.instrument_for("State_Environmental_Planning_Policy_(Exempt_and_Complying_Development_Codes)_2008___NSW_Legislation_section_6") == "epi-2008-0572"
    assert S.instrument_for("LE9962_1") is None
    assert S.instrument_for("Chapter_E2_Haberfield_Neighbourhood") is None


def test_ref_clause():
    assert S.ref_clause("Section 86(2)") == "86"
    assert S.ref_clause("Clause 21") == "21"
    assert S.ref_clause("provision_2344") is None


def test_apply_refuses_changed_md5_and_missing_rows():
    plan = [{"id": 1, "md5": "a"}, {"id": 2, "md5": "b"}, {"id": 3, "md5": "c"}]
    assert check_plan(plan, {1: ("a",), 2: ("X",)}) == [
        "2: provision_text changed since the plan", "3: not current / not state-law any more"]
    assert check_plan(plan[:1], {1: ("a",)}) == []
