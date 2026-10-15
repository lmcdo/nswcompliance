"""Cumberland DCP Part B (Residential Zones) -- applicability by sub-Part.

DQ-105 / DQ-107: Part B is ONE registered document holding FIVE sub-Parts (the first through the fifth). Each has its own
"1.1 Land to which this Part applies" naming different development types, and their section codes collide (every
sub-Part has a 1.1 and a 2.4), so neither document_id nor the section code can tell them apart. The row's PDF page
can: each sub-Part opens with a divider page, and ``cumberland_part_pages.json`` records the page range each owns.
The tagger consults ``part_pages`` only when the row's heading names no Part; a divider page, the cover/contents
pages and anything outside every range stay unresolved (no_config) -- never a guess.

Zones: no 1.1 clause names a zone. B1 1.1 says "land zoned Residential" and the document is titled "Development in
Residential Zones"; Cumberland's residential zones in lep_zone_coverage are exactly the three the rows already carry. That is the value
these rows already carried, so it is kept.
"""
import json
from pathlib import Path


def _load_part_pages() -> list:
    with open(Path(__file__).with_name("cumberland_part_pages.json"), encoding="utf-8") as fh:
        return json.load(fh)["ranges"]


_ZONES = ("Zones kept as the rows already carry them: no 1.1 clause names a zone, B1 1.1 says 'land zoned "
          "Residential', the document is 'Development in Residential Zones', and Cumberland's residential zones "
          "in lep_zone_coverage are R2, R3, R4. ")  # noqa: zone-codes
_RESIDENTIAL_ZONES = ["R2", "R3", "R4"]  # noqa: zone-codes - Cumberland LEP 2021 'Residential' zones per lep_zone_coverage; see _ZONES

CUMBERLAND_CONFIG: dict = {
    "part_pages": _load_part_pages(),
    "parts": {
        "B1": {
            "applicable_zones": _RESIDENTIAL_ZONES,
            "applicable_dev_types": ["dwelling_house", "secondary_dwelling"],
            "scope_evidence": {
                "applicable_zones": _ZONES + "B1 1.1 (PDF p8) verbatim: 'This Part applies to development types "
                    "detailed within this Part within land zoned Residential under Cumberland Local Environmental "
                    "Plan 2021.'",
                "applicable_dev_types":
                    "B1 1.1 (PDF p8) verbatim: 'This Part applies to development types detailed within this Part "
                    "within land zoned Residential under Cumberland Local Environmental Plan 2021.' -- 1.1 names "
                    "no type itself; the types are named by the very next clause 1.2 (PDF p8) verbatim: 'This Part "
                    "is intended to guide the assessment of the development of a dwelling house, secondary "
                    "dwelling and associated outbuildings.'",
            },
        },
        "B2": {
            "applicable_zones": _RESIDENTIAL_ZONES,
            "applicable_dev_types": ["dual_occupancy", "multi_dwelling_housing"],
            "scope_evidence": {
                "applicable_zones": _ZONES + "NOT applied: B2 1.2 (PDF p31) says the Part guides dual occupancy "
                    "'located with the R2 and R3 zones'; that is a purpose sentence, not the application clause, "  # noqa: zone-codes
                    "and narrowing on it is left to a person.",
                "applicable_dev_types":
                    "B2 1.1 (PDF p31) verbatim: 'This Part applies to low rise dual occupancy development under "
                    "the Cumberland Local Environment Plan 2021.' Note B2 2.1 (PDF p31) goes on to say all low "
                    "rise medium density development is assessed against the Low Rise Housing Diversity Design "
                    "Guide, 'including: dual occupancies; manor houses ...; and multi-dwelling housing'. Both are "
                    "kept (2026-10-16): narrowing to 1.1 alone would hide B2 rules from multi-dwelling housing "
                    "that 2.1 brings in, and a hidden rule is the worse error.",
            },
        },
        "B3": {
            "applicable_zones": _RESIDENTIAL_ZONES,
            "applicable_dev_types": ["residential_flat_building"],
            "scope_evidence": {
                "applicable_zones": _ZONES + "B3 1.1 (PDF p39) names no zone.",
                "applicable_dev_types":
                    "B3 1.1 (PDF p39) verbatim: 'This Part applies to residential flat building development "
                    "under the Cumberland Local Environment Plan 2021.'",
            },
        },
        "B4": {
            "applicable_zones": _RESIDENTIAL_ZONES,
            "applicable_dev_types": ["boarding_house"],
            "scope_evidence": {
                "applicable_zones": _ZONES + "B4 1.1 (PDF p45) names no zone.",
                "applicable_dev_types":
                    "B4 1.1 (PDF p45) verbatim: 'This Part applies to development of land for the purposes of a "
                    "boarding house under the Cumberland Local Environmental Plan 2021.'",
            },
        },
        "B5": {
            "applicable_zones": _RESIDENTIAL_ZONES,
            # 'all residential development types except for single dwelling house': the vocabulary has no
            # "all but X", so the residential use types of devTypeHierarchy.ts are listed WITHOUT dwelling_house.
            "applicable_dev_types": ["secondary_dwelling", "dual_occupancy", "multi_dwelling_housing",
                                     "residential_flat_building", "boarding_house", "shop_top_housing"],
            "scope_evidence": {
                "applicable_zones": _ZONES + "B5 1.1 (PDF p53) names no zone.",
                "applicable_dev_types":
                    "B5 1.1 (PDF p53) verbatim: 'This Part applies to all residential development types except "
                    "for single dwelling house development under the Cumberland Local Environmental Plan 2021.' "
                    "The vocabulary cannot say 'all but', so the residential use types in "
                    "frontend-nextjs/lib/see/devTypeHierarchy.ts (secondary_dwelling, dual_occupancy, "
                    "multi_dwelling_housing, residential_flat_building, boarding_house, plus shop_top_housing "
                    "because B5 2.1 binds 'the residential component of mixed use developments') are listed and "
                    "dwelling_house is left out.",
            },
        },
    },
}
