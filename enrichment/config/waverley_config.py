"""
Waverley DCP 2022 Configuration

Structure (Parts A–F, 490 pages, Amendment 5):
- Part A: Preliminary — administrative, applies to ALL
- Part B: General Provisions — applies to ALL (B1–B17 topics)
  - B8: Heritage — condition-based (heritage items and HCAs only)
- Part C: Residential Development — scoped by DEVELOPMENT, LGA-wide
  - C1: Low Density Residential Development
  - C2: Other Residential Development   <- NOT "medium to high density"
- Part D: Commercial Development — scoped by DEVELOPMENT, LGA-wide
  - D1: Commercial and Retail Development
  - D2: Outdoor Dining                  <- NOT "mixed use"
- Part E: Site-Specific Provisions — precinct-filtered
  - E1: Bondi Junction Centre
  - E2: Bondi Beachfront Area
  - E3: Local Village Centres
  - E4: Special Character Areas
  - E5: 113 Macpherson Street, Bronte
  - E6: 194-214 Oxford Street Bondi Junction
  - E7: Edina Estate
- Part F: Development-Specific Controls — type-filtered
  - F1: Shared Residential Accommodation
  - F2: Tourist and Visitor Accommodation
  - F3: Child Care Centres
  - F4: Places of Public Worship
  - F5: Horticulture

NO Part of this DCP states a zone. The two labels marked above were wrong,
and the zone lists inferred from those labels hid 114 served rows until
2026-10-03. See the `parts` comment.

Source PDF: waverley/Waverley_DCP_2022_Full_Version_Amendment5.pdf
Registry key: waverley/waverley-dcp-2022
"""

# NO PART OF THIS DCP STATES A ZONE. Checked 2026-10-03 by reading every Part's
# own opening sentence in the source PDF; each scopes itself by DEVELOPMENT or by
# a MAPPED AREA, and the plan-level sentence (A1 section 1.2) is "This DCP applies
# to all land within the Waverley Council Local Government Area (LGA)."
#
# The zone constants that used to live here -- RESIDENTIAL_ZONES,
# LOW_DENSITY_ZONES, MEDIUM_HIGH_DENSITY_ZONES, BUSINESS_ZONES, MIXED_USE_ZONES --
# were removed with the four zone lists that used them, because they were derived
# from Part TITLES rather than from any sentence in the plan and were hiding 114
# served rows. Do not reintroduce a zone list for this council without quoting the
# Part that states it.
#
# SPECIAL_ZONES and ALL_ZONES went with them. Both were already unused, and they
# only surfaced as lint violations once the paragraph above stopped mentioning
# enrichment/config/zone_taxonomy.py: lint_hardcoded_zone_codes.py exempts a file
# whose TEXT names a shared source, so the old comment was granting the whole
# file an exemption it had not earned. Worth knowing before trusting a clean run
# on any other config -- a mention is not an import.

# Part B section codes → topic slugs
WAVERLEY_PART_B_TOPICS: dict[str, str] = {
    "B1":  "waste",
    "B2":  "sustainability",
    "B3":  "landscaping",
    "B4":  "coastal",
    "B5":  "water",
    "B6":  "accessibility",
    "B7":  "transport",
    "B8":  "heritage",
    "B9":  "safety",
    "B10": "public_art",
    "B11": "design_excellence",
    "B12": "subdivision",
    "B13": "excavation",
    "B14": "signage",
    "B15": "public_domain",
    "B16": "inter_war_buildings",
    "B17": "social_impact",
}

# Part E precinct codes → human-readable names
WAVERLEY_PRECINCTS: dict[str, str] = {
    "E1": "Bondi Junction Centre",
    "E2": "Bondi Beachfront Area",
    "E3": "Local Village Centres",
    "E4": "Special Character Areas",
    "E5": "113 Macpherson Street, Bronte",
    "E6": "194-214 Oxford Street Bondi Junction",
    "E7": "Edina Estate",
}

