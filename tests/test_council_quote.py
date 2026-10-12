"""scripts/council_quote.py: each state, on small pages shaped like the real cases.

Real cases these stand for (2026-10-12 dry run): CoS 150954 (a ligature hid an exact
quote), NB 130236 (stored words reworded; the council's own are recovered), Ashfield
87150 (a sideways chapter banner at the copy's edge), CoS 95878 (map labels).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import citation_proof as cp  # noqa: E402
import council_quote as cq  # noqa: E402


def stream(pages: dict[int, list[str]], margin: dict[int, list[str]] | None = None) -> cq.Stream:
    """A one-reading stream: lines as printed (cased); the cache holds them lowercased.
    `margin` lines are in the PDF but dropped from the reading (footers, page numbers)."""
    lines, cased = [], {}
    for page, texts in (margin or {}).items():
        for n, t in enumerate(texts):
            cased[(page, 800.0 + 12 * n, 72.0, t.lower())] = t
    for page, texts in pages.items():
        for n, t in enumerate(texts):
            ln = cp.Line(page, 100.0 + 12 * n, 72.0, t.strip().lower())
            lines.append(ln)
            cased[(ln.page, ln.y, ln.x, ln.text)] = t.strip()
    return cq.Stream(SimpleNamespace(lines=lines), cased)


def row(text: str, page: int = 1, rid: int = 1) -> dict:
    return {"id": rid, "source_council": "x", "pdf_page": page, "page_check": "on_page", "provision_text": text}


def test_exact_keeps_the_councils_casing_and_reads_through_a_ligature():
    st = stream({1: ["C3 Fences", "Front fences are not to exceed 1.2m in height and must be",
                     "of open construction. Speciﬁcations are in Appendix A."]})
    out = cq.judge(row("front fences are not to exceed 1.2m in height and must be of open "
                       "construction. Specifications are in Appendix A."), [st])
    assert out["status"] == "exact"
    assert out["quote"] == ("Front fences are not to exceed 1.2m in height and must be\n"
                            "of open construction. Specifications are in Appendix A.")


def test_reworded_middle_is_recovered_in_the_councils_words():
    council = ["A single integrated bus interchange for the site is to be provided.",
               "The interchange is to be capable of accommodating both the existing local",
               "and commuter bus networks and growth in the number of bus services to the Mall.",
               "The indicative integrated bus interchange zone is illustrated in Figure 11."]
    stored = ("A single integrated bus interchange for the site is to be provided. It is to "
              "accommodate the existing local and commuter bus networks and growth in the number "
              "of bus services to the Mall. The indicative integrated bus interchange zone is "
              "illustrated in Figure 11.")
    out = cq.judge(row(stored), [stream({1: council})])
    assert out["status"] == "recovered" and out["reason"] == "anchors"
    assert "capable of accommodating both" in out["quote"]
    assert "It is to accommodate" not in out["quote"]


def test_running_banner_is_trimmed_from_the_copy_edge():
    banner = "Chapter F - Development Category Guidelines"
    pages = {p: [banner, f"filler text number {p} on this page only"] for p in range(2, 8)}
    pages[1] = [banner, "Minimum landscaped area complies with the table below and applies",
                "to heritage items within conservation areas."]
    stored = (banner + " Minimum landscaped area complies with the table below and applies to "
              "heritage items within conservation areas. 2016")
    out = cq.judge(row(stored), [stream(pages, margin={1: ["Comprehensive Inner West DCP 2016"]})])
    assert out["status"] == "recovered"
    assert not out["quote"].startswith("Chapter F")
    assert out["quote"].startswith("Minimum landscaped area")


def test_values_cut_from_the_end_are_unconfirmed_not_recovered():
    council = ["Space for small to medium scale exhibitions ideally at ground floor with open",
               "space, uninterrupted walls, high ceilings and no direct sunlight on exhibitions.",
               "Floor space", "Capacity", "Office", "80-1000m2", "300 people", "15-50m2"]
    stored = ("Space for small to medium scale exhibitions ideally at ground floor with open space, "
              "uninterrupted walls, high ceilings and no direct sunlight on exhibitions. Floor space: "
              "80-1000m2. Capacity: 300 people. Office/Admin: Office 15-50m2.")
    out = cq.judge(row(stored), [stream({1: council})])
    assert out["status"] == "unconfirmed" and out["reason"] == "values_cut"
    assert "300" in out["lost_numbers"]


def test_map_labels_are_not_a_control():
    labels = " ".join(["K", "E", "N", "S T", "U S", "S T", "DRUITT", "PLACE", "E", "E", "T", "R",
                       "S", "X", "4 STOREYS", "R E E", "S U S", "T", "15m", "3m", "E", "N"])
    out = cq.judge(row(labels), [stream({1: ["unrelated text"]})])
    assert out["status"] == "not_a_control" and out["reason"] == "map_labels"


def test_short_quote_printed_in_many_places_is_unconfirmed():
    st = stream({1: ["Maximum 9m"], 2: ["Maximum 9m"]})
    out = cq.judge(row("Maximum 9m", page=3), [st])
    assert out["status"] == "unconfirmed" and out["reason"] == "too_short_many_places"


def test_short_quote_on_its_own_page_is_exact():
    st = stream({1: ["Maximum 9m"], 2: ["Maximum 9m"]})
    out = cq.judge(row("Maximum 9m", page=2), [st])
    assert out["status"] == "exact" and out["quote_page"] == 2


def test_words_not_printed_are_unconfirmed_not_recovered():
    st = stream({1: ["Something else entirely about drainage and stormwater detention tanks."]})
    out = cq.judge(row("Front fences are not to exceed 1.2m in height along the primary street frontage."), [st])
    assert out["status"] == "unconfirmed" and out["reason"] == "not_found"
    assert "quote" not in out


def test_label_bounded_copy_stops_at_the_next_label_of_the_same_kind():
    st = stream({1: ["(a)", "Side setbacks are to be clear of obstructions to allow views between",
                     "buildings and landscaping.", "(b)", "Rear setbacks are a minimum of 6m."]})
    # opening printed; the stored ending was invented, so no closing anchor exists
    stored = "Side setbacks are to be clear of obstructions to allow views between buildings and landscaping as shown."
    out = cq.judge(row(stored), [st])
    # "as shown" is not printed and is not page furniture: cutting it is not a copy
    assert out["status"] == "unconfirmed" and out["reason"] == "words_cut"
    # the label path itself: from "(a)" to before "(b)", never past it
    text, page = st.copy_from_label(st.s.find("sidesetbacks"))
    assert text == ("(a)\nSide setbacks are to be clear of obstructions to allow views between\n"
                    "buildings and landscaping.") and page == 1


def test_label_kind_reads_roman_before_alpha_and_codes_by_prefix():
    assert cq.label_kind("(i) text")[0] == "paren_roman"
    assert cq.label_kind("(c) text")[0] == "paren_alpha"
    assert cq.label_kind("C3 Fences") == cq.label_kind("C12 Walls")
    assert cq.label_kind("C3 Fences") != cq.label_kind("O1 Objective")
    assert cq.label_kind("2.1 Heading") == cq.label_kind("4.7 Other")
    assert cq.label_kind("2.1 Heading") != cq.label_kind("2.1.3 Deeper")
    assert cq.label_kind("Ordinary sentence") is None


def test_oversized_row_is_unconfirmed_even_when_printed_word_for_word():
    text = " ".join(f"Control {n}: buildings are to be set back from the boundary." for n in range(60))
    st = stream({1: [text]})
    out = cq.judge(row(text), [st])
    assert out["status"] == "unconfirmed" and out["reason"] == "oversized"


def test_line_without_its_printed_casing_is_never_passed_off_as_the_councils():
    st = stream({1: ["Front fences are not to exceed 1.2m in height and must be",
                     "of open construction along the primary street."]})
    st.uncased = {1}       # the second line's printed text could not be re-read
    out = cq.judge(row("Front fences are not to exceed 1.2m in height and must be of open "
                       "construction along the primary street."), [st])
    assert out["status"] == "unconfirmed" and out["reason"] == "casing_unread"


def test_a_rule_that_starts_with_a_figure_title_is_still_a_rule():
    body = ("Figure 4d: Parking and vehicle access\nGeneral\n4.4 Where a setback applies, buildings are to "
            "provide articulated and varied facades that do not present a blank wall to the street.")
    assert cq.figure_kind(body) is None
    assert cq.figure_kind("Figure 14L.3-1:\nBuilding Setbacks Plan\nLegend\n2m Front Setback") == "figure_legend"
    assert cq.figure_kind("Figure 12: Setback Type R3") == "figure_caption"


def test_label_copy_cut_off_by_the_line_cap_is_refused():
    lines = ["(a)"] + [f"line {n} of a very long control that never reaches another label" for n in range(60)]
    st = stream({1: lines})
    assert st.copy_from_label(st.s.find("line0")) is None
