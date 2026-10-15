"""DQ-33: nine ingested documents in four councils had no development-type config.

2,421 served rows carried v2_dev_type_source='no_config' (measured 2026-10-15):
northern_beaches 1,518, marrickville 535, ashfield 198, cumberland 170. Same shape as
the Leichhardt repair (test_leichhardt_documents_all_resolve.py): an unmatched document
falls through to ALL because nothing matched, not because anything decided it.

Each document now resolves to a declared entry whose scope is quoted from the plan.
The rule these tests hold: a resolved row is never `no_config`, no entry narrows what
the plan did not narrow, and Cumberland -- five sub-Parts, five scopes, one document --
is DECLINED rather than collapsed to ALL or to one sub-Part's list.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from enrichment.config.ashfield_config import ASHFIELD_CONFIG  # noqa: E402
from enrichment.config.marrickville_config import MARRICKVILLE_CONFIG  # noqa: E402
from enrichment.extractors.applicability_tagger import ApplicabilityTagger  # noqa: E402

MARRICKVILLE_SLUGS = {
    "part2_s20_tree_management": "2_20",
    "part2_s21_site_facilities_waste": "2_21",
    "part2_s22_flood_management": "2_22",
    "part2_s23_acid_sulfate": "2_23",
    "part2_s24_contaminated_land": "2_24",
    "part2_s26_entertainment_precincts": "2_26",
}
NB_DOC = "Warringah_DCP_2011__warringah_dcp_2011_full"


@pytest.fixture(scope="module")
def tagger():
    return ApplicabilityTagger()


class TestMarrickville:
    @pytest.mark.parametrize("slug,key", sorted(MARRICKVILLE_SLUGS.items()))
    def test_resolves_to_a_declared_key(self, tagger, slug, key):
        assert tagger._marrickville_slug_key(f"Marrickville_DCP_2011__{slug}") == ("part", key)
        assert key in MARRICKVILLE_CONFIG["parts"]

    @pytest.mark.parametrize("slug", sorted(MARRICKVILLE_SLUGS))
    def test_no_row_comes_back_no_config(self, tagger, slug):
        _z, _d, prov = tagger.tag_with_provenance("Any control.", f"Marrickville_DCP_2011__{slug}")
        assert "no_config" not in prov.values(), prov

    def test_entertainment_precincts_are_declined_not_narrowed(self, tagger):
        _z, d, prov = tagger.tag_with_provenance(
            "# 2.26 Application", "Marrickville_DCP_2011__part2_s26_entertainment_precincts")
        assert d == ["ALL"] and prov["dev_type_source"] == "config_declined"

    @pytest.mark.parametrize("key", sorted(MARRICKVILLE_SLUGS.values()))
    def test_every_new_key_carries_its_quote(self, key):
        ev = MARRICKVILLE_CONFIG["parts"][key]["scope_evidence"]
        for k in ("applicable_zones", "applicable_dev_types"):
            assert len(ev[k]) > 80 and "PDF p" in ev[k], (key, k)


class TestAshfield:
    def test_haberfield_resolves(self, tagger):
        doc = "Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield"
        assert tagger._ashfield_slug_key(doc) == ("chapter", "Chapter E2")
        assert "Chapter E2" in ASHFIELD_CONFIG["chapters"]
        _z, d, prov = tagger.tag_with_provenance("# 2.2 Haberfield", doc)
        assert d == ["ALL"] and prov["dev_type_source"] == "config_all"

    def test_e1_still_resolves_to_e1(self, tagger):
        doc = "Inner_West_Ashfield_DCP_2016__chapter_e1_heritage"
        assert tagger._ashfield_slug_key(doc) == ("chapter", "Chapter E1")
