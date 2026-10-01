"""A repeated ref must not silently overwrite the provision that had it.

`diff_provisions` built its new-side map with a plain `new_provisions[ref] = ...`,
so two extracted sections resolving to the same ref left only the later one. The
earlier provision reached neither `added`, `changed` nor `removed`, and `total_new`
counted the survivors, so nothing downstream could notice.

Measured 2026-10-02 on city_of_sydney, re-read from the 1 Oct PDFs: `schedules`
emitted 605 provisions and 451 reached the review queue; `section-3-general-
provisions` emitted 1,464 and 1,239 reached it. 379 provisions disappeared in one
run, across two chapters.

The cause is that a clause letter is not unique inside a section. Schedules 7.4
"Transport Impact Study requirements" prints a list (a)-(o), and a "Pedestrians"
sub-heading inside the same section restarts its own (a)(b)(c). Both resolve to
`..._7_4 (a)`. The later list won, so the council's real 7.4(b) ("The ability of the
public transport network to service the site in the peak and off peak and weekend
periods") and 7.4(c) ("Mode share targets") are absent from the extraction while
their keys carry another list's text. Both strings are plainly printed on PDF page
39 and appear nowhere in the 2,069 queued rows.
"""
import os
import sys
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
for _k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY",
           "R2_BUCKET_NAME", "R2_ENDPOINT_URL", "R2_PUBLIC_URL"):
    os.environ.setdefault(_k, "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
_STUBS = ("boto3", "botocore", "pdfplumber", "psycopg2", "dotenv",
          "enrichment", "enrichment.pipeline")
_saved = {k: sys.modules.get(k) for k in _STUBS}
for _k in _STUBS:
    sys.modules[_k] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()
try:
    from dcp_extract_changed import diff_provisions  # noqa: E402
finally:
    for _k, _v in _saved.items():
        if _v is None:
            sys.modules.pop(_k, None)
        else:
            sys.modules[_k] = _v

DOC = "Sydney_DCP_2012__schedules"


class _FakeCursor:
    """Minimal cursor: diff_provisions does one execute() + fetchall()."""

    def __init__(self, old_rows):
        self._rows = old_rows

    def execute(self, *a, **k):
        return None

    def fetchall(self):
        return self._rows


def _section(number, content, page=1):
    return {"section_number": number, "section_title": "", "content": content,
            "tables": [], "page_start": page, "page_end": page, "pages": [page]}


def _diff(sections, old_rows=()):
    return diff_provisions(sections, "city_of_sydney", "schedules", DOC,
                           _FakeCursor(list(old_rows)))


def _refs(result):
    return {r["ref_number"] for r in result["added"]}


class TestARepeatedRefKeepsBothProvisions:
    def test_the_real_shape_both_clauses_survive(self):
        """7.4 (a) twice, different text: the council's own words, both kept."""
        main = ("The accessibility of the site by a range of transport modes "
                "including car, public transport, walking and cycling;")
        pedestrians = ("identification of major pedestrian routes and existing "
                       "pedestrian desire lines;")
        res = _diff([_section("7.4 (a)", main, page=39),
                     _section("7.4 (a)", pedestrians, page=41)])

        assert res["total_new"] == 2, "a repeated ref dropped a provision"
        texts = " ".join(r["new_text"] for r in res["added"])
        assert "accessibility of the site" in texts
        assert "major pedestrian routes" in texts

    def test_the_second_is_suffixed_not_overwritten(self):
        res = _diff([_section("7.4 (a)", "first clause text here", page=39),
                     _section("7.4 (a)", "a different second clause", page=41)])
        assert _refs(res) == {f"{DOC}__7_4 (a)", f"{DOC}__7_4 (a)~2"}

    def test_three_provisions_on_one_ref(self):
        res = _diff([_section("7.4 (a)", "alpha text one", page=1),
                     _section("7.4 (a)", "beta text two", page=2),
                     _section("7.4 (a)", "gamma text three", page=3)])
        assert res["total_new"] == 3
        assert _refs(res) == {f"{DOC}__7_4 (a)",
                              f"{DOC}__7_4 (a)~2",
                              f"{DOC}__7_4 (a)~3"}

    def test_identical_text_is_still_collapsed(self):
        """The same clause read twice is a duplicate, not two provisions.

        Suffixing it would invent a provision the document does not contain, which
        is the opposite failure and just as wrong.
        """
        same = "The same clause text read twice by the reader"
        res = _diff([_section("7.4 (a)", same, page=1),
                     _section("7.4 (a)", same, page=1)])
        assert res["total_new"] == 1
        assert _refs(res) == {f"{DOC}__7_4 (a)"}

    def test_whitespace_only_difference_is_the_same_clause(self):
        res = _diff([_section("7.4 (a)", "one   clause  text", page=1),
                     _section("7.4 (a)", "one clause text", page=1)])
        assert res["total_new"] == 1

    def test_distinct_refs_are_untouched(self):
        res = _diff([_section("7.4 (a)", "first", page=1),
                     _section("7.4 (b)", "second", page=1)])
        assert _refs(res) == {f"{DOC}__7_4 (a)", f"{DOC}__7_4 (b)"}


class TestEveryNewProvisionIsAccountedFor:
    """total_new == unchanged + changed + renumbered + added, always.

    An identity, not a heuristic: a new ref is either matched (unchanged/changed),
    fuzzy-matched to an old ref (renumbered), or added. There is no fourth door, so
    a shortfall means a provision was dropped without a trace.
    """

    @staticmethod
    def _accounted(res):
        return (res["unchanged_count"] + len(res["changed"])
                + len(res["renumbered"]) + len(res["added"]))

    def test_holds_with_duplicate_refs(self):
        res = _diff([_section("7.4 (a)", "first clause text here", page=1),
                     _section("7.4 (a)", "a different second clause", page=2)])
        assert self._accounted(res) == res["total_new"] == 2

    def test_holds_for_all_added(self):
        res = _diff([_section("1.1", "alpha text"), _section("1.2", "beta text")])
        assert self._accounted(res) == res["total_new"] == 2

    def test_holds_with_an_unchanged_provision(self):
        res = _diff([_section("1.1", "alpha text")],
                    old_rows=[(f"{DOC}__1_1", "# 1.1\n\nalpha text", 1)])
        assert self._accounted(res) == res["total_new"] == 1

    def test_holds_when_a_provision_is_removed(self):
        """A removal is an OLD-side outcome, so it must not enter the identity."""
        res = _diff([_section("1.1", "alpha text")],
                    old_rows=[(f"{DOC}__9_9", "# 9.9\n\nsomething else entirely", 1)])
        assert res["removed"], "expected the orphaned old provision to be removed"
        assert self._accounted(res) == res["total_new"] == 1

class TestTheEmittedVsKeptGuardRefuses:
    """Force the real guard to fail, per feedback-detect-a-guard-by-forcing-its-failure.

    The guard that catches the original defect is the emitted-vs-kept equality where
    the new-side map is built, NOT the door identity above — that one held perfectly
    while 379 provisions were missing, because the overwrite shrank the map before
    any count was taken. So this forces the emitted-vs-kept one specifically.

    `build_ref_number` is monkeypatched to return a constant, which reproduces the
    defect exactly: every section collides on one ref. With the fix in place the
    sections are suffixed apart and the count reconciles, so to make the guard fire
    the suffixing has to be disabled too — done by making `_normalize_for_diff`
    claim every text is identical, which sends each collision down the
    collapse-as-duplicate path while `collapsed_duplicates` still counts it. The
    guard must therefore stay SILENT here (the collapse is accounted), which is the
    honest result and is asserted as such.
    """

    def test_collapsed_duplicates_are_counted_so_the_equality_still_holds(self):
        """One ref, all texts identical: 1 kept + 2 collapsed == 3 emitted.

        Both stubs are needed. A constant ref alone makes them collide, and
        identical text alone changes nothing while the refs differ — it is the
        combination that sends every section down the collapse path. If the
        collapse were not counted, the emitted-vs-kept guard would raise here.
        """
        import dcp_extract_changed as mod

        real_build, real_norm = mod.build_ref_number, mod._normalize_for_diff
        mod.build_ref_number = lambda doc, num: f"{doc}__same"
        mod._normalize_for_diff = lambda _t: "same"
        try:
            res = _diff([_section("1.1", "alpha"), _section("1.2", "beta"),
                         _section("1.3", "gamma")])
            assert res["total_new"] == 1
        finally:
            mod.build_ref_number, mod._normalize_for_diff = real_build, real_norm

    def test_a_constant_ref_with_differing_text_keeps_every_section(self):
        """The defect's exact shape: every section collides on one ref.

        Before the fix this kept ONE provision out of three and reported
        total_new = 1 with every downstream count agreeing. Now all three survive
        under suffixed refs and the emitted-vs-kept equality reconciles.

        The guard cannot be forced to fire at runtime — given the code, every
        section is either kept or counted as collapsed, which is the property it
        asserts. It is forced by mutating the source instead; see the QA report's
        observed_red.
        """
        import dcp_extract_changed as mod

        real_build = mod.build_ref_number
        mod.build_ref_number = lambda doc, num: f"{doc}__same"
        try:
            res = _diff([_section("1.1", "alpha text one"),
                         _section("1.2", "beta text two"),
                         _section("1.3", "gamma text three")])
            assert res["total_new"] == 3, "a colliding ref dropped a provision"
            assert _refs(res) == {f"{DOC}__same",
                                  f"{DOC}__same~2",
                                  f"{DOC}__same~3"}
        finally:
            mod.build_ref_number = real_build
