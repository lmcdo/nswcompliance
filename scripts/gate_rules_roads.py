#!/usr/bin/env python3
"""Gate rules for DCP rows whose own words limit them to lots on a State road or a classified road.

prior-art-checked: split out of scripts/gate_rules.py (at its 500-line limit), which splices ROAD_GATE_RULES into
GATE_RULES; same contract (re-run after every publish, gate columns only, provision_text never touched).

The property lookup flags the lot (frontend-nextjs/lib/classified-road.ts, shared/classified-roads.json):
  'state_road'      -- the lot touches a road corridor carrying a TfNSW State road (admin class 'S');
  'classified_road' -- ... a State road or a classified Regional road (unclassified Regional roads, numbered 7xxx,
                       are NOT classified roads).
A row is gated only when its WHOLE content applies only to such lots. Keyed by row id (exact row); a re-extraction
that changes the id makes the rule match nothing (the row is shown to every lot again, never hidden).

Not gated (2026-10-21 scan of live rows): rows that only mention such roads or name a road; "arterial" / "main
road" wording (not a legal road class); Blacktown "SP2 Infrastructure - Classified Road or Local Road" (zone-based);
clauses and tables with a State/Regional branch AND an other-roads branch (the check would choose a column, not
switch the row: Parramatta 4.3 p145 and 4.6 p158-159, C-B 9.1 2.2 p5 and 2.10 p7, C-B 10.5 4.7 p12 and 7.5 p20,
C-B 3.2 parking schedule note p10); rows with another trigger as well (C-B 10.2 4.11 p13 "Zone E4 ... or
state/regional roads or rail corridors"; Georges River 6.1.4 p42 "within 60m of a railway or facing a classified
major road"; Sydney DCP 4 child care (3) p56 "a classified road, or any other road ..."); C-B 3.6 2.5 pylon signs
p6 (the limit also answers lots with no classified-road boundary); C-B 10.7 2.3 p6 ("within 100m of a state road
listed in the table": a distance and a named list, not frontage); C-B 3.3 waste p10-11 (collection points "must
avoid classified roads": applies to every lot).
"""
from __future__ import annotations

_CLASSIFIED = {"v2_dcp_layer": "condition", "v2_site_condition_required": "classified_road"}
_STATE = {"v2_dcp_layer": "condition", "v2_site_condition_required": "state_road"}

ROAD_GATE_RULES: list[dict] = [
    # Ashfield DCP Chapter F Part 8 DS4.2 (p63): "Child Care Centres proposed on sites adjoining a classified road do
    # not to have vehicular access from that road unless ..."
    {"name": "ashfield_f_ds4_2_classified_road", "council": "ashfield",
     "where": "source_chapter_key = 'chapter-f-dev-category' AND id IN (241411)", "set": _CLASSIFIED},
    # Leichhardt DCP 2013 C3.12 C5 (p32): "For residential developments adjacent to classified roads, developers are
    # to address the requirements of ... Environmental Criteria for Road Traffic Noise ..."
    {"name": "leichhardt_c3_12_c5_classified_road", "council": "leichhardt",
     "where": "source_chapter_key = 'part-c-s3-residential' AND id IN (204967)", "set": _CLASSIFIED},
    # Leichhardt DCP 2013 C4.10 C21 (p31): "Industrial sites with frontage to classified roads must consult with the
    # relevant NSW State Government department as to the appropriate access and egress."
    {"name": "leichhardt_c4_10_c21_classified_road", "council": "leichhardt",
     "where": "source_chapter_key = 'part-c-s4-non-residential' AND id IN (205478)", "set": _CLASSIFIED},
    # Sydney DCP 2012 4.4.2 (11) (p53): "Where an allotment has frontages to a classified road and a local road, the
    # development should provide vehicle access from the local road."
    {"name": "sydney_4_4_2_11_classified_road", "council": "city_of_sydney",
     "where": "source_chapter_key = 'section-4-development-types' AND id IN (178732)", "set": _CLASSIFIED},
    # Wollongong DCP 2009 E3 4.1.2 (p17) control 5: "Where a development site has dual frontage to a classified road
    # and a secondary road, all driveway crossings ... are to be provided via the secondary road ..."; control 6:
    # "In cases where an access to a classified road is permitted, a deceleration lane may be required ..."
    {"name": "wollongong_e3_4_1_2_classified_road", "council": "wollongong",
     "where": "source_chapter_key = 'chapter-e3-car-parking' AND id IN (249273, 249274)", "set": _CLASSIFIED},
    # Hornsby DCP 2024 "Main roads" (1.3.2.1 p24; 3.3.13 p51; 3.4.13 p66; 3.5.13 p99): "Development adjoining roads
    # that are subject to Section 2.119 of the Transport and Infrastructure SEPP require separate approval from
    # Transport for NSW (TfNSW) for access to State and Regional Roads as classified by TfNSW." SEPP 2.119 is
    # development on land with a frontage to a classified road, so 'classified' (unclassified 7xxx excluded).
    {"name": "hornsby_main_roads_classified_road", "council": "hornsby",
     "where": "source_chapter_key IN ('part-1-general', 'hornsby-dcp-2024-part3-residential')"
              " AND id IN (244816, 248066, 248170, 248320)", "set": _CLASSIFIED},
    # Canterbury-Bankstown DCP 2023 10.7 Sex services premises (p13): 9.1 "Sex services premises are not permitted to
    # front state roads."; 9.2 "... may locate in a complex of industrial units which have an entrance on a state
    # road if the individual unit does not have frontage to a state road ...". State roads only: the DCP defines
    # "state road means a roadway under the control of the TfNSW" (3.1, p22) = TfNSW admin class 'S'.
    {"name": "cb_10_7_9_state_road", "council": "canterbury_bankstown",
     "where": "source_chapter_key = 'chapter-10-7-sex-services-premises' AND id IN (161423, 161424)", "set": _STATE},
]

#: The site conditions these rules set; the probes in scripts/dq_probe_live.py must know every one of them.
ROAD_CONDITIONS = ("state_road", "classified_road")
