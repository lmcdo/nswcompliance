#!/usr/bin/env python3
"""Gate rules: who a DCP chapter's rows reach, from the chapter's own land sentence.

prior-art-checked: split out of scripts/derive_precinct_keys.py (500-line limit), which runs it
in the same pass. No other script writes v2_marker / v2_dcp_layer / v2_site_condition_required
from a rule (grep of scripts/ and migrations/, 2026-10-11).
"""
from __future__ import annotations

#: GATE RULES: who a chapter's rows reach, set from the chapter's OWN land sentence (page cited).
#: Same contract as RULES: a written rule per (council, chapter), re-run by dcp_commit_approved.py
#: after every publish, so a re-extraction cannot undo it. Each sets only gate columns that the
#: for-property route reads; provision_text is never touched. Origin: DQ-146 (2026-10-11), 905
#: current rules parked in the condition layer with no flood/bushfire condition and no heritage
#: marker -- returned by no query, so shown to no house.
GATE_RULES: list[dict] = [
    # "applies to any land within Wollongong LGA where (i) An item of environmental heritage as
    # listed under Schedule 5 ... (ii) ... within one of the Heritage Conservation Areas ...
    # (iii) adjacent to or within the vicinity" (Wollongong DCP 2009 E11, p3). (iii) has no land
    # layer: recorded limit -- a house only NEAR a heritage item is not shown these rules.
    {"name": "wollongong_e11_heritage", "council": "wollongong",
     "where": "source_chapter_key = 'chapter-e11-heritage-conservation'",
     "set": {"v2_marker": "heritage"}},
    # "Part E1 applies to sites which are listed as Heritage Items listed in the Inner West LEP
    # 2022, and to sites and places contained within Heritage Conservation Areas" (Ashfield E1 p6).
    {"name": "ashfield_e1_heritage", "council": "ashfield",
     "where": "source_chapter_key = 'chapter-e1-heritage'",
     "set": {"v2_marker": "heritage"}},
    # "Part 8 applies to heritage items, heritage conservation areas (HCAs), archaeological sites
    # and Aboriginal heritage" (Marrickville DCP 2011 Part 8, p15). Address audit 2026-10-15: 913
    # rules with a non-heritage topic reached every house; the other 448 reached no HCA house
    # (queryHeritageByHca reads v2_marker only). Recorded limit: archaeological sites and
    # Aboriginal heritage have no land layer, so a house that is only one of those is not shown these.
    {"name": "marrickville_part8_heritage", "council": "marrickville",
     "where": "source_chapter_key = 'part8-heritage'",
     "set": {"v2_marker": "heritage"}},
    # Parramatta DCP 2023 Part 7 Heritage (p290): "works on heritage items, archaeological site or a building or place
    # within a heritage conservation area" (7.2, p292), plus 7.5 development in their vicinity (no land layer: limit as
    # Wollongong E11 (iii)). Rows already keyed to a 7.10 conservation area keep that key (precinct gate). 230 rows were
    # parked in the condition layer with no marker after the 2026-10-14 publish -- shown to no house (OC-21).
    {"name": "parramatta_part7_heritage", "council": "parramatta",
     "where": "source_chapter_key = 'parramatta-dcp-2023-full' AND ref_number ~ '__7_' AND v2_precinct_id IS NULL",
     "set": {"v2_marker": "heritage"}},
    # "This Part applies to all land identified, and land adjacent to site identified, under
    # Schedule 5 of WLEP" (Waverley DCP 2022 B8, printed p67). Same adjacency limit as E11.
    {"name": "waverley_b8_heritage", "council": "waverley",
     "where": "source_chapter_key = 'waverley-dcp-2022' AND v2_dcp_part = 'B8'",
     "set": {"v2_marker": "heritage"}},
    # Woollahra E2.1.1 (p5): stormwater "applies to all land within the Woollahra Municipality";
    # "The flood risk management component ... applies to all land ... that is within a flood
    # risk precinct". E2.3 "Flood risk management controls" starts p34.
    {"name": "woollahra_e2_3_flood", "council": "woollahra",
     "where": "source_chapter_key = 'chapter-e2-stormwater-flood' AND ref_number ~ '__E2_3'",
     "set": {"v2_dcp_layer": "condition", "v2_site_condition_required": "flood"}},
    {"name": "woollahra_e2_whole_council", "council": "woollahra",
     "where": "source_chapter_key = 'chapter-e2-stormwater-flood' AND ref_number !~ '__E2_3'"
              " AND v2_dcp_layer = 'condition'",
     "set": {"v2_dcp_layer": "generic"}},
    # "This chapter applies to all land within the Woollahra Municipality" (E4 p5).
    {"name": "woollahra_e4_whole_council", "council": "woollahra",
     "where": "source_chapter_key = 'chapter-e4-contaminated-land' AND v2_dcp_layer = 'condition'",
     "set": {"v2_dcp_layer": "generic"}},
    # C-B 4.2 "applies to heritage items listed in the Canterbury-Bankstown LEP 2023 (Schedule 5,
    # Part 1)" (p4): heritage marker, so heritage properties get it. 22 rows sat in v2_dcp_layer
    # 'heritage', which the for-property route never queries (DQ-146, widened 2026-10-11).
    # C-B 4.1 is the heritage chapters' introduction ("does not remove the requirement to comply with the LEP ... that
    # may affect a heritage item or a building within a heritage conservation area", p6): same reach as 4.2. Its 60 rows
    # sat in the unread 'heritage' layer -- shown to no house (OC-21, 2026-10-15).
    {"name": "cb_4_1_heritage_intro", "council": "canterbury_bankstown",
     "where": "source_chapter_key = 'chapter-4-1-introduction'",
     "set": {"v2_marker": "heritage", "v2_dcp_layer": "generic"}},
    {"name": "cb_4_2_heritage_items", "council": "canterbury_bankstown",
     "where": "source_chapter_key = 'chapter-4-2-heritage-items'",
     "set": {"v2_marker": "heritage", "v2_dcp_layer": "generic"}},
    # C-B 4.4 "vicinity of places of heritage significance": no land layer records "vicinity", so the
    # 3 rows parked in the unread 'heritage' layer go to the generic layer (shown, scope recorded as
    # unconfirmed under DQ-144) rather than to no house at all.
    {"name": "cb_4_4_vicinity_generic", "council": "canterbury_bankstown",
     "where": "source_chapter_key = 'chapter-4-4-vicinity-of-places-of-heritage-significance'"
              " AND v2_dcp_layer = 'heritage'",
     "set": {"v2_dcp_layer": "generic"}},
    # Ku-ring-gai Part 16 "guides development on land identified on the Ku-ring-gai Bushfire Prone
    # Land Map and/or ... the Ku-ring-gai Bushfire Risk Evacuation Map" (p2). The Bushfire Prone Land
    # Map is the one the Planning Portal's bushfire flag reads, so the condition layer serves these to
    # exactly those houses. Recorded limit (user decision 2026-10-11): land only on the Risk
    # Evacuation Map has no layer here and is not shown these rules.
    {"name": "krg_16_bushfire_condition", "council": "ku_ring_gai",
     "where": "source_chapter_key = 'section-b-part-16-bushfire'",
     "set": {"v2_dcp_layer": "condition", "v2_site_condition_required": "bushfire"}},
    # Marrickville 2.23 "applies to the land specified in Inner West Local Environmental Plan 2022
    # (Inner West LEP 2022) Acid Sulfate Soils Maps" (p5) -- the LEP layer the page reads.
    {"name": "marrickville_2_23_acid_sulfate", "council": "marrickville",
     "where": "source_chapter_key = 'part2-s23-acid-sulfate'",
     "set": {"v2_dcp_layer": "condition", "v2_site_condition_required": "acid_sulfate"}},
    # Ku-ring-gai Part 17 "guides development on land identified within the Natural Resource --
    # Riparian Lands Map in the KLEP (see clause 6.4)" (p2) -- the LEP layer the page reads.
    {"name": "krg_17_riparian", "council": "ku_ring_gai",
     "where": "source_chapter_key = 'section-b-part-17-riparian'",
     "set": {"v2_dcp_layer": "condition", "v2_site_condition_required": "riparian"}},
    # "General Requirements for residential flat buildings and mixed use development in areas zoned R4, B3 and B4
    # zones." (Campbelltown DCP Part 4, p2). B3 and B4 were retired by the 2023 Employment Zones reform; the repo's
    # own translation (frontend-nextjs/shared/zone-taxonomy.json legacyToCurrentAliases) maps B3 -> E2, B4 -> MU1.
    {"name": "campbelltown_part4_zones", "council": "campbelltown",
     "where": "source_chapter_key = 'part-4-rfb-mixed-use'",
     "set": {"v2_applicable_zones": ["R4", "E2", "MU1"]}},  # noqa: zone-codes (the plan's own zones, translated)
    # "to enhance the function, design and amenity of employment lands within Zones E3 Productivity Support and SP4
    # Enterprise." (Canterbury-Bankstown DCP 2023 chapter 8.1, p4).
    {"name": "cb_8_1_employment_zones", "council": "canterbury_bankstown",
     "where": "source_chapter_key = 'chapter-8-1-general-requirements'",
     # layer 'generic': in the precinct layer with no precinct the zone tag was never read (2026-10-15 fail-closed)
     "set": {"v2_applicable_zones": ["E3", "SP4"], "v2_dcp_layer": "generic"}},  # noqa: zone-codes (the plan's own zones)
    # "Part 19 applies to any development associated with a Heritage Item or within a Heritage Conservation Area
    # (HCA) identified on the KLEP Heritage Map." (Ku-ring-gai DCP Part 19, p2). Same gate as ashfield_e1_heritage.
    # Recorded limit: 19F's "vicinity of a heritage item" has no land layer, so a lot only adjoining one is not shown it.
    {"name": "krg_19_heritage", "council": "ku_ring_gai",
     "where": "source_chapter_key = 'section-b-part-19-heritage'",
     "set": {"v2_marker": "heritage"}},
]
# ---- lane-gates 2026-10-15: Marrickville Part 8 by HCA ----------------------------------------------------------
# Part 8 section 8.2.N (N >= 3) is "<name> Heritage Conservation Area - HCA N-2" (contents, PDF p3-12): its rules
# are that HCA's. 8.2.1-8.2.2 (principles for HCAs), 8.3 "Controls for residential HCAs", 8.4 "Controls for retail
# streetscapes in Heritage Conservation Areas" and 8.5 "HCA Style Sheets" apply in any HCA, not to a heritage item
# outside one (ANY_HCA in frontend-nextjs/lib/provision-sql-filters.ts). Slugs = heritage_conservation_areas.db_slug
# of the Inner West LEP 2022 HCA with the same name -- what the route resolves the property's HCA to; same table as
# scripts/enrichment/link_marrickville_hca_provisions.py, plus HCA 13, 24, 36-38 matched by name. Address audit
# 2026-10-15: 5 of 10 rules at 21/1-3 Coronation Ave Petersham (heritage item, no HCA) were other HCAs' rules.
# Recorded limit: an HCA whose LEP name is stored mis-encoded (C70 Porter's, C67 Inter-War) does not resolve, so
# its lots get the general Part 8 rules only -- missing rules, never another area's.
_MARRICKVILLE_8_2_HCA = {
    3: "the_abergeldie_estate_heritage_conservation_area", 4: "hca_2", 5: "hca_3",
    6: "railway_street_petersham_heritage_conservation_area", 7: "hca_5", 8: "hca_6", 9: "hca_7", 10: "hca_8",
    11: "hca_9", 12: "hca_10", 13: "hca_11", 14: "hca_12", 15: "enmore_house_heritage_conservation_area",
    16: "hca_14", 17: "hca_15", 18: "hca_16", 19: "kingston_south_heritage_conservation_area",
    20: "petersham_south_norwood_estate_heritage_conservation_area", 21: "hca_19",
    22: "audley_street_south_bayswater_estate_heritage_conservation_area", 23: "hca_21", 24: "hca_22",
    25: "hca_23", 26: "hca_24", 27: "hca_25", 28: "hca_26", 29: "hca_27", 30: "hca_28",
    31: "south_dulwich_hill_heritage_conservation_area", 32: "hca_30", 33: "hca_31", 34: "hca_32", 35: "hca_33",
    36: "hca_34", 37: "hca_35", 38: "hoskins_park_and_environs_heritage_conservation_area",
    39: "lackey_street_and_simpson_park_heritage_conservation_area",
    40: "camden_street_and_james_street_heritage_conservation_area",
}
_P8 = "source_chapter_key = 'part8-heritage' AND ref_number ~ "
# Part 8.3 subdivision controls (PDF p196) carry C8-C13 refs, not 8.3, so the any-HCA rule's regex missed them
# (live check 2026-10-16). C11-C13 each name one HCA: "C11 HCA 14 Llewellyn Estate", "C12 HCA 31 David Street",
# "C13 HCA 17 Kingston South" (HCA N = section 8.2.N+2); C8-C10 apply in any HCA.
_P8_196 = "source_chapter_key = 'part8-heritage' AND pdf_page = 196 AND ref_number ~ "

