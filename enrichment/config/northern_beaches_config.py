"""Warringah DCP 2011 (Northern Beaches) — applicability config.

WHY THIS ONE IS DIFFERENT FROM THE OTHERS IN THIS DIRECTORY
------------------------------------------------------------
The whole DCP is stored as ONE document — `warringah_dcp_2011_full` — so there
is no per-chapter document_id to key on, and the `chapter_topics` shape every
other council here uses cannot express it. That looked like a reason to split
the PDF into Parts and re-extract.

It is not. **The Part is already recorded in every rule's own section
reference**: `# G9.1.5.1.14 C2 Signage`, `# E11 C1 Flood Prone Land`,  # noqa: zone-codes (Warringah DCP PART letters, not NSW zone codes)
`# D23 O4 Signs`. Measured 2026-09-23, `_extract_section_code` reads a code on
1,560 of 1,602 served rows. So this uses the EXISTING `parts` path — the one
Woollahra and Waverley use — which reads that code out of the text and strips it
progressively (`G9.1` -> `G9` -> `G`).

That matters beyond tidiness. Re-extracting to recover structure the data
already holds would have risked the thing `dcp_commit_approved`'s section-loss
guard exists to catch: a re-read has gutted a chapter before. This needed no new
code, no new registry rows, and no change to a single provision's provenance.

WHERE EACH SCOPE COMES FROM
---------------------------
Section A.6 "Parts of the DCP", in the plan's own words:

  * "A series of built form controls, including setbacks and landscaped open
    space, is contained in Part C, D and E" — general controls, binding any
    development.
  * "Part F covers development and activities in certain zones and sensitive
    areas e.g. local and neighbourhood centres" — a scope this file does NOT
    enumerate; see the entry.
  * "Part G applies controls to special areas of Warringah e.g. parts of Dee
    Why, Warringah Mall" and, decisively, "where there is inconsistency with
    Parts C, D and E, the requirements of Part G will prevail."
  * "Part H is a compilation of relevant appendices e.g. carparking and
    vegetation matters."

The G-series are named places — G3 Belrose Corridor, G4 Warringah Mall, G5
Freshwater Village, G6 Dee Why RSL Club, G8 Narrabeen, G9 Frenchs Forest Town
Centre, G10 Low and Mid-Rise Housing Areas. Scoped GEOGRAPHICALLY, so every
development inside one is bound by it: that is a real assertion of universality
on development type, not a fallthrough, and it is recorded as `config_all`.

⚠ WHAT IS DELIBERATELY NOT HERE. 110 served rows carry a bare numeric code
(`# 5.4.7 C9 Basement entries`, `# 8 C5.2 Green roofs`, `# 6 C10.1 Car share`)
which belongs to no Part letter in this plan's structure, and 42 carry no code
at all. Guessing a Part for them to improve the numbers is the behaviour DQ-33
exists to refuse, so they stay unmatched and keep being counted.
"""

#: Section A.3 "Land to which this plan applies", the plan-level sentence every
#: Part below inherits where it states no land of its own (PDF p3, verbatim):
#: "This Plan applies to all land to which Warringah Local Environmental Plan
#: 2011 applies."
_PLAN_LAND = ("Section A.3 'Land to which this plan applies' (PDF p3) verbatim: 'This Plan "
              "applies to all land to which Warringah Local Environmental Plan 2011 applies.' "
              "Section A.2 adds that this is 'the only development control plan that applies to "
              "all land within the Warringah LGA'. ")

