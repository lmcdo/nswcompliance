"""Area keying + layer rules kept beside gate_rules.py (over its 500-line limit); gate_rules.py splices these in.

prior-art-checked: same rule shapes as gate_rules.GATE_RULES / EXTRA_KEY_RULES; no new mechanism.
"""
from __future__ import annotations

_MARRICKVILLE_2_26 = "source_chapter_key = 'part2-s26-entertainment-precincts'"

#: Precinct-keying rules (spliced into EXTRA_KEY_RULES).
AREA_KEY_RULES: list[dict] = [
    # Marrickville DCP 2011 s2.26: "Section 2.26 applies to land identified as a Sound Category Area in the following
    # maps" (p1, Figures 2.26.1-2.26.5). Each figure = pink Special Entertainment Precinct blocks + Category 1-3 street
    # lines. Outline = the IWLEP 2022 SEP polygons those figures cover (marrickville_2_26_sep.geojson, 97 polygons), so
    # a lot inside the pink is served the section for sure; other houses in the figures' suburbs see it in the
    # "may apply" box (area marrickville-2-26-sound-category-areas, SOUND_AREA_MAP) -- the street lines are not drawn.
    {"name": "marrickville_2_26_entertainment_precincts", "council": "marrickville", "validate": False,
     "where": _MARRICKVILLE_2_26,
     "strategy": {"type": "constant", "precinct_id": "Marrickville 2.26 entertainment precinct"}},
    # C-B DCP Ch 6.2 Section 6.8 "KS8- 212 South Terrace" (p182 only; KS9 starts p183): "The 212 South Terrace key site
    # is situated at the eastern edge of the City Centre, at the corner of South Terrace and Stacey Street" (p182).
    # Outline = the parcel under the register's 212 SOUTH TERRACE BANKSTOWN point (7,629 m2), matched to the red key
    # site boundary of Figure 80 (IoU 0.99): data/site_chapters/address_sites.json, build_site_boundaries --addresses.
    # The other key sites (p167-181, p183-213) stay unkeyed in the "may apply" box (area cb-6-2-key-sites).
    {"name": "cb_6_2_ks8_212_south_terrace", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-6-2-bankstown-city-centre' AND pdf_page = 182",
     "strategy": {"type": "constant", "precinct_id": "6.2 KS8"}},
    # C-B DCP 2023 Ch 11.5 Riverlands: "Chapter 11.5 of this DCP applies to the site as shown in the Land Application
    # Map (Figure 1a)" (p4) -- every section. Outline: site_map_11_5.geojson (Figure 1a fitted to the cadastre, shape
    # 0.991, 83 ha; lot-line share 0.439 accepted by the user 2026-10-21, recorded in the file). Rows already 'precinct'.
    {"name": "cb_11_5_riverlands", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-11-5-riverlands'",
     "strategy": {"type": "constant", "precinct_id": "11.5"}},
    # C-B DCP 2023 Ch 11.6 Potts Hill: "applies to the former Potts Hill Reservoir site, Potts Hill as shown in Figure 1"
    # (p4) -- every section. Outline: site_map_11_6.geojson (Figure 1 fitted to the cadastre, shape 0.992, 23 ha;
    # lot-line share 0.449 accepted by the user 2026-10-21, recorded in the file). Rows already 'precinct'.
    {"name": "cb_11_6_potts_hill", "council": "canterbury_bankstown", "validate": False,
     "where": "source_chapter_key = 'chapter-11-6-potts-hill'",
     "strategy": {"type": "constant", "precinct_id": "11.6"}},
]

#: Gate rules (spliced into GATE_RULES).
AREA_GATE_RULES: list[dict] = [
    # s2.26's 'generic' rows reached every Marrickville house; they go to the precinct layer, keyed above.
    {"name": "marrickville_2_26_layer", "council": "marrickville",
     "where": _MARRICKVILLE_2_26 + " AND v2_dcp_layer = 'generic'",
     "set": {"v2_dcp_layer": "precinct"}},
]
