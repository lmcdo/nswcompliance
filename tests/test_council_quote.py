"""scripts/council_quote.py: each state, on small pages shaped like the real cases.

Real cases these stand for (2026-10-12 dry run): CoS 150954 (a ligature hid an exact
quote), NB 130236 (stored words reworded; the council's own are recovered), Ashfield
87150 (a sideways chapter banner at the copy's edge), CoS 95878 (map labels).
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import citation_proof as cp  # noqa: E402
import council_quote as cq  # noqa: E402


def stream(pages: dict[int, list[str]], margin: dict[int, list[str]] | None = None,
           skip_labels: bool = False) -> cq.Stream:
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
    return cq.Stream(SimpleNamespace(lines=lines), cased, skip_labels=skip_labels)


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
    k = st.s.find("line0")        # the stream is letters and digits only: "line 0" reads "line0"
    assert k > 0
    assert st.copy_from_label(k) is None


def test_a_short_rule_after_a_figure_title_is_still_a_rule_and_punctuated_legends_are_legends():
    assert cq.figure_kind("Figure 4d: Parking\n4.4 Garages are to be set back 1m behind the front building line.") is None
    assert cq.figure_kind("Figure 9: Site\nBuildings must not exceed 9m.") is None
    assert cq.figure_kind("Figure 12\nLegend:\nHeritage item\nExisting trees") == "figure_legend"
    assert cq.figure_kind("Figure 12\nLEGEND \u2013\nHeritage item") == "figure_legend"


def test_a_rule_under_a_legend_is_still_a_rule():
    assert cq.figure_kind("Figure 12\nLegend:\nExisting trees\n(a) Development must retain mature trees") is None


def test_a_superscript_reads_as_the_digit_the_text_layer_holds():
    """Hornsby pilot 2026-10-12: the reader writes "m²", the PDF text layer holds "m2"."""
    st = stream({1: ["The minimum private open space is 24m2 with a minimum dimension of 4m."]})
    out = cq.judge(row("The minimum private open space is 24m² with a minimum dimension of 4m."), [st])
    assert out["status"] == "exact"
    assert "24m2" in out["quote"]


def test_a_superscript_does_not_make_a_different_number_match():
    st = stream({1: ["The minimum private open space is 24m2 with a minimum dimension of 4m."]})
    out = cq.judge(row("The minimum private open space is 243 with a minimum dimension of 4m."), [st])
    assert out["status"] != "exact"


def test_a_figures_labels_coded_as_the_figure_are_not_a_rule():
    """Hornsby Figure 3.1-f as the reader returned it: one short label per line."""
    st = stream({1: ["Street tree", "Front garden", "Driveway crossing", "Building line"]})
    r = {**row("Rear boundary\n3 / 8m\nSecondary boundary\nDwelling 1\nSide boundary"), "code": "Figure 3.2"}
    out = cq.judge(r, [st])
    assert out["status"] == "not_a_control" and out["reason"] == "figure_labels"


def test_a_coded_figure_with_rule_wording_is_still_judged_as_a_rule():
    text = "Garages must be set back at least 1 metre behind the building line."
    st = stream({1: [text]})
    out = cq.judge({**row(text), "code": "Figure 4"}, [st])
    assert out["status"] == "exact"


def test_a_rule_without_a_figure_code_is_not_dropped_as_labels():
    st = stream({1: ["Street tree", "Front garden", "Driveway crossing", "Building line"]})
    out = cq.judge({**row("Street tree Front garden Driveway crossing Building line"), "code": "C3"}, [st])
    assert out["status"] == "exact"


def test_a_footnote_superscript_never_joins_a_number():
    """Cross-review 2026-10-12: "24³" (a footnote mark) must not read as "243"."""
    st = stream({1: ["The building height is not to exceed 24³ metres above existing ground level."]})
    out = cq.judge(row("The building height is not to exceed 243 metres above existing ground level."), [st])
    assert out["status"] != "exact"


def test_the_copy_keeps_the_councils_unit_superscript():
    st = stream({1: ["The minimum private open space is 24m² with a minimum dimension of 4m."]})
    out = cq.judge(row("The minimum private open space is 24m2 with a minimum dimension of 4m."), [st])
    assert out["status"] == "exact" and "24m²" in out["quote"]


def test_a_coded_figure_that_reads_as_a_sentence_is_judged_as_a_rule():
    """Cross-review 2026-10-12: no "must", but a binding sentence all the same."""
    text = "Vehicle access is prohibited from Smith Street"
    out = cq.judge({**row(text), "code": "Figure 4"}, [stream({1: [text]})])
    assert out["status"] == "exact"


def test_a_one_line_instruction_coded_as_a_figure_is_judged_as_a_rule():
    """Cross-review 2026-10-12: no listed verb, but one line of words is an instruction, not labels."""
    text = "Locate vehicle access on Smith Street"
    out = cq.judge({**row(text), "code": "Figure 4"}, [stream({1: [text]})])
    assert out["status"] != "not_a_control"


def test_labels_with_a_long_line_are_judged_as_a_rule():
    text = "Rear boundary\nLocate the garage behind the front building line of the dwelling"
    out = cq.judge({**row(text), "code": "Figure 4"}, [stream({1: text.split("\n")})])
    assert out["status"] != "not_a_control"


def test_a_blank_chapter_never_widens_to_the_whole_council(monkeypatch):
    import council_quote_db as store
    import dcp_page_repair as dpr
    import pytest
    rows = [{"id": 1, "source_chapter_key": "a"}, {"id": 2, "source_chapter_key": "b"}]
    monkeypatch.setattr(dpr, "fetch", lambda conn, council: rows)
    monkeypatch.setattr("psycopg2.connect", lambda *a, **k: type("C", (), {
        "cursor": lambda self: type("K", (), {"execute": lambda self, *a: None})(),
        "close": lambda self: None})())
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    assert store.fetch("x", None, "") == []
    assert [r["id"] for r in store.fetch("x", None, "a")] == [1]
    assert len(store.fetch("x", None, None)) == 2
    monkeypatch.setattr(sys, "argv", ["council_quote.py", "--dry-run", "--council", "x", "--chapter", " "])
    with pytest.raises(SystemExit):
        cq.main()


def test_unchecked_selects_only_null_status_rows(monkeypatch):
    import council_quote_db as store
    import dcp_page_repair as dpr
    rows = [{"id": 1, "source_chapter_key": "a"}, {"id": 2, "source_chapter_key": "a"},
            {"id": 3, "source_chapter_key": "b"}]
    seen = []

    class K:
        def execute(self, sql, params=None):
            seen.append((sql, params))

        def fetchall(self):
            return [(2,), (3,)]   # the DB says only 2 and 3 have quote_status IS NULL

    monkeypatch.setattr(dpr, "fetch", lambda conn, council: rows)
    monkeypatch.setattr("psycopg2.connect", lambda *a, **k: type("C", (), {
        "cursor": lambda self: K(), "close": lambda self: None})())
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    assert [r["id"] for r in store.fetch(None, None, None, unchecked=True)] == [2, 3]
    assert any("quote_status IS NULL" in q for q, _ in seen if q)
    assert [r["id"] for r in store.fetch(None, None, "a", unchecked=True)] == [2]
    assert len(store.fetch(None, None, None)) == 3   # without the flag nothing is filtered


def test_unchecked_with_no_rows_exits_zero_quietly(monkeypatch, tmp_path, capsys):
    import council_quote_db as store
    monkeypatch.setattr(store, "fetch", lambda *a, **k: [])
    out = tmp_path / "o.json"
    monkeypatch.setattr(sys, "argv", ["council_quote.py", "--apply", "--unchecked", "--out", str(out)])
    assert cq.main() == 0
    assert not out.exists()
    assert "unchecked rules selected: 0" in capsys.readouterr().out


# -- a lead-in and one of its items, printed apart (prove_pieces) -------------------------------------
LEAD = "C.09 A carwash bay must be provided in accordance with the following:"
ITEM = "g) Approval must be obtained from Sydney Water prior to construction of the development."
BETWEEN = ["a) The bay is to be roofed and bunded so that rain water cannot enter.",
           "b) Wash water is to drain to the sewer through a pre-treatment device."]


def test_a_lead_in_and_its_item_printed_apart_are_exact_in_the_councils_words():
    st = stream({1: [LEAD] + BETWEEN + [ITEM]})
    out = cq.judge(row(f"# 8.5.9.6 g Car parking\n\n{LEAD}\n{ITEM}"), [st])
    assert out["status"] == "exact" and out["reason"] == "pieces"
    assert out["quote"] == f"{LEAD}\n{ITEM}"          # the items between are never copied
    assert out["quote_page"] == 1


def test_an_item_on_the_next_page_is_still_proven():
    st = stream({1: [LEAD] + BETWEEN, 2: [ITEM]})
    assert cq.judge(row(f"{LEAD}\n{ITEM}"), [st])["reason"] == "pieces"


def test_an_item_printed_far_from_its_lead_in_is_not_proven():
    pages = {1: [LEAD], 2: ["unrelated filler on page 2"], 3: ["unrelated filler on page 3"], 4: [ITEM]}
    out = cq.judge(row(f"{LEAD}\n{ITEM}"), [stream(pages)])
    assert out["status"] == "unconfirmed"


def test_an_item_printed_before_its_lead_in_is_not_proven():
    out = cq.judge(row(f"{LEAD}\n{ITEM}"), [stream({1: [ITEM] + BETWEEN + [LEAD]})])
    assert out["status"] == "unconfirmed"


def test_an_item_with_a_word_the_council_did_not_print_is_not_proven():
    st = stream({1: [LEAD] + BETWEEN + [ITEM]})
    out = cq.judge(row(f"{LEAD}\n{ITEM.replace('prior to', 'before')}"), [st])
    assert out["status"] != "exact"


def test_an_item_whose_number_differs_is_not_proven():
    st = stream({1: ["C.02 The following minimum setbacks apply:"] + BETWEEN
                 + ["c) Rear setback of 6 metres for all dwellings on the site."]})
    out = cq.judge(row("C.02 The following minimum setbacks apply:\nc) Rear setback of 8 metres for all "
                       "dwellings on the site."), [st])
    assert out["status"] != "exact"


def test_two_short_lines_are_never_proven_as_pieces():
    st = stream({1: ["Objectives", "filler line one here", "Controls"], 2: ["Objectives", "Controls"]})
    assert cq.prove_pieces("Objectives\nControls", [st], __import__("council_quote_table"), 1) is None


def test_a_lead_in_on_the_page_before_the_stored_page_is_proven():
    st = stream({1: [LEAD] + BETWEEN, 2: [ITEM]})
    assert cq.judge(row(f"{LEAD}\n{ITEM}", page=2), [st])["reason"] == "pieces"


def test_pieces_printed_far_from_the_stored_page_are_not_proven():
    pages = {p: [f"unrelated filler on page {p}"] for p in range(1, 40)}
    pages[3] = [LEAD] + BETWEEN + [ITEM]
    out = cq.judge(row(f"{LEAD}\n{ITEM}", page=35), [stream(pages)])
    assert out["reason"] != "pieces"     # the older anchor path may still recover it; this check must not


def test_fragments_of_a_two_column_page_are_not_proven():
    # Ashfield 123241 as stored: each fragment is printed, the row is not one of the council's sentences
    st = stream({1: ["Heritage items are to preserve the character of buildings within the Urban",
                     "Character areas where the original fabric is to be retained and conserved.",
                     "Village."]})
    out = cq.judge(row("to preserve the character of buildings within the Urban\nretained and conserved.\nVillage."), [st])
    assert out["status"] != "exact"


def test_a_line_that_stops_mid_sentence_is_not_proven_as_a_piece():
    # Ashfield 123339 as stored: both lines printed, the second cut off mid-sentence
    st = stream({1: ["Parramatta Road streetscape.", "To improve the image, quality and amenity of",
                     "the Parramatta Road corridor."]})
    out = cq.judge(row("Parramatta Road streetscape.\nTo improve the image, quality and amenity of"), [st])
    assert out["reason"] != "pieces"


def test_a_bare_label_line_does_not_block_a_proof():
    st = stream({1: ["Applicants are required to ensure that the proposal is consistent with:", "1.", "Text one.",
                     "3.", "Roof coverage and panels number is appropriate to the scale of the building."]})
    out = cq.judge(row("Applicants are required to ensure that the proposal is consistent with:\n3.\n"
                       "Roof coverage and panels number is appropriate to the scale of the building."), [st])
    assert out["reason"] == "pieces"


HORNSBY = {5: ["Height", "a.", "Sites with the following maximum building heights under Clause 4.3",
               "should comply with the maximum number of storeys in Table 3.5.4-a.",
               "b.", "Development should not exceed the storeys shown."]}
DROPPED_LABEL = ("Height Sites with the following maximum building heights under Clause 4.3 should "
                 "comply with the maximum number of storeys in Table 3.5.4-a.")


def test_a_rule_whose_lone_label_line_was_dropped_is_proven_with_the_label_kept():
    # Hornsby 248365: the reader joined "Height" to the rule and dropped the "a." line between them.
    assert cq.judge(row(DROPPED_LABEL, page=5), [stream(HORNSBY)])["status"] == "unconfirmed"
    out = cq.judge_twice(row(DROPPED_LABEL, page=5), [stream(HORNSBY)], [stream(HORNSBY, skip_labels=True)])
    assert out["status"] == "exact" and out["reason"].endswith("+label_skipped")
    assert out["quote"].startswith("Height" + chr(10) + "a." + chr(10) + "Sites with")   # the council's text, label included


def test_a_rule_proven_as_printed_is_not_judged_again():
    stored = "a. Sites with the following maximum building heights under Clause 4.3"
    out = cq.judge_twice(row(stored, page=5), [stream(HORNSBY)], [stream(HORNSBY, skip_labels=True)])
    assert out["status"] == "exact" and "label_skipped" not in out["reason"]


@pytest.mark.parametrize("cell", ["3", "3.", "3)", "(3)"])
def test_a_number_alone_is_a_table_value_not_a_label(cell):
    # "3" or "3." alone can be a value: skipping it would let "Maximum storeys 2" pass over a printed 3.
    tbl = {1: ["Maximum storeys in the precinct", cell, "2 for sites fronting a heritage item listed in Schedule 5"]}
    stored = "Maximum storeys in the precinct 2 for sites fronting a heritage item listed in Schedule 5"
    out = cq.judge_twice(row(stored), [stream(tbl)], [stream(tbl, skip_labels=True)])
    assert out["status"] == "unconfirmed"


@pytest.mark.parametrize("cell", ["(x)", "A.", "c)"])
def test_a_lone_letter_with_no_list_beside_it_is_not_skipped(cell):
    # City of Sydney Section 6 map key: "(x)" means "brackets indicate additional height", a value,
    # not the tenth list item. With no neighbour label of the same list nearby it must stay in the search.
    page = {5: ["Height", cell] + HORNSBY[5][2:4]}
    out = cq.judge_twice(row(DROPPED_LABEL, page=5), [stream(page)], [stream(page, skip_labels=True)])
    assert out["status"] == "unconfirmed"


@pytest.mark.parametrize("text, skipped", [
    (["a.", "x", "b.", "y"], {0, 2}),
    (["(i)", "x", "(ii)"], {0, 2}),
    (["i)", "x", "j)"], {0, 2}),          # "i)" read as a letter, next to "j)"
    (["a.", "x", "(b)"], set()),          # different wrapping: not the same list
    (["a."] + ["x"] * (cq.LABEL_NEAR + 1) + ["b."], set()),   # too far apart
    (["(x)", "storeys"], set()),
])
def test_list_label_lines(text, skipped):
    assert cq.list_label_lines(text) == skipped


def test_words_not_printed_stay_unconfirmed_with_labels_skipped():
    stored = "Height Sites with the following maximum building heights must not exceed four storeys anywhere."
    out = cq.judge_twice(row(stored, page=5), [stream(HORNSBY)], [stream(HORNSBY, skip_labels=True)])
    assert out["status"] == "unconfirmed"


def test_contents_page_is_not_a_rule():
    # Hornsby Part 3 page 2, as stored and wrongly proven (row 248138)
    hornsby = ("RESIDENTIAL .......................................... 3-2\n3.1 Dwelling Houses and Dual Occupancies | 3-5\n"
               "3.1.1   Scale | 3-5\n3.1.2   Setbacks | 3-9\n3.1.3   Landscaping | 3-12\n3.1.4   Open Space | 3-13")
    assert cq.contents_kind(hornsby) == "contents_page"
    # titles only, no page numbers (row 248327)
    titles = "3.4.1   Desired Future Character\n3.4.2   Design Quality\n3.4.3   Site Requirements\n3.4.4   Height\n3.4.5   Setbacks"
    assert cq.contents_kind(titles) == "contents_page"
    # a heading in the list may say "to be"; page numbers still make it contents (Marrickville 2.21)
    leaders = ("2.21.1 Introduction ........ 2\n2.21.1.1 Objectives ........ 2\n2.21.2 Waste facilities ........ 3\n"
               "2.21.2.2 Waste related information to be submitted with a\ndevelopment application ........ 3")
    assert cq.contents_kind(leaders) == "contents_page"


def test_rules_that_look_like_lists_stay_rules():
    # Woollahra B3.2 side setback table: dotted numbers, but numbers not titles
    table = ("Side setback table for dwelling houses.\nA. Site width | B. Side setback in metres\n< 9.0 | 0.9\n"
             "9.0 - < 11.0 | 1.1\n11.0 - < 13.0 | 1.3\n13.0 - < 15.0 | 1.5\n15.0 - < 17.0 | 1.9")
    assert cq.contents_kind(table) is None
    # numbered controls with rule wording
    rules = "3.1 Buildings must not exceed 9m.\n3.2 Setbacks\n3.3 Height\n3.4 Parking\n3.5 Landscaping"
    assert cq.contents_kind(rules) is None
    # a street list (Woollahra contributory items)
    streets = "8 Manion Avenue | Inter-War flat building\n9 Manion Avenue | Toronto\n10 Manion Avenue | Greystanes\n11 Manion Avenue | flat\n12 Manion Avenue | flat"
    assert cq.contents_kind(streets) is None
    assert cq.contents_kind("3.1 Scale\n3.2 Setbacks") is None    # too short to judge


def test_standards_and_values_are_not_contents():
    # cross-review 2026-10-28: a standards schedule with dot leaders, and numbered lines carrying values
    schedule = "Maximum building height .... 9\nMinimum lot area .... 500\nMinimum frontage .... 15\nMaximum FSR .... 1\nMinimum setback .... 6"
    assert cq.contents_kind(schedule) is None
    values = ("3.1 Building height 9 metres\n3.2 Front setback 6 metres\n3.3 Site coverage 50 percent\n"
              "3.4 Landscaped area 30 percent\n3.5 Parking two spaces")
    assert cq.contents_kind(values) is None


def test_numbered_commands_are_not_contents():
    commands = ("3.1 Locate car parking behind the front building line where possible\n"
                "3.2 Provide deep soil planting along the rear boundary of the site\n"
                "3.3 Retain existing trees that are prominent streetscape features of the area\n"
                "3.4 Screen plant equipment and services from the street and neighbours\n"
                "3.5 Orient living areas and private open space towards the north")
    assert cq.contents_kind(commands) is None