GATE_RULES += [
    {"name": f"marrickville_8_2_{n}_hca", "council": "marrickville",
     "where": _P8 + f"'__8_2_{n}([_~ ]|$)'", "set": {"v2_heritage_hca": slug}}
    for n, slug in sorted(_MARRICKVILLE_8_2_HCA.items())
] + [
    {"name": "marrickville_8_3_c11_hca14", "council": "marrickville", "where": _P8_196 + "'__C11$'",
     "set": {"v2_heritage_hca": _MARRICKVILLE_8_2_HCA[16]}},  # HCA 14 = 8.2.16,
    {"name": "marrickville_8_3_c12_hca31", "council": "marrickville", "where": _P8_196 + "'__C12$'",
     "set": {"v2_heritage_hca": _MARRICKVILLE_8_2_HCA[33]}},  # HCA 31 = 8.2.33,
    {"name": "marrickville_8_3_c13_kingston", "council": "marrickville", "where": _P8_196 + "'__C13$'",
     "set": {"v2_heritage_hca": _MARRICKVILLE_8_2_HCA[19]}},  # HCA 17 = 8.2.19,
    {"name": "marrickville_8_3_c8_c10_any", "council": "marrickville", "where": _P8_196 + "'__C(8|9|10)$'",
     "set": {"v2_heritage_hca": "__any_hca__"}},
] + [
    {"name": "marrickville_part8_any_hca", "council": "marrickville",
     "where": _P8 + "'__(8_2_[12]|8_[345])([_~ ]|$)'", "set": {"v2_heritage_hca": "__any_hca__"}},
]
# ---- lane-ashfield-hca 2026-10-16: Ashfield E1 Part 9 by HCA ---------------------------------------------------------
# Ashfield DCP Chapter E1 Part 9 is, per Heritage Conservation Area, "C<n> <name>": key period, statement of
# significance, key character elements, non-contributory elements, history and building rankings (PDF p47-391, each
# section opens on the page of its "C<n>" heading row). Those are that HCA's own statements, so a heritage item
# outside every HCA (3 Rectory Ave Ashfield) must not be shown them: they are keyed by page range to the HCA's
# heritage_conservation_areas.db_slug (the Inner West LEP 2022 HCA of the same name; what the route resolves the
# property's HCA to), as for Marrickville above. Part 9 p44-46 (location map, list of all HCAs) apply in any HCA
# (ANY_HCA, frontend-nextjs/lib/provision-sql-filters.ts). Parts 1-8 (items and general HCA controls) stay untagged.
# Section numbers C8, C22, C25, C36, C41, C42 do not exist in the DCP. 49 sections, all resolve to a slug.
# Recorded limits: (a) the twelve Summer Hill HCAs (C44-C55) share db_slug 'summer_hill' in the table,
# so a lot in any of them is shown all twelve sections; (b) section C12 Murrell opens mid-page 113 below the tail of
# Mountjoy's photo table (rows ~217-219), so only its heading row is keyed to Murrell on that page.
_ASHFIELD_E1_HCA = [  # (section no., first PDF page, last PDF page, db_slug)
    (1, 47, 54, "holwood"), (2, 55, 59, "eccles_estate_heritage_conservation_area"), (3, 60, 67, "farleigh"),
    (4, 68, 74, "goodwin_avenue_heritage_conservation_area"), (5, 75, 80, "hillcot_street_heritage_conservation_area"),
    (6, 81, 86, "king_street"), (7, 87, 93, "harland"), (9, 94, 98, "ilford_avenue_heritage_conservation_area"),
    (10, 99, 102, "miller_avenue_heritage_conservation_area"),
    (11, 103, 113, "mountjoy_estate_heritage_conservation_area"),  # p113: all but the C12 heading row
    (12, 114, 119, "murrell"), (13, 120, 129, "federal_fyle_heritage_conservation_area"),
    (14, 130, 139, "park_avenue_heritage_conservation_area"), (15, 140, 144, "rectory_estate_heritage_conservation_area"),
    (16, 145, 149, "richmond_avenue_heritage_conservation_area"), (17, 150, 154, "rose_street_heritage_conservation_area"),
    (18, 155, 163, "service_avenue_heritage_conservation_area"), (19, 164, 167, "somerville"),
    (20, 168, 174, "taringa_estate_heritage_conservation_area"), (21, 175, 181, "tintern"),
    (23, 182, 190, "victoria_square"), (24, 191, 196, "webbs_avenue_heritage_conservation_area"),
    (26, 197, 200, "birriga_road_heritage_conservation_area"), (27, 201, 204, "bridges_avenue_heritage_conservation_area"),
    (28, 205, 210, "edwin_street_north_heritage_conservation_area"), (29, 211, 217, "gads_hill_heritage_conservation_area"),
    (30, 218, 224, "hammond_park_estate_heritage_conservation_area"), (31, 225, 231, "howes_estate_heritage_conservation_area"),
    (32, 232, 239, "ivanhoe_heritage_conservation_area"),
    (33, 240, 243, "lang_street_heritage_conservation_area"), (34, 244, 252, "lucy_street_heritage_conservation_area"),
    (35, 253, 260, "rathgael_estate_heritage_conservation_area"), (37, 261, 268, "the_ranch_heritage_conservation_area"),
    (38, 269, 275, "wetherill_street_heritage_conservation_area"), (39, 276, 282, "goodlet_heritage_conservation_area"),
    (40, 283, 290, "hillside_heritage_conservation_area"), (43, 291, 296, "clover_hill_heritage_conservation_area"),
    (44, 297, 303, "summer_hill"), (45, 304, 309, "summer_hill"), (46, 310, 316, "summer_hill"),
    (47, 317, 328, "summer_hill"), (48, 329, 333, "summer_hill"), (49, 334, 341, "summer_hill"),
    (50, 342, 348, "summer_hill"), (51, 349, 357, "summer_hill"), (52, 358, 368, "summer_hill"),
    (53, 369, 377, "summer_hill"), (54, 378, 383, "summer_hill"), (55, 384, 391, "summer_hill"),
]
_A9 = "source_chapter_key = 'chapter-e1-heritage' AND ref_number ~ '__Part 9' AND "
GATE_RULES += [
    {"name": f"ashfield_e1_9_c{n}_hca", "council": "ashfield",
     "where": _A9 + (f"((pdf_page BETWEEN {a} AND {b}) OR (pdf_page = 113 AND ref_number ~ '__Part 9 C12$'))"
                     if n == 12 else
                     f"pdf_page BETWEEN {a} AND {b} AND ref_number !~ '__Part 9 C12$'" if n == 11 else
                     f"pdf_page BETWEEN {a} AND {b}"),
     "set": {"v2_heritage_hca": slug}}
    for n, a, b, slug in _ASHFIELD_E1_HCA
] + [
    {"name": "ashfield_e1_9_any_hca", "council": "ashfield",
     "where": _A9 + "pdf_page BETWEEN 44 AND 46", "set": {"v2_heritage_hca": "__any_hca__"}},
]
# ---- end lane-ashfield-hca ---------------------------------------------------------------------------------------
GATE_RULES += [
    # "This section applies to land zoned MU1 Mixed Use in the Paddington business precinct in Oxford Street and
    # the streets adjoining" (Woollahra DCP 2015 E1.8.4, p25): zone tag here, Paddington HCA key in EXTRA_KEY_RULES.
    {"name": "woollahra_e1_8_4_zone", "council": "woollahra",
     "where": "source_chapter_key = 'chapter-e1-parking-access' AND ref_number ~ '__E1_8_4([_~ ]|$)'",
     "set": {"v2_applicable_zones": ["MU1"]}},  # noqa: zone-codes (the plan's own zone)
]
# ---- end lane-gates ----------------------------------------------------------------------------------------------
_GATE_COLUMNS = {"v2_marker", "v2_dcp_layer", "v2_site_condition_required", "v2_applicable_zones",
                 "v2_heritage_hca"}
