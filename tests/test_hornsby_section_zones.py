"""Hornsby Part 3: a rule's zone comes from the section its page sits in.

prior-art-checked: extends the existing tagger's config path; no other test covers page-range sections.
"""
import pytest

from enrichment.extractors.applicability_tagger import ApplicabilityTagger

DOC = "Hornsby_DCP_2024__hornsby_dcp_2024_part3_residential"
CHAPTER = "hornsby-dcp-2024-part3-residential"
READ_IN = "193ac6a451b06b2adde87867088f23cf7b19969ee0df4b0a012d38068e751492"


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, sql, params=None):
        assert "dcp_chapter_registry" in sql

    def fetchall(self):
        return self.rows


def tagger_for(on_hand=READ_IN, extracted=READ_IN):
    tagger = ApplicabilityTagger()
    tagger.load_section_versions(Cursor([(CHAPTER, on_hand, extracted)]))
    return tagger


@pytest.mark.parametrize("page,zones", [
    (7, ["R2", "R3", "R4"]), (16, ["R2", "R3", "R4"]),  # 3.1 is left on the Part's zones  # noqa: zone-codes - expected values quoted from the council's section openings
    (17, ["R3"]), (39, ["R3"]), (40, ["R3", "R4"]), (51, ["R3", "R4"]), (52, ["R4"]), (82, ["R4"]),  # noqa: zone-codes - expected values quoted from the council's section openings
    (83, ["R2", "R3", "R4"]), (101, ["R2", "R3", "R4"]),  # 3.5 unchanged until the seniors area's zone is known  # noqa: zone-codes - expected values quoted from the council's section openings
    (None, ["R2", "R3", "R4"]),  # no page: never guess a section  # noqa: zone-codes - expected values quoted from the council's section openings
])
def test_zone_follows_the_section_page(page, zones):
    got_zones, got_types, source = tagger_for().tag_with_provenance("A rule.", DOC, pdf_page=page)
    assert sorted(got_zones) == zones
    assert got_types == ["ALL"] and source["dev_type_source"] == "config_declined"


def test_narrow_only_never_writes_a_row_that_gains_a_zone():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from retag_applicability_slug_docids import only_narrowing

    def row(i, new_z, old_z, new_d=("ALL",), old_d=("ALL",)):
        return (i, list(new_z), list(new_d), "config_specific", "config_declined", list(old_z), list(old_d))

    plan = [row(1, ["R4"], ["R2", "R3", "R4"]), row(2, ["R2", "R3", "R4"], ["R4"]),  # noqa: zone-codes - expected values quoted from the council's section openings
            row(3, ["R3"], ["R4"]), row(4, ["R4"], ["ALL"]), row(5, ["ALL"], ["R4"]),  # noqa: zone-codes - expected values quoted from the council's section openings
            row(6, ["R4"], ["R2", "R4"], ["ALL"], ["dwelling_house"])]  # noqa: zone-codes - expected values quoted from the council's section openings
    assert [r[0] for r in only_narrowing(plan)] == [1, 4]


@pytest.mark.parametrize("on_hand,extracted", [("new", READ_IN), (READ_IN, "old"), ("new", "new"), (None, None)])
def test_another_file_version_keeps_the_chapter_zones_and_says_so(on_hand, extracted, caplog):
    tagger = tagger_for(on_hand, extracted)
    zones, _types, _source = tagger.tag_with_provenance("A rule.", DOC, pdf_page=60)
    assert sorted(zones) == ["R2", "R3", "R4"]  # noqa: zone-codes - the Part's own zones
    assert tagger.section_version_errors and "SECTION ZONES NOT APPLIED" in caplog.text


def test_versions_not_loaded_keeps_the_chapter_zones_and_says_so(caplog):
    tagger = ApplicabilityTagger()
    zones, _types, _source = tagger.tag_with_provenance("A rule.", DOC, pdf_page=60)
    assert sorted(zones) == ["R2", "R3", "R4"]  # noqa: zone-codes - the Part's own zones
    assert "SECTION ZONES NOT APPLIED" in caplog.text


def test_dict_rows_load_like_tuple_rows():
    tagger = ApplicabilityTagger()
    tagger.load_section_versions(Cursor([{"chapter_key": CHAPTER, "content_hash": READ_IN,
                                          "provisions_extracted_from_hash": READ_IN}]))
    zones, _types, _source = tagger.tag_with_provenance("A rule.", DOC, pdf_page=60)
    assert zones == ["R4"]  # noqa: zone-codes - section 3.4's own words


def test_retag_reads_current_rows_only():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "scripts" / "retag_applicability_slug_docids.py").read_text(
        encoding="utf-8")
    assert "WHERE is_current AND source_council = ANY(%s)" in source
