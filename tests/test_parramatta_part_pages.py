"""Parramatta DCP 2023: the row's PDF page names its Part (the plan's own cover pages), and the page outranks a
heading code that names another Part. prior-art-checked: extends the part_pages mechanism of
tests/test_northern_beaches_part_pages.py / test_cumberland_part_pages.py to a numbered-Part plan."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

DOC = "Parramatta_DCP_2023_(Amendment_4)__parramatta_dcp_2023_full"
PAGES = json.loads((ROOT / "enrichment/config/parramatta_part_pages.json").read_text(encoding="utf-8"))


def _tag(text, page):
    return ApplicabilityTagger().tag_with_provenance(text, DOC, part="unknown", pdf_page=page)


def test_ranges_are_contiguous_and_start_on_the_cover_pages():
    rs = PAGES["ranges"]
    assert [r["part"] for r in rs] == [str(n) for n in range(1, 13)]
    for a, b in zip(rs, rs[1:]):
        assert b["first_page"] == a["last_page"] + 1
    assert {r["part"]: r["first_page"] for r in rs} == {k: v for k, v in PAGES["cover_pages"].items()}


def test_a_heading_from_another_part_takes_the_pages_part():
    # An appendix row (Part 12 pages) headed "8.0" used to be scoped as Part 8, a named-area Part.
    on_appendix = _tag("# 8.0\n\nAppendix text.", 1530)
    as_part12 = _tag("# 12.1\n\nAppendix text.", 1530)
    as_part8 = _tag("# 8.2.3\n\nGranville Local Centre control.", 500)
    assert on_appendix == as_part12
    assert on_appendix != as_part8


def test_a_heading_inside_the_pages_part_is_kept():
    # "8.2.3" on a Part 8 page keeps its own code.
    assert _tag("# 8.2.3\n\nGranville control.", 500) == _tag("# 8.2.3\n\nGranville control.", None)


def test_a_row_with_no_heading_code_keeps_its_text_reading():
    # A Part entry's ALL would overwrite what the text says and widen the rule to every project.
    assert _tag("Retail, cafe and restaurant tenancies must face the street.", 500)[2]["dev_type_source"] != "config_all"


def test_a_bare_number_heading_keeps_its_old_handling():
    # "# 3 Metre Wide Lanes" on a Part 8 page is a misread, not Part 3; it is not re-pointed to Part 8 either.
    text = "# 3 Metre Wide Lanes\n\nC.11 Where development adjoins a lane."
    assert _tag(text, 500) == _tag(text, None)


def test_title_and_contents_pages_stay_unresolved():
    assert _tag("Development must not exceed the height shown.", 2)[2]["dev_type_source"] == "no_config"