WAVERLEY_CONFIG = {
    "council": "waverley",
    "dcp_name": "Waverley DCP 2022",
    # EVERY entry declares BOTH keys, each carrying the Part's own sentence.
    # Nothing here is a fallthrough: the Parts of this DCP are scoped by
    # DEVELOPMENT and by MAPPED AREA, and not one of them states a zone. The four
    # zone lists this file used to carry were read off Part titles and are
    # contradicted by the Parts themselves -- see the module docstring.
    "parts": {
        "A": {
            "description":     "Preliminary",
            "scope_evidence": {
                "applicable_zones":
                    "A1 section 1.2 'LAND TO WHICH THIS DCP APPLIES' (PDF p7) verbatim: 'This "
                    "DCP applies to all land within the Waverley Council Local Government Area "
                    "(LGA).' This is the plan-level sentence every other Part inherits where it "
                    "states nothing of its own.",
                "applicable_dev_types":
                    "A1 section 1.3 'PURPOSE' (PDF p7) verbatim: 'This DCP provides strategies, "
                    "objectives and development guidelines for the assessment of Development "
                    "Applications (DA) and complements the provisions of the Waverley Local "
                    "Environmental Plan (WLEP).' Any DA, so no type narrows it.",
            },
            "applicable_zones":      ["ALL"],
            "applicable_dev_types":  ["ALL"],
            "layer":           "generic",
            "site_conditions": None,
        },
        "B": {
            "description":     "General Provisions",
            "scope_evidence": {
                "applicable_zones":
                    "B2 Ecologically Sustainable Development (PDF p23) verbatim: 'This Part "
                    "applies to all development in the Waverley LGA.' The B-series sub-parts "
                    "(B1-B17) each open the same way -- B1 Waste (PDF p12): 'This Part applies "
                    "to all works requiring a development application (DA) and is to be read in "
                    "conjunction with Council's relevant policies and guidelines.' ALL is stated, "
                    "not assumed. This entry serves every B sub-code except B8 via the parts "
                    "lookup's progressive strip (B1 -> B).",
                "applicable_dev_types":
                    "Same two sentences: 'all works requiring a development application' and "
                    "'all development in the Waverley LGA'. A general-provisions Part that names "
                    "a development type would stop binding every type it left out.",
            },
            "applicable_zones":      ["ALL"],
            "applicable_dev_types":  ["ALL"],
            "layer":           "generic",
            "site_conditions": None,
        },
        "B8": {
            "description":     "Heritage",
            "scope_evidence": {
                "applicable_zones":
                    "B8 (PDF p75) verbatim: 'This Part applies to all land identified, and land "
                    "adjacent to site identified, under Schedule 5 ...'. The scope is a HERITAGE "
                    "LISTING, not a zone -- a listed item or an HCA can carry any zone, and "
                    "`site_conditions: ['heritage']` below is what actually narrows this Part. A "
                    "zone list would hide heritage controls from every listed property zoned "
                    "otherwise.",
                "applicable_dev_types":
                    "The same sentence scopes by LAND, not by development. Any development on "
                    "listed or adjacent land is caught, so no type narrows it.",
            },
            "applicable_zones":      ["ALL"],
            "applicable_dev_types":  ["ALL"],
            "layer":           "condition",
            "site_conditions": ["heritage"],
        },
        # ZONE LIST REMOVED 2026-10-03, and it was hiding rules. See the module
        # docstring: C1 and C2 both state their scope as DEVELOPMENT, in the whole
        # LGA. "C" is the fallback for a C heading with no C1/C2 sub-code.
        "C": {
            "scope_declined": ("applicable_dev_types",),
            "description":       "Residential Development",
            "scope_evidence": {
                "applicable_zones":
                    "Neither sub-part of Part C states a zone. C1 (PDF p167) verbatim: 'This "
                    "Part applies to any type of low density residential development proposing a "
                    "new building or alterations and additions to an existing building or "
                    "buildings in the Waverley LGA.' C2 (PDF p199) states only what development "
                    "it covers. The previous ['R2','R3','R4'] was inferred from the Part title "  # noqa: zone-codes - names the zone list this change REMOVED, as the record of the defect; introduces no new list.
                    "and is contradicted by both.",
                "applicable_dev_types":
                    "C1 and C2 between them name seventeen forms of residential accommodation "  # noqa: zone-codes - DCP Part codes C1/C2 (Low Density / Other Residential Development), not zone codes.
                    "and this entry is the fallback for a heading that resolves to neither, so "
                    "no list can be attributed to it. ALL is the honest state for the fallback.",
            },
            "applicable_zones":      ["ALL"],
            "layer":             "use_specific",
        },
        "C1": {
            "scope_declined": ("applicable_dev_types",),
            "description":       "Low Density Residential Development",
            "scope_evidence": {
                "applicable_zones":
                    "C1 (PDF p167) verbatim: 'This Part applies to any type of low density "
                    "residential development proposing a new building or alterations and "
                    "additions to an existing building or buildings in the Waverley LGA.' The "
                    "scope is the WHOLE LGA. The previous ['R2'] came from reading the Part's "
                    "title against the Standard Instrument's name for R2 ('Low Density "
                    "Residential'); the Part itself names no zone, and R2-only filtered these 40 "
                    "served rows off every dwelling house in R3 or R4.",  # noqa: zone-codes - names the zone list this change REMOVED, as the record of the defect; introduces no new list.
                "applicable_dev_types":
                    "The same section defines the Part's own term, verbatim: 'For the purposes "
                    "of Part C1 Low Density Residential Development the term lower density "
                    "residential accommodation includes the following types of development: "
                    "Dwelling house; Dual occupancy; Semi-detached dwelling; Attached dwelling "
                    "(terrace styled development); and Secondary dwelling.' Three of the five "
                    "have a term; semi-detached and attached dwellings have none and are absent "
                    "from the serving taxonomy too. Declaring the three is a candidate narrowing "
                    "and is deliberately NOT made here, because narrowing hides and this change "
                    "is all in the widening direction. ALL preserves today's answer.",
            },
            "applicable_zones":      ["ALL"],
            "layer":             "use_specific",
        },
        # MISLABELLED until 2026-10-03: described as "Medium to High Density
        # Residential". The Part is "Other Residential Development", and that
        # mislabel is what produced the ["R3","R4"] zone list below it.
        "C2": {
            "scope_declined": ("applicable_dev_types",),
            "description":       "Other Residential Development",
            "scope_evidence": {
                "applicable_zones":
                    "C2 states NO zone. Verbatim (PDF p199): 'This Part applies to the "
                    "residential components of: Boarding Houses; Co-living housing; Group homes; "
                    "Hostels; Manor Houses; Multi dwelling housing; Multi dwelling housing "
                    "(terraces); Residential flat buildings; Seniors housing; Serviced "
                    "apartments; Shop top housing; and Student accommodation.' The previous "
                    "['R3','R4'] was inferred from a title this Part does not have. It filtered "  # noqa: zone-codes - names the zone list this change REMOVED, as the record of the defect; introduces no new list.
                    "40 served rows -- including every shop-top-housing control -- off the "
                    "centre zones where shop top housing and serviced apartments are found.",
                "applicable_dev_types":
                    "The same sentence is the list, and six of the twelve have a term "
                    "(boarding_house, manor_house, multi_dwelling_housing, "
                    "residential_flat_building, serviced_apartment, shop_top_housing) while "
                    "co-living housing, group homes, hostels, seniors housing and student "
                    "accommodation do not. A six-term list would delete the Part from the other "
                    "five, so it is not declared here; ALL preserves today's answer and the "
                    "narrowing needs each missing term checked against what the DA intake can "
                    "ask for.",
            },
            "applicable_zones":      ["ALL"],
            "layer":             "use_specific",
        },
        "D": {
            "scope_declined": ("applicable_dev_types",),
            "description":       "Commercial Development",
            "scope_evidence": {
                "applicable_zones":
                    "Neither sub-part states a zone: D1 (PDF p231) 'applies to commercial and "
                    "retail premises throughout Waverley' and D2 (PDF p238) addresses footpath "
                    "areas 'within the Waverley LGA'. The previous ['E1','E2','MU1'] was "  # noqa: zone-codes - names the zone list this change REMOVED, as the record of the defect; introduces no new list.
                    "inferred from the Part title.",
                "applicable_dev_types":
                    "This entry is the fallback for a D heading with no D1/D2 sub-code, so no "
                    "list can be attributed to it.",
            },
            "applicable_zones":      ["ALL"],
            "layer":             "use_specific",
        },
        "D1": {
            "scope_declined": ("applicable_dev_types",),
            "description":       "Commercial and Retail Development",
            "scope_evidence": {
                "applicable_zones":
                    "D1 (PDF p231) verbatim, its whole scope sentence: 'This Part applies to "
                    "commercial and retail premises throughout Waverley.' 'Throughout Waverley' "
                    "is the LGA. The previous ['E1','E2'] was never source-verified -- this "  # noqa: zone-codes - names the zone list this change REMOVED, as the record of the defect; introduces no new list.
                    "file's own comment said so and asked for the check -- and it filtered 12 "
                    "served rows off commercial and retail premises anywhere else.",
                "applicable_dev_types":
                    "The same sentence names 'commercial and retail premises'. Both terms exist "
                    "in the vocabulary and the serving taxonomy, so this is the one entry in the "
                    "file where a truthful narrowing is immediately expressible; it is still not "
                    "made here, because this change is confined to the widening direction. "
                    "Recorded as the strongest narrowing candidate in this council.",
            },
            "applicable_zones":      ["ALL"],
            "layer":             "use_specific",
        },
        # MISLABELLED until 2026-10-03: described as "Mixed Use", which produced
        # the ["MU1"] zone list. Part D2 of this DCP is OUTDOOR DINING.
        "D2": {
            "scope_declined": ("applicable_dev_types",),
            "description":       "Outdoor Dining",
            "scope_evidence": {
                "applicable_zones":
                    "D2 (PDF p238) verbatim: 'This Part guides applicants seeking approval to "
                    "utilise footpath areas outside their cafe or restaurant for footpath "
                    "seating, as well as developments that include outdoor courtyards. Where "
                    "proposals are partly or fully on public land within the Waverley LGA, "
                    "development consent and approval under Section 125 of the Roads Act 1993 is "
                    "required.' The scope is a FOOTPATH beside a cafe, anywhere in the LGA. The "
                    "previous ['MU1'] followed from calling this Part 'Mixed Use', which it is "
                    "not, and filtered 22 served rows off every shopping street not zoned MU1.",
                "applicable_dev_types":
                    "The same sentence scopes the Part to applicants 'outside their cafe or "
                    "restaurant'. `food_and_drink_premises` exists in the vocabulary, but the "
                    "Part also covers 'developments that include outdoor courtyards', which is "
                    "not a use at all, so a type list would drop that half. ALL.",
            },
            "applicable_zones":      ["ALL"],
            "layer":             "use_specific",
        },
        "E": {
            "scope_declined": ("applicable_zones",),
            "description":           "Site-Specific Provisions",
            "scope_evidence": {
                "applicable_zones":
                    "E1 Bondi Junction section 1.1 (PDF p260) verbatim: 'This Part applies to "
                    "land as identified in Figure 1.' E2 (PDF p314): 'This Part applies to the "
                    "land commonly known as the Bondi Beachfront Area shaded in [the figure].' "
                    "The scope is a MAPPED AREA, which a zone list cannot express; "
                    "`is_precinct_specific` below is what carries the geography (DQ-99). A zone "
                    "list would hide a precinct control from any lot inside the precinct "
                    "carrying another zone.",
                "applicable_dev_types":
                    "E1 section 1.1 binds the area, not a use, and adds 'All development is to "
                    "comply with Part B11 Design Excellence.' E2 (PDF p315): 'All development to "
                    "which this Part applies is to provide active street frontages'. 'All "
                    "development' is the Part's own words.",
            },
            "applicable_dev_types":  ["ALL"],
            "layer":                 "precinct",
            "is_precinct_specific":  True,
        },
        "F": {
            "scope_declined": ("applicable_dev_types",),
            "description":     "Development-Specific Controls",
            "scope_evidence": {
                "applicable_zones":
                    "F1 Shared Residential Accommodation (PDF p418) verbatim: 'This Part "
                    "contains guidelines for student housing, boarding houses, co-living "
                    "housing, group homes and hostels throughout Waverley.' 'Throughout "
                    "Waverley' is the LGA, and no F sub-part states a zone.",
                "applicable_dev_types":
                    "Part F is organised BY use -- F1 Shared Residential Accommodation, F2 "
                    "Tourist and Visitor Accommodation (backpackers, hotels and motels, serviced "
                    "apartments), F3 Child Care Centres, F4 Places of Public Worship, F5 "
                    "Horticulture (contents, PDF p417) -- but this is ONE entry covering all of "
                    "them, so any list would delete the Part from every sub-part left out. Four "
                    "of F1's five uses and F4's entire subject have no term. ALL is the only "
                    "honest value until Part F is split per sub-code.",
            },
            "applicable_zones":      ["ALL"],
            "layer":           "use_specific",
            "site_conditions": None,
        },
    },
    "precincts": WAVERLEY_PRECINCTS,
    "part_b_topics": WAVERLEY_PART_B_TOPICS,
}
