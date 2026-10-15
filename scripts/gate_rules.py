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
     "set": {"v2_applicable_zones": ["E3", "SP4"]}},  # noqa: zone-codes (the plan's own zones)
    # "Part 19 applies to any development associated with a Heritage Item or within a Heritage Conservation Area
    # (HCA) identified on the KLEP Heritage Map." (Ku-ring-gai DCP Part 19, p2). Same gate as ashfield_e1_heritage.
    # Recorded limit: 19F's "vicinity of a heritage item" has no land layer, so a lot only adjoining one is not shown it.
    {"name": "krg_19_heritage", "council": "ku_ring_gai",
     "where": "source_chapter_key = 'section-b-part-19-heritage'",
     "set": {"v2_marker": "heritage"}},
]
_GATE_COLUMNS = {"v2_marker", "v2_dcp_layer", "v2_site_condition_required", "v2_applicable_zones"}
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
    {"name": "cb_8_3_hume_highway_by_page", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-8-3-hume-highway'",
     "strategy": {"type": "page_range", "ranges": [("8.3.4", 10, 14), ("8.3.6", 19, 33)]},
     "fingerprint": {"max_page": 42, "min_coverage": 0.6}},
    {"name": "krg_14a_st_ives_by_page", "council": "ku_ring_gai", "validate": False,
     "where": "source_chapter_key = 'section-b-part-14a-st-ives-local-centre'",
     "strategy": {"type": "page_range", "ranges": [
         ("14A", 1, 8), ("14A_S1", 9, 13), ("14A_S2", 14, 19), ("14A_S3", 20, 22)]},
     "fingerprint": {"max_page": 22, "min_coverage": 0.95}},
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


def apply_gate_rules(cur, council: str | None, apply: bool, only: set[str] | None = None) -> list[tuple]:
    """Set each GATE_RULES row's gate columns. Returns (id, column, before, after, rule) per
    changed column, for the backup. Idempotent: a row already holding the values is skipped."""
    changes: list[tuple] = []
    for rule in GATE_RULES:
        if (council and rule["council"] != council) or (only and rule["name"] not in only):
            continue
        unknown = set(rule["set"]) - _GATE_COLUMNS
        if unknown:
            raise ValueError(f"{rule['name']}: not a gate column {sorted(unknown)}")
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
