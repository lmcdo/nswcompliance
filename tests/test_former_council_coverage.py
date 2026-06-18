"""GATE-coverage: detect_former_council resolves every onboarded LGA's DCP data.

Regression for the stale-allow-list bug found on 17 Corden Ave, Five Dock: Canada Bay
(and ~13 other LGAs) had complete current rows in dcp_setback_controls but were absent
from the hand-maintained ZONE_EPI_TO_LGA_SLUG map, so detect_former_council returned None
and the brief silently served no DCP setbacks/site-coverage for them.

The fix derives the slug from the EPI name and validates it against DCP_ONBOARDED_SLUGS.
These tests pin: (1) the previously-unreachable LGAs now resolve, (2) the completeness
gate still blocks an un-onboarded LGA, (3) special cases (Sydney, Inner West) hold, and
(4) a non-LEP string cannot accidentally resolve.
"""
import pytest

from scripts.generate_conveyancing_report import (
    detect_former_council,
    _slug_from_epi,
    DCP_ONBOARDED_SLUGS,
)


# (epi_name, expected_slug) — the regression set: LGAs that were missing from the old map.
PREVIOUSLY_UNREACHABLE = [
    ("Canada Bay Local Environmental Plan 2013", "canada_bay"),
    ("Bayside Local Environmental Plan 2021", "bayside"),
    ("Burwood Local Environmental Plan 2012", "burwood"),
    ("Camden Local Environmental Plan 2010", "camden"),
    ("Cumberland Local Environmental Plan 2021", "cumberland"),
    ("Fairfield Local Environmental Plan 2013", "fairfield"),
    ("Georges River Local Environmental Plan 2021", "georges_river"),
    ("Parramatta Local Environmental Plan 2023", "parramatta"),
    ("Randwick Local Environmental Plan 2012", "randwick"),
    ("Ryde Local Environmental Plan 2014", "ryde"),
    ("Strathfield Local Environmental Plan 2012", "strathfield"),
    ("Sutherland Shire Local Environmental Plan 2015", "sutherland_shire"),
    ("The Hills Local Environmental Plan 2019", "the_hills"),
]


@pytest.mark.parametrize("epi,expected", PREVIOUSLY_UNREACHABLE)
def test_previously_unreachable_lgas_now_resolve(epi, expected):
    # address is only used for Inner West disambiguation; irrelevant for these LGAs.
    assert detect_former_council("1 Example St, Somewhere NSW", epi) == expected


@pytest.mark.parametrize("epi,expected", PREVIOUSLY_UNREACHABLE)
def test_every_regression_slug_is_in_the_onboarded_gate(epi, expected):
    # The fix only works because the derived slug is whitelisted.
    assert expected in DCP_ONBOARDED_SLUGS


def test_canada_bay_real_string_is_the_17_corden_case():
    # The exact EPI string the portal returned for 17 Corden Ave, Five Dock.
    assert detect_former_council(
        "17 Corden Ave, Five Dock NSW 2046",
        "Canada Bay Local Environmental Plan 2013",
    ) == "canada_bay"


def test_city_of_sydney_special_case_maps_via_explicit_entry():
    # "Sydney" slugifies to "sydney" (not "city_of_sydney"), so it must come from the
    # explicit map override, not the generic deriver.
    assert _slug_from_epi("Sydney Local Environmental Plan 2012") == "sydney"
    assert detect_former_council("1 George St, Sydney NSW", "Sydney Local Environmental Plan 2012") == "city_of_sydney"


def test_unonboarded_lga_still_returns_none():
    # An LGA with a valid-looking EPI but no complete DCP data must stay gated.
    assert _slug_from_epi("Wollongong Local Environmental Plan 2009") == "wollongong"
    assert "wollongong" not in DCP_ONBOARDED_SLUGS
    assert detect_former_council("1 Crown St, Wollongong NSW", "Wollongong Local Environmental Plan 2009") is None


def test_non_lep_string_does_not_resolve():
    # A string with no instrument phrase must not slugify into a false positive.
    assert _slug_from_epi("Canada Bay") is None
    assert detect_former_council("somewhere", "Canada Bay") is None
    assert _slug_from_epi("") is None


def test_inner_west_still_disambiguates_by_suburb():
    # The Inner West special path (suburb -> former council) must be unaffected.
    assert detect_former_council("12 Dalhousie St, Haberfield NSW 2045",
                                 "Inner West Local Environmental Plan 2022") == "ashfield"


def test_lep_abbreviation_form_also_resolves():
    # Some portal responses use the short "LEP" form.
    assert _slug_from_epi("Sutherland Shire LEP 2015") == "sutherland_shire"
    assert detect_former_council("1 Test St", "Sutherland Shire LEP 2015") == "sutherland_shire"
