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
]

#: Gate rules (spliced into GATE_RULES).
AREA_GATE_RULES: list[dict] = [
    # s2.26's 'generic' rows reached every Marrickville house; they go to the precinct layer, keyed above.
    {"name": "marrickville_2_26_layer", "council": "marrickville",
     "where": _MARRICKVILLE_2_26 + " AND v2_dcp_layer = 'generic'",
     "set": {"v2_dcp_layer": "precinct"}},
]