NORTHERN_BEACHES_CONFIG: dict = {
    "parts": {
        # Matched before the letter-only fallback, so this wins over "E".
        # Part E11 Flood Prone Land: a SITE CONDITION, not a development type —
        # it binds whatever is proposed on land the flood maps cover.
        "E11": {
            "scope_evidence": {
                "applicable_zones":
                    _PLAN_LAND + "E11 is scoped by the FLOOD MAPS, not by zone, and "
                    "`site_conditions: ['flood']` below is what narrows it. A zone list would "
                    "hide a flood control from every flood-affected lot zoned otherwise.",
                "applicable_dev_types":
                    "E11 binds whatever is proposed on land the flood maps cover; the Part "
                    "enumerates no development type, and naming any would drop the flood "
                    "controls from every type left out.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
            "site_conditions": ["flood"],
        },

        # Part A Introduction and administration: objectives, interpretation,
        # how the Parts relate. Binds every application by construction.
        "A": {
            "scope_evidence": {
                "applicable_zones": _PLAN_LAND + "Part A is where that sentence is printed.",
                "applicable_dev_types":
                    "Part A is introduction, interpretation and administration -- objectives, "
                    "abbreviations, how the Parts relate -- so it binds every application by "
                    "construction and names no development type.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
        },

        # PART B — ADDED 2026-10-03. Its absence is what put 43 served rows in
        # `filtered_to_all`: with no entry the config path returns None, text
        # extraction runs, and "B1"/"B2" in "# B1 C1 Wall Heights" are read as
        # NSW zone codes. See the module docstring.
        "B": {
            "scope_evidence": {
                "applicable_zones":
                    "Part B Built Form Controls, control B1 Wall Heights 'Applies to Land' (PDF "
                    "p15) verbatim: 'This control applies to all land identified on the Warringah "
                    "Local Environmental Plan 2011 - Land Zoning Map as: RU4 Primary Production "
                    "Small Lots / R2 Low Density Residential / E3 Environmental Management / E4 "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "Environmental Living and to which an 8.5m maximum height of building control "
                    "applies under LEP 2011.' That is ONE control's scope, not the Part's: B2 "
                    "Number of Storeys and B10 Merit Assessment of Rear Boundary Setbacks each "
                    "state their own, and this entry governs all of them through the progressive "
                    "strip. It also must not be declared as written: 'E3 Environmental "
                    "Management' and 'E4 Environmental Living' are the PRE-2023 names. The "
                    "employment-zone reform renamed them C3 and C4, and E3 and E4 now mean "  # noqa: zone-codes - names the PRE-2023 codes in order to say why they must NOT be declared; introduces no list.
                    "Productivity Support and General Industrial -- both of which EXIST for this "
                    "LGA -- so declaring E3/E4 would bind wall-height controls for bushland "  # noqa: zone-codes - names the PRE-2023 codes in order to say why they must NOT be declared; introduces no list.
                    "housing to industrial land. That is the trap wollongong_config.py records "
                    "for the same pair. ALL is the non-hiding answer.",
                "applicable_dev_types":
                    "B1's scope sentence qualifies land and an LEP height control, not a "
                    "development type, and no B control names one. These are built-form controls "
                    "-- wall heights, number of storeys, setbacks -- which bind whatever is "
                    "built.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
        },

        # Parts C, D and E — "a series of built form controls, including
        # setbacks and landscaped open space". General, so ALL is a decision.
        "C": {
            "scope_evidence": {
                "applicable_zones":
                    "Part C Siting Factors, first control 'Applies to Land' (PDF p27) verbatim: "
                    "'This control applies to all land shown on the Warringah Local Environmental "
                    "Plan 2011 - Land Application Map other than land that is shown as \'Deferred "
                    "matter\'.' The LEP's whole extent less the deferred matter, which is an area "
                    "on the Land Application Map and not a zone. (The deferred-matter exclusion "
                    "is real and is DQ-120's subject for another council; it is not expressible "
                    "as a zone list.)",
                "applicable_dev_types":
                    "Section A.6 'Parts of the DCP' verbatim: 'A series of built form controls, "
                    "including setbacks and landscaped open space, is contained in Part C, D and "
                    "E.' Siting controls bind any development on the land; no type is named.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
        },
        "D": {
            "scope_evidence": {
                "applicable_zones":
                    "Part D Design, control-level 'Applies to Land' repeated verbatim through the "
                    "Part (PDF p40, p43, p46, p48 and on): 'This control applies to land to which "
                    "Warringah Local Environmental Plan 2011 applies.' " + _PLAN_LAND,
                "applicable_dev_types":
                    "Section A.6 verbatim: 'A series of built form controls, including setbacks "
                    "and landscaped open space, is contained in Part C, D and E.' Design controls "
                    "bind any development; no type is named anywhere in the Part.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
        },
        "E": {
            "scope_evidence": {
                "applicable_zones":
                    "Part E The Natural Environment, control-level 'Applies to Land' (PDF p71, "
                    "p74) verbatim: 'This control applies to land to which Warringah Local "
                    "Environmental Plan 2011 applies.' One control narrows to a DCP map rather "
                    "than a zone -- p75: 'This control applies to all land shown on DCP Map Land "
                    "Adjoining Public Open Space' -- which a zone list cannot express either.",
                "applicable_dev_types":
                    "Section A.6 verbatim: 'A series of built form controls, including setbacks "
                    "and landscaped open space, is contained in Part C, D and E.' No development "
                    "type is named.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
        },

        # Part F — DECLARED 2026-10-03. It was omitted on the grounds that the
        # plan "names 'certain zones' without listing them". F1 lists them; they
        # are retired codes. See the module docstring.
        "F": {
            "scope_evidence": {
                "applicable_zones":
                    "Part F Zones and Sensitive Areas, F1 Local and Neighbourhood Centres "
                    "'Applies to Land' (PDF p90) verbatim: 'This control applies to land "
                    "identified as zone B1 Neighbourhood Centre or B2 Local Centre on the "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "Warringah Local Environmental Plan 2011 - Land Zoning Map.' The zones ARE "
                    "listed -- section A.6's looser 'certain zones' is why this entry was "
                    "previously left undecided -- but BOTH codes were retired by the "
                    "employment-zone reform and neither exists for this LGA in lep_zone_coverage. "
                    "They also both map onto E1 Local Centre, so the translation is not "
                    "one-to-one and belongs in zone-migration data with its own citation, not "
                    "here. Declaring the retired codes would be rejected by the DQ-30 filter and "
                    "land the rows back in `filtered_to_all`. ALL is the non-hiding answer.",
                "applicable_dev_types":
                    "F1's objectives name a mix rather than a type, verbatim: 'To provide a range "
                    "of small-scale shops and business uses at street level with offices or "
                    "low-rise shop-top housing to create places with a village-like atmosphere.' "
                    "Its requirements then address named centres -- Forestville, The Strand Dee "
                    "Why, Pittwater Road Collaroy, Forestway Shops -- as places, covering 'retail, "
                    "commercial, housing and community uses'. Community uses have no vocabulary "
                    "term, so any list would drop part of what the Part itself names.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },

        # Part G — special areas, and it PREVAILS over C, D and E where they
        # conflict. G1..G10 all reach this through the progressive strip.
        "G": {
            "scope_evidence": {
                "applicable_zones":
                    "Part G Special Area Controls scopes each area by PLACE, verbatim: 'This part "
                    "applies to land identified in the B4 Mixed Use Zone under Warringah Local "
                    "Environmental Plan 2011 (WLEP 2011) and known as the Dee Why Town Centre, as "
                    "shown in Figure 1' (PDF p95); 'This part applies to land at Belrose shown "
                    "outlined on the figure below' (p112); 'This part applies to land Zoned R2 "
                    "Low Density Residential in Warringah Local Environmental Plan 2011 and known "
                    "as the Evergreen Estate at 26 Campbell Avenue Cromer' (p158); 'This part "
                    "applies to land at Nos. 1294, 1296, 1298, 1300 Pittwater Road, and Nos. 2 "
                    "and 4 Albert Street, Narrabeen' (p168). A FIGURE or an address list, which a "
                    "zone list cannot express -- and the one zone named, B4 Mixed Use, is a "
                    "retired code. `is_precinct_specific` carries the geography.",
                "applicable_dev_types":
                    "Section A.6 verbatim: 'Part G applies controls to special areas of Warringah "
                    "e.g. parts of Dee Why, Warringah Mall' and 'where there is inconsistency "
                    "with Parts C, D and E, the requirements of Part G will prevail.' Scoped "
                    "geographically, so every development inside a named area is bound: a real "
                    "assertion of universality on development type.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
            "is_precinct_specific": True,
        },

        # Part H — appendices (carparking, vegetation). Referenced by the
        # controls above rather than scoped away from them.
        "H": {
            "scope_evidence": {
                "applicable_zones":
                    _PLAN_LAND + "Part H states no land of its own. Section A.6 verbatim: 'Part H "
                    "is a compilation of relevant appendices e.g. carparking and vegetation "
                    "matters.' It is referenced BY the controls above rather than scoped away "
                    "from them, so it inherits the plan's extent.",
                "applicable_dev_types":
                    "An appendix of carparking rates and vegetation schedules, reached from "
                    "whichever control cites it, so it binds whatever that control binds and "
                    "names no type itself.",
            },
            "applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
        },
    },
}