#: v2_applicable_zones added 2026-10-14: a zone limit set by hand was undone by every re-extraction (dry run of the
#: map job); as a gate rule it is re-applied after every publish like the others.

#: Precinct-keying rules kept here because derive_precinct_keys.py is at its 500-line limit; it
#: splices these into RULES. C-B 4.3 lists seven HCAs (p4); section 21 is "Specific controls for the
#: Ashbury HCA"; every other section applies to all seven (outlines: import_cb_heritage_areas.py).
EXTRA_KEY_RULES: list[dict] = [
    {"name": "cb_4_3_ashbury", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-4-3-heritage-conservation-areas' AND ref_number ~ '__21(_|$)'",
     "strategy": {"type": "constant", "precinct_id": "Ashbury HCA"}},
    {"name": "cb_4_3_all_seven", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-4-3-heritage-conservation-areas' AND ref_number !~ '__21(_|$)'",
     "strategy": {"type": "constant", "precinct_id": "C-B 4.3 heritage conservation areas"}},
    # "This chapter applies to the Woollahra Heritage Conservation Area, which is shown in Map 1." (Woollahra DCP 2015
    # C2, p5). Outline already loaded (precinct 'Woollahra HCA'); 47 of its rows were keyed by hand, so a re-extraction
    # would have unkeyed them -- now a rule.
    {"name": "woollahra_c2_woollahra_hca", "council": "woollahra", "validate": False,
     "where": "source_chapter_key = 'chapter-c2-woollahra-hca'",
     "strategy": {"type": "constant", "precinct_id": "Woollahra HCA"}},
    # Ku-ring-gai Part 14B, by PDF PAGE (refs are garbled L-codes). Each precinct section opens on the page of
    # its figure: 14B.8 T1 p10, 14B.9 T2 p21, 14B.10 T3 p27, 14B.11 T4 p35. 14B.1-14B.7 (p1-9) apply to the
    # whole centre, Figure 14B.1-1 p2 = T1-T4 together: outline '14B' (import_woollahra_b2_union.py --union
    # krg_14b; the id must match precinct-service's ^14[A-O] pattern). Address audit 2026-10-15: all 184
    # served rows sat in the precinct layer with no key.
    {"name": "krg_14b_turramurra_by_page", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14b-turramurra-local-centre'",
     "strategy": {"type": "page_range", "ranges": [
         ("14B", 1, 9), ("14B_T1", 10, 20), ("14B_T2", 21, 26), ("14B_T3", 27, 34), ("14B_T4", 35, 38)]},
     "fingerprint": {"max_page": 38, "min_coverage": 0.95}},
    # Canterbury-Bankstown DCP 2023 Ch 7.2 City West, by PDF PAGE from its contents (p3): Section N "applies to land
    # shown in Figure Na" (2 Bass Hill p6 ... 13 Yagoona p65). Section 1 (p1-5) and Appendix 1 Setbacks (p71-84)
    # apply to every centre -> union '7.2'. Appendix 2 (p85-108) is the lot table Section 2.21 points to (Arundle Rd
    # lots) -> Bass Hill. Outlines: scripts/fit_cb_raster_centres.py. Address audit 2026-10-15: all 339 served rows
    # sat in the precinct layer with no key. Fingerprint = the last page any current row sits on.
    {"name": "cb_7_2_city_west_by_page", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-7-2-city-west'",
     "strategy": {"type": "page_range", "ranges": [
         ("7.2", 1, 5), ("7.2.2", 6, 16), ("7.2.3", 17, 21), ("7.2.4", 22, 25), ("7.2.5", 26, 28),
         ("7.2.6", 29, 32), ("7.2.7", 33, 35), ("7.2.8", 36, 41), ("7.2.9", 42, 49), ("7.2.10", 50, 53),
         ("7.2.11", 54, 61), ("7.2.12", 62, 64), ("7.2.13", 65, 70), ("7.2", 71, 84), ("7.2.2", 85, 108)]},
     "fingerprint": {"max_page": 96, "min_coverage": 0.95}},
    # Ku-ring-gai Part 14 centres, by PDF PAGE from each precinct section's own running heading ("14D.7 PRECINCT G1:
    # ST JOHNS AVENUE AND HENRY STREET" ...). Sections x.1-x.6 apply to the whole centre ("All development within the
    # Gordon local centre, as outlined in Figure 14D.1-1") -> the union outline. Outlines:
    # scripts/fit_vector_centres.py + import_vector_centres.py. Address audit 2026-10-15: all unkeyed.
    # C-B Ch 8.3 Hume Highway: only the sections whose land is PROVED are keyed. S4 Rookwood (p10-14) -> union of the
    # register-found sites (8.3.4); S6 167 Hume Hwy (p19-33) -> its Lot 402 DP 631754 (8.3.6). S5/S7/S8 name addresses
    # the NSW register does not hold; S1-S3 and Appendix 1 cover the whole corridor (S3: E3 land adjoining the highway,
    # no outline). Those rows stay unkeyed -- shown to no house -- rather than guessed. Fingerprint: 135/206 rows keyed.
    # C-B Ch 2.2 Flood risk management is two plans in one PDF: Sections 1-8 (p4-65) are "Flood risk management in the
    # former Bankstown Local Government Area" (p4), Sections 9-10 (p66-) "... in the former Canterbury Local Government
    # Area" (p66). Keyed to the ABS 2015 former-LGA outlines (former_councils_abs2015.geojson). Address audit 2026-10-15:
    # 29 Mavis St / 37A Victoria St Revesby (former Bankstown) were served Section 9.
    # C-B Ch 7.4 Neighbourhood centres applies to "neighbourhood centres that are identified as 'Area 1' on the Land
    # Zoning Map" (p4-5). Keyed to the union of the LEP's own Area 1 polygons (lep_area1_7_4.geojson, Planning Portal).
    {"name": "cb_7_4_neighbourhood_centres", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-7-4-neighbourhood-centres'",
     "strategy": {"type": "constant", "precinct_id": "7.4"}},
    {"name": "cb_2_2_flood_by_former_council", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-2-2-flood-risk-management'",
     "strategy": {"type": "page_range", "ranges": [
         ("C-B former Bankstown", 1, 65), ("C-B former Canterbury", 66, 69)]},
     "fingerprint": {"max_page": 69, "min_coverage": 0.95}},
    {"name": "cb_8_3_hume_highway_by_page", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-8-3-hume-highway'",
     "strategy": {"type": "page_range", "ranges": [("8.3.4", 10, 14), ("8.3.6", 19, 33), ("8.3.8", 38, 41)]},
     "fingerprint": {"max_page": 42, "min_coverage": 0.6}},  # S8 (p38-41): placed from its site plan, Fig 8a
    # C-B Ch 7.1 / 6.1 "General requirements": Part 7 holds the local and village centres (7.2-7.6), Part 6 the strategic
    # centres (6.2 Bankstown, 6.3 Campsie); each .1 chapter's controls "enhance the function, design and amenity of the
    # centres" (7.1/6.1 p5). Keyed to the union of the Part's centres MAPPED so far (cb_part7 / cb_part6 unions):
    # a centre not yet mapped is missing these rules, never given them wrongly.
    {"name": "cb_7_1_part7_centres", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-7-1-general-requirements'",
     "strategy": {"type": "constant", "precinct_id": "C-B Part 7 centres"}},
    {"name": "cb_6_1_part6_centres", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-6-1-general-requirements'",
     "strategy": {"type": "constant", "precinct_id": "C-B Part 6 centres"}},
    # C-B Ch 11.4 Croydon Street Precinct: "Chapter 11.4 of this DCP applies to the site as shown in the Land
    # Application Map (Figure 1a)" (p5) -- every section. Outline: scripts/fit_site_plans.py --config
    # site_plans_11_4.json (dark-red precinct line placed on lot lines, shape 0.985, 8/8 register addresses inside).
    {"name": "cb_11_4_croydon_street", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-11-4-croydon-street-precinct'",
     "strategy": {"type": "constant", "precinct_id": "11.4"}},
    # Ku-ring-gai Part 14H: "The site at 101 Eton Road, Lindfield, which is currently occupied by Screen Australia"
    # (p3), drawn as the orange "Site Location" in Figure 14H.1-1 (p2) -- every section is that one site. 101 left the
    # address register when the site was subdivided (DP271066 2019, SP109812 2025); outline = those 12 lots, shape
    # 0.997 against the figure (build_site_boundaries.py --addresses, register_absent).
    {"name": "krg_14h_screen_australia", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14h-screen-australia-site'",
     "strategy": {"type": "constant", "precinct_id": "14H"}},
    {"name": "krg_14a_st_ives_by_page", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14a-st-ives-local-centre'",
     "strategy": {"type": "page_range", "ranges": [
         ("14A", 1, 8), ("14A_S1", 9, 13), ("14A_S2", 14, 19), ("14A_S3", 20, 22)]},
     "fingerprint": {"max_page": 22, "min_coverage": 0.95}},
    # 14G Pymble Business Park: "Core Urban Precinct (E3 Productivity Support Zone)" as outlined in Figure 14G.1-1 (p2);
    # outline fitted from the plan's vector lot lines to the cadastre, IoU 0.944 vs the figure (2026-10-17,
    # scripts/fit_area_maps.py, picture data/area_map_checks/section-b-part-14g-pymble-business-park_14G.png).
    {"name": "krg_14g_pymble_business_park", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14g-pymble-business-park'",
     "strategy": {"type": "constant", "precinct_id": "14G"}},
    {"name": "krg_14d_gordon_by_page", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14d-gordon-local-centre'",
     "strategy": {"type": "page_range", "ranges": [
         ("14D", 1, 9), ("14D_G1", 10, 15), ("14D_G2", 16, 21), ("14D_G3", 22, 27), ("14D_G4", 28, 33),
         ("14D_G5", 34, 36)]},
     "fingerprint": {"max_page": 35, "min_coverage": 0.95}},
    {"name": "krg_14e_lindfield_by_page", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14e-lindfield-local-centre'",
     "strategy": {"type": "page_range", "ranges": [
         ("14E", 1, 10), ("14E_L1", 11, 17), ("14E_L2", 18, 23), ("14E_L3", 24, 29), ("14E_L4", 30, 42),
         ("14E_L5", 43, 55), ("14E_L6", 56, 64), ("14E_L7", 65, 66), ("14E_L8", 67, 70)]},
     "fingerprint": {"max_page": 69, "min_coverage": 0.95}},
]


# ---- lane-gates 2026-10-15: rules whose own words name their area (address audit run2) ----
EXTRA_KEY_RULES += [
    # Warringah DCP 2011 G1 "applies to land identified in the B4 Mixed Use Zone ... known as the Dee Why Town Centre"
    # (p95). Outline = WLEP 2011 Centres Map 'Dee Why Town Centre' (MU1 IoU 0.998). Sections 1-11 only (p95-104 and the
    # p105 'General' landscaping rows); 12 Key Sites, 13 Civic Centre Site, 14 RFBs and G2 (p110) stay withheld.
    {"name": "warringah_g1_dee_why_town_centre", "council": "northern_beaches", "validate": False,
     "where": "source_chapter_key = 'warringah-dcp-2011-full' AND (pdf_page BETWEEN 95 AND 104"
              " OR id IN (190884, 191033, 191125, 191195, 192013))",
     "strategy": {"type": "constant", "precinct_id": "G1 Dee Why Town Centre"}},
    # Warringah DCP 2011 G4 "This Plan applies to Lot 100, DP 1015283, 145 Old Pittwater Road, Brookvale" (p121).
    # Outline = build_site_boundaries.py --addresses (the lot is no longer in the cadastre). G4 runs p121-137; p121 is
    # shared with G3, so only its two G4 rows (the 'Applies to Land' and 'Objectives' rows) are listed by id.
    {"name": "warringah_g4_warringah_mall", "council": "northern_beaches", "validate": False,
     "where": "source_chapter_key = 'warringah-dcp-2011-full' AND (pdf_page BETWEEN 122 AND 137"
              " OR id IN (192062, 192063))",
     "strategy": {"type": "constant", "precinct_id": "G4 Warringah Mall"}},
    # Warringah DCP 2011 G6 "for future development on Lot 1, DP 706230, 932 Pittwater Road Dee Why" (p152).
    # Outline = build_site_boundaries.py (lot list). G6 runs p152-157 plus the one G6 row at the top of p158 (G7 starts
    # lower on that page).
    {"name": "warringah_g6_dee_why_rsl", "council": "northern_beaches", "validate": False,
     "where": "source_chapter_key = 'warringah-dcp-2011-full' AND (pdf_page BETWEEN 152 AND 157 OR id IN (192172))",
     "strategy": {"type": "constant", "precinct_id": "G6 Dee Why RSL Club"}},
]
EXTRA_KEY_RULES += [
    # Woollahra E1.8.4 "Certain land in Paddington zoned MU1 Mixed Use" (p25) -> Paddington HCA outline + MU1 tag.
    {"name": "woollahra_e1_8_4_paddington", "council": "woollahra", "validate": False,
     "where": "source_chapter_key = 'chapter-e1-parking-access' AND ref_number ~ '__E1_8_4([_~ ]|$)'",
     "strategy": {"type": "constant", "precinct_id": "Paddington HCA"}},
    # Waverley DCP 2022 B7 7.1(i)(i) "Basement parking areas and structures ... In Bondi Junction must not protrude
    # above the level of the adjacent street" (p58) -> outline E1 Bondi Junction. Only the rows that say so.
    {"name": "waverley_b7_in_bondi_junction", "council": "waverley", "validate": False,
     "where": "source_chapter_key = 'waverley-dcp-2022' AND v2_dcp_part = 'B7'"
              " AND provision_text ~* '\mIn Bondi Junction must\M'",
     "strategy": {"type": "constant", "precinct_id": "E1"}},
]
# ---- end lane-gates keys ----


def apply_gate_rules(cur, council: str | None, apply: bool, only: set[str] | None = None) -> list[tuple]:
    """Set each GATE_RULES row's gate columns. Returns (id, column, before, after, rule) per
    changed column, for the backup. Idempotent: a row already holding the values is skipped."""
    changes: list[tuple] = []
    truth = slug_key = None
    for rule in GATE_RULES:
        if (council and rule["council"] != council) or (only and rule["name"] not in only):
            continue
        unknown = set(rule["set"]) - _GATE_COLUMNS
        if unknown:
            raise ValueError(f"{rule['name']}: not a gate column {sorted(unknown)}")
        if "v2_applicable_zones" in rule["set"]:
            # DQ-30: a zone this council's LEP does not have would reach no house. Refuse before writing.
            if truth is None:
                try:
                    from validate_zone_code_validity import load_ground_truth, load_slug_resolution
                except ImportError:                   # imported as scripts.gate_rules
                    from scripts.validate_zone_code_validity import load_ground_truth, load_slug_resolution
                truth = load_ground_truth(cur)
                slug_key = load_slug_resolution(cur, truth)
            key = slug_key.get(rule["council"])
            zones = set(rule["set"]["v2_applicable_zones"]) - {"ALL"}
            if key is None or not zones <= truth.get(key, set()):
                raise ValueError(f"{rule['name']}: zones {sorted(zones - truth.get(key or '', set()))} are not in "
                                 f"{rule['council']}'s LEP land-use table (or the council has none)")
        cols = sorted(rule["set"])
        cur.execute(
            f"SELECT id, {', '.join(cols)} FROM regulatory_provisions"
            f" WHERE is_current = true AND source_council = %(council)s AND ({rule['where']})",
            {"council": rule["council"]})
        rows = cur.fetchall()
        n = 0
        for row in rows:
            diff = [(c, row[i + 1], rule["set"][c]) for i, c in enumerate(cols)
                    if row[i + 1] != rule["set"][c]]
            if not diff:
                continue
            n += 1
            changes.extend((row[0], c, before, after, rule["name"]) for c, before, after in diff)
            if apply:
                cur.execute(
                    f"UPDATE regulatory_provisions SET {', '.join(f'{c} = %s' for c, _, _ in diff)}"
                    " WHERE id = %s",
                    [after for _, _, after in diff] + [row[0]])
        print(f"  gate {rule['name']:<29} rows={len(rows):<5} to-change={n}")
    return changes
