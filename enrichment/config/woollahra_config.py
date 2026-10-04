"""
Woollahra DCP 2015 Configuration

Structure: per-chapter PDFs, chapter codes A1–F3.
Each chapter PDF has subsection headings of the form "B3.1 Site Coverage" or
"C1.2 Materials", where the chapter code prefix (B3, C1) is the key in `parts`.

Layer assignment:
  generic      — applies to all development regardless of zone or site conditions
  use_specific — applies to specific zones or development types
  condition    — only applies when a site condition flag is set (heritage, flood, etc.)

Zone mapping (DQ-30, .claude/DATA_QUALITY_TRACKER.md — updated to current
zone codes; the previous "LEP 2014" B-zone list below was retired by the
26 April 2023 NSW Employment Zones Reform):
  Woollahra's real current zones, confirmed against lep_zone_coverage:
  C1, C2, E1, MU1, R2, R3, RE1, RE2, SP2, SP3 — ZERO B-zones.
  Zone assignments below use each retired code's current equivalent (see
  enrichment/config/zone_taxonomy.py): B1,B2->E1; B4->MU1.
  (Historical note, no longer accurate: this file previously said
  "Woollahra LEP 2014 zones: R2, R3, B1, B2, B4, SP2, RE1, RE2, E2, E3.")

Source: https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules

Amendment history:
  A2 repealed; C2/C3 were originally separate HCA chapters, subsequently replaced by B2
  (Neighbourhood HCAs); D3 NOT repealed (still in DB); C2 and C3 reinstated at current
  URLs. D5 (Double Bay) not yet in DB. E7/E8/F1/F3 added from extraction.
"""

BASE_URL = "https://www.woollahra.nsw.gov.au/files/assets/public/plans-policies-publications/development-control-plans"

WOOLLAHRA_CONFIG = {
    "council": "woollahra",
    "dcp_name": "Woollahra DCP 2015",

    # Section codes are extracted from the markdown heading injected by the extractor:
    #   "# B3.1 Site Coverage\n\n..." → code "B3.1" → stripped to "B3" → lookup here.
    # Exact match is tried first, then progressive strip, then single-letter prefix.
    "parts": {
        # ── Part A — Introduction & Definitions ─────────────────────────────────
        "A1": {
            "scope_evidence": {
                "applicable_zones":
                    "A1.1.3 'Land where this plan applies', verbatim: 'This plan applies to all land within the Woollahra Municipality.' ALL is the council's own statement here, not a fallthrough.",
                "applicable_dev_types":
                    "A1.1.4 'Development to which this plan applies', verbatim: 'This plan applies to development requiring consent under the Woollahra Local Environmental Plan 2014 (Woollahra LEP 2014).' Any consent-requiring development, so ALL.",
            },
            "layer": "generic",
            "topic": "general",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "A3": {
            "scope_evidence": {
                "applicable_zones":
                    "INHERITED. A1.1.3 'Land where this plan applies', verbatim: 'This plan applies to all land within the Woollahra Municipality.' Chapter A3 is the definitions chapter and states no scope of its own -- read 2026-10-04, its 14 pages are the A3.1 definitions list with no 'Land where this chapter applies' section -- so it takes the plan's.",
                "applicable_dev_types":
                    "INHERITED. A1.1.4 'Development to which this plan applies', verbatim: 'This plan applies to development requiring consent under the Woollahra Local Environmental Plan 2014 (Woollahra LEP 2014).' Chapter A3 states no development scope of its own (read 2026-10-04), so it takes the plan's.",
            },
            "layer": "generic",
            "topic": "general",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },

        # ── Part B — General Residential ────────────────────────────────────────
        "B1": {
            "scope_evidence": {
                "applicable_zones":
                    "B1.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to the following residential precincts:' followed by a two-column list beginning Darling Point, Bellevue Hill South, Bellevue Hill North, Rose Bay, Double Bay, Vaucluse West (quote shortened 2026-10-04 to the words the PDF prints contiguously; the list's two columns interleave in the text layer). The scope is a set of named PRECINCTS, not a zone list -- the geography is carried by v2_precinct_id on each rule. The config declared ['R2','R3']; a precinct can contain land zoned otherwise, and v2_applicable_zones is a HARD filter, so that list silently removed this chapter from any such lot inside a precinct it governs.",
                "applicable_dev_types":
                    "B1.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent. Generally this will be residential development, but may include other permitted uses such as child care centres, community facilities, educational establishments, neighbourhood shops and places of public worship, and other uses permitted in Woollahra LEP 2014.' The council names five non-residential uses and then says 'and other uses permitted', so a six-item residential list hid the chapter from every one of them.",
            },
            "layer": "use_specific",
            "topic": "residential",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "B2": {
            "scope_evidence": {
                "applicable_zones":
                    "B2.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to the following neighbourhood HCAs: Etham Avenue, Darling Point; Darling Point Road, Darling Point; Mona Road, Darling Point [and the remaining HCAs listed].' Mapped heritage conservation areas, not zones; site_conditions ['heritage'] carries the scope, so ALL on zones is correct rather than permissive.",
                "applicable_dev_types":
                    "B2.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent. Generally this will be residential development, but may include other permitted uses such as child care centres, community facilities, educational establishments, neighbourhood shops and places of public worship, and other uses permitted in Woollahra LEP 2014.' ALL is the council's own breadth.",
            },
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },
        "B3": {
            "scope_evidence": {
                "applicable_zones":
                    "B3.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to land identified on Map 1 below.' The scope is a MAP, which neither this config nor the serving path can express as a zone list, so ALL is the non-narrowing answer: a zone list would hide the chapter from land inside Map 1 carrying any other zone.",
                "applicable_dev_types":
                    "B3.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent. This includes new development and additions and alterations. Generally this will be residential development, but may include other permitted uses such as child care centres...' The chapter names non-residential uses itself, so ALL rather than a residential list.",
            },
            "layer": "generic",
            "topic": None,  # topic from text
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        # ZONE LIST CORRECTED 2026-10-03, and it was hiding rules. The config
        # declared ["R3"] alone. B4.1.2 says, verbatim: "This chapter only
        # applies to land zoned R2 Low Density Residential or R3 Medium Density
        # Residential." v2_applicable_zones is a HARD filter in
        # frontend-nextjs/app/api/provisions/for-property/route.ts, not a
        # ranking hint, so every R2 property in Woollahra was served none of
        # this chapter's controls.
        #
        # The E1/E2/MU1 zones named earlier in B4.1.2 are the CENTRES that the
        # 800m walking distance is measured FROM. They are not the land this
        # chapter binds, and declaring them would serve housing controls to
        # commercial lots.
        #
        # DEV TYPES CORRECTED in the same pass, both directions. B4.1.3 names
        # "dual occupancies, multi-dwelling housing, multi-dwelling housing
        # (terraces), residential flat buildings, and shop top housing".
        # dual_occupancy was ABSENT, so a dual occupancy DA missed the chapter;
        # boarding_house was DECLARED although the chapter never names one, so a
        # boarding house DA was served controls the council did not write for it.
        "B4": {
            "layer": "use_specific",
            "topic": "residential",
            "scope_evidence": {
                "applicable_zones":
                    "B4.1.2 'Land where this chapter applies', verbatim: 'This chapter only "
                    "applies to land zoned R2 Low Density Residential or R3 Medium Density "
                    "Residential.' The same section defines accessible areas as 'land within 800m "
                    "walking distance of specified town centres zoned E1 Local Centre, E2 "
                    "Commercial Centre or MU1 Mixed Use' -- those three are the centres measured "
                    "FROM, not the land bound, and are deliberately not declared. The config "
                    "declared R3 alone, which hid the whole chapter from every R2 property.",
                "applicable_dev_types":
                    "B4.1.3 'Development to which this chapter applies', verbatim: 'This chapter "
                    "applies to dual occupancies, multi-dwelling housing, multi-dwelling housing "
                    "(terraces), residential flat buildings, and shop top housing within 800m "
                    "walking distance of specified town centres.' dual_occupancy was missing from "
                    "the declared list; boarding_house was in it although the chapter never names "
                    "a boarding house.",
            },
            "applicable_zones": ["R2", "R3"],  # noqa: zone-codes (the two zones B4.1.2 names as its own scope)
            "applicable_dev_types": [
                "dual_occupancy", "multi_dwelling_housing",
                "residential_flat_building", "shop_top_housing",
            ],
        },

        # ── Part C — Heritage Conservation Areas ────────────────────────────────
        "C1": {
            "scope_evidence": {
                "applicable_zones":
                    "C1.1.2 'Land where this chapter applies', verbatim: 'This chapter applies to the Paddington HCA as identified in Map 1. Parts of the suburbs of Edgecliff and Woollahra are located in the Paddington HCA; this chapter applies to those parts.' A heritage conservation area is a mapped overlay, not a zone, and site_conditions ['heritage'] carries that scope. ALL on zones avoids hiding the HCA from any zone that falls inside it.",
                "applicable_dev_types":
                    "C1.1.3, verbatim: 'This chapter applies to development that requires consent under Woollahra Local Environmental Plan 2014 (Woollahra LEP 2014). Generally this will be residential or commercial development, but may include other permitted uses such as child care centres, community facilities, educational establishments and places of [public worship].' Explicitly non-residential as well, so ALL.",
            },
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },
        "C2": {
            "scope_evidence": {
                "applicable_zones":
                    "C2.1.2 'Land to which this chapter applies', verbatim: 'This chapter applies to the Woollahra Heritage Conservation Area, which is shown in Map 1.' A mapped HCA, not a zone; site_conditions ['heritage'] carries the scope.",
                "applicable_dev_types":
                    "C2.1.3, verbatim: 'This chapter applies to development that requires development consent under Woollahra LEP 2014.' No development type is excluded, so ALL.",
            },
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },
        "C3": {
            "scope_evidence": {
                "applicable_zones":
                    "C3.1.2 'Land where this chapter applies', verbatim: 'This chapter applies to the land identified in Map 1 on the following page. This predominantly comprises land identified as the Watsons Bay HCA in Woollahra Local Environmental Plan 2014 (Woollahra LEP 2014), but also includes other land, such as HMAS Watson.' The scope is WIDER than the HCA itself, which is why no zone list is declared.",
                "applicable_dev_types":
                    "C3.1.3, verbatim: 'This chapter applies to development that requires consent under Woollahra LEP 2014.' ALL.",
            },
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },

        # ── Part D — Business & Mixed Use Centres ───────────────────────────────
        "D1": {
            "scope_evidence": {
                "applicable_zones":
                    "D1.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to the following centres, as identified on Map A (see next page):' then Hopetoun Avenue, Vaucluse; South Head Roundabout, Vaucluse; Vaucluse Shopping Village, Vaucluse; Plumer Road, Rose Bay; O'Sullivan Road, Rose Bay; Streatfield Road, Bellevue Hill and the rest of the list (quote corrected 2026-10-04: the PDF reads 'Map A (see next page)' and lists one centre per line). D1.1.2 names the zone itself: 'A key objective of the E1 zone is to provide a range of small-scale retail, business and community uses that serve the needs of people who live or work in the surrounding neighbourhood.' E1 is the council's own word for these centres.",
                "applicable_dev_types":
                    "D1.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent... The E1 zone permits a limited range of retail premises including shops, restaurants [and the remaining uses listed].' The council's sentence is 'development that requires development consent' and it names COMMUNITY uses alongside retail and business, so a four-item commercial list hid the chapter from community facilities in its own centres.",
            },
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["E1"],  # noqa: zone-codes (the zone D1.1.2 names as its own scope)
            "applicable_dev_types": ["ALL"],
        },
        "D2": {
            "scope_evidence": {
                "applicable_zones":
                    "D2.1 Introduction (PDF p5), verbatim: 'This chapter contains controls for three centres, zoned MU1 Mixed Use under Woollahra Local Environmental Plan 2014', and 'Land where this chapter applies' names the three centres (New South Head Road Corridor, Edgecliff; Rose Bay North; Rose Bay South).",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table.
                "applicable_dev_types":
                    "D2.1 'Development to which this chapter applies' (PDF p6), verbatim: 'This chapter applies to development that requires development consent.' CORRECTED 2026-10-04: the config declared commercial_premises, shop_top_housing and residential_flat_building, which hid this chapter from every other consent-requiring use in these centres -- the error D4, D5 and D6 were already corrected for. The chapter says the zone permits 'a wide range of retail premises, business premises, office premises, community facilities, restaurants and cafes and shop top housing'.",
            },
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["MU1"],  # noqa: zone-codes (the zone D2.1 names as its own scope)
            "applicable_dev_types": ["ALL"],
        },
        "D3": {
            "scope_evidence": {
                "applicable_zones":
                    "D3.1 Introduction (PDF p5), verbatim: 'This chapter contains controls for twelve centres, zoned either E1 Local Centre or MU1 Mixed Use under the Woollahra Local Environmental Plan 2014 (LEP).'",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table.
                "applicable_dev_types":
                    "INHERITED. A1.1.4 'Development to which this plan applies', verbatim: 'This plan applies to development requiring consent under the Woollahra Local Environmental Plan 2014 (Woollahra LEP 2014).' D3 has 'Land where this chapter applies' but no 'Development to which this chapter applies' section (contents, PDF p3, read 2026-10-04), so it takes the plan's.",
            },
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["E1", "MU1"],  # noqa: zone-codes (the zones D3.1 names)
            "applicable_dev_types": ["ALL"],
        },
        "D4": {
            "scope_evidence": {
                "applicable_dev_types":
                    "D4.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent. Generally this will be mixed use retail, business, office and/or residential development, but may also include permitted uses such as child care centres, community facilities, and other uses as permitted by Woollahra LEP 2014.' The declared three-item list omitted child care centres and community facilities, which the chapter names, and omitted the 'other uses as permitted' catch-all entirely.",
                "applicable_zones":
                    "D4.1 Introduction (PDF p5), verbatim: 'This chapter contains controls for the Edgecliff Centre, zoned E1 Local Centre'. CORRECTED 2026-10-04 from MU1: the chapter separates the centre from 'the wider Edgecliff commercial area which includes the land zoned MU1 Mixed Use along New South Head Road' (PDF p8). Checked in the app the same day: the D4.1.1 lots resolve to E1 (SHOP 24A 203-233 New South Head Road; 180 Ocean Street). The third, 235-285 New South Head Road, could not be checked -- the app resolved that address to 582 New South Head Road, Point Piper.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table.
            },
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["E1"],  # noqa: zone-codes (the zone D4.1 names as its own scope)
            "applicable_dev_types": ["ALL"],
        },
        "D5": {
            "scope_evidence": {
                "applicable_dev_types":
                    "D5.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent. Generally this will be mixed use retail, business, office and/or residential development, but may also include permitted uses such as child care centres, community facilities, and other uses as permitted by Woollahra LEP 2014.' The declared list named no residential type at all, so a shop top housing or residential flat building DA in the Double Bay Centre was served none of this chapter.",
                "applicable_zones":
                    "D5.1.1 'Land where this chapter applies' (PDF p5), verbatim: 'This chapter applies to the Double Bay Centre, as identified in Figure 1.' The chapter states its scope as mapped LAND, not a zone, and names no zone anywhere. E1 is MEASURED, not quoted: checked in the app 2026-10-04, 20-38 Bay Street, 2-22 Knox Street and 15-15A Cross Street, Double Bay all resolve to E1. A sample, not the whole mapped area.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table.
            },
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["E1"],  # noqa: zone-codes (measured on the centre land, see evidence)
            "applicable_dev_types": ["ALL"],
        },
        "D6": {
            "scope_evidence": {
                "applicable_dev_types":
                    "D6.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent. Generally this will be mixed use retail, business, office and/or residential development, but may also include permitted uses such as child care centres, community facilities, and other uses as permitted by Woollahra LEP 2014.' Same correction as D4 and D5: the declared list named no residential type although the chapter does.",
                "applicable_zones":
                    "D6.1.1 'Land where this chapter applies' (PDF p5), verbatim: 'This chapter applies to the Rose Bay Centre, as identified in Figure 1.' The chapter states its scope as mapped LAND, not a zone, and names no zone anywhere. E1 is MEASURED, not quoted: checked in the app 2026-10-04, 674-680 New South Head Road, Rose Bay resolves to E1 (a second sample could not be checked: the app resolved 700 New South Head Road to 893). A sample, not the whole mapped area.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table.
            },
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["E1"],  # noqa: zone-codes (measured on the centre land, see evidence)
            "applicable_dev_types": ["ALL"],
        },

        # ── Part E — General Controls for All Development ────────────────────────
        "E1": {
            "scope_evidence": {
                "applicable_zones":
                    "E1.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E1.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires consent and may generate demand for parking, loading or other associated facilities.' Any development can generate parking demand, so ALL; narrowing would drop the parking rates from the development types that most need them.",
            },
            "layer": "generic",
            "topic": "parking",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E2": {
            "scope_evidence": {
                "applicable_zones":
                    "E2.1.1 'Land and development to which this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.' The flood component is narrower by its own words -- 'the flood risk management component of this chapter applies to all land within the Woollahra Municipality that is within a flood risk precinct' -- and that narrowing is carried by site_conditions ['flood'], not by the zone list.",
                "applicable_dev_types":
                    "E2.1.2 'Development types to which this chapter applies', verbatim: 'This chapter applies to all development that requires consent.'",
            },
            "layer": "condition",
            "topic": "environmental",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["flood"],
        },
        "E3": {
            "scope_evidence": {
                "applicable_zones":
                    "E3.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E3.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to tree works proposed to be carried out on or near a prescribed tree. Tree works include pruning any tree part, removing, injuring or willfully destroying a tree, and the like.' The scope is an ACTIVITY and the serving taxonomy has no term for tree works. ALL is recorded deliberately: tree works accompany development of any type, and any narrowing here would hide the tree controls from the applications that trigger them.",
            },
            "layer": "generic",
            "topic": "landscaping",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E4": {
            "scope_evidence": {
                "applicable_zones":
                    "E4.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E4.1.2 'Development to which this chapter applies', verbatim: 'This chapter applies to development that requires development consent.'",
            },
            "layer": "condition",
            "topic": "environmental",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["contamination"],
        },
        "E5": {
            "scope_evidence": {
                "applicable_zones":
                    "E5.1.2 'Land to which this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E5.1.3 'Development types that this chapter applies to', verbatim: 'This chapter applies to development that requires development consent, including development involving demolition and construction.'",
            },
            "layer": "generic",
            "topic": "waste",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E6": {
            "scope_declined": ("applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones":
                    "E6.1.2 'Land where this chapter applies' (PDF p5), verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E6.1.3 'Development types to which this chapter applies' (PDF p5), verbatim: 'commercial development that requires consent;' and 'non-residential development that requires consent;' plus solar energy systems outside, or forming part of other works under, the Transport and Infrastructure SEPP. DECLINED, not ALL: 'non-residential development' is a category the vocabulary has no term for, so no list can express it without hiding the chapter from some non-residential use. Served value stays ALL; the chapter is NOT residential in scope.",
            },
            "layer": "generic",
            "topic": "sustainability",
            "applicable_zones": ["ALL"],
        },
        "E7": {
            "scope_evidence": {
                "applicable_zones":
                    "E7.1.1 'Land where this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E7.1.2 'Development types that this chapter applies to', verbatim: 'Woollahra LEP 2014 only permits building identification signs and business identification signs; general advertising signs are prohibited. This chapter applies to building identification signs and business identification signs that require consent, or that form part of other works that require consent.' That last clause is why ALL stands: signage controls bind a shop fitout, an office or a residential flat building whenever signage forms part of the application, so a signage-only development type would hide them from every such application.",
            },
            "layer": "generic",
            "topic": "signage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E8": {
            "scope_evidence": {
                "applicable_zones":
                    "E8.1.1 'Land where this chapter applies' (PDF p5), verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "E8.1.2 'Development to which this chapter applies' (PDF p5), verbatim: 'This chapter of the DCP applies to the following types of development:' dwelling houses; semi-detached dwellings; dual occupancies; attached dwellings; multi dwelling housing; multi dwelling housing (terraces); manor houses; residential flat buildings; and shop top housing. NARROWED 2026-10-04 from ALL. Semi-detached and attached dwellings have no term in the serving taxonomy (frontend-nextjs/lib/see/devTypeHierarchy.ts), so no query can ask for them and naming the rest hides nothing selectable -- the Georges River 6.1 test.",
            },
            "layer": "generic",
            "topic": "accessibility",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["dwelling_house", "dual_occupancy", "multi_dwelling_housing",
                                     "manor_house", "residential_flat_building", "shop_top_housing"],
        },

        # ── Part F — Land Use Specific Controls ─────────────────────────────────
        "F1": {
            "scope_evidence": {
                "applicable_zones":
                    "F1.1.2 'Land where this chapter applies', verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "F1.1.3 'Development to which this chapter applies', verbatim: 'Development for the purpose of a child care centre requires consent. The controls in this chapter [apply to that development].' The chapter is written for one use, so child_care_centre is the council's own narrowing, not ours.",
            },
            "layer": "use_specific",
            "topic": "child_care",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["child_care_centre"],
        },
        "F2": {
            "scope_evidence": {
                "applicable_zones":
                    "F2.1.2 'Land where this chapter applies' (PDF p5), verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "F2.1.3 'Development to which this chapter applies' (PDF p5), verbatim: 'This chapter applies to development for educational establishments that require consent.' Added 2026-10-04: the chapter had no entry, so its 9 served rows fell to no_config.",
            },
            "layer": "use_specific",
            "topic": "educational",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["educational_establishment"],
        },
        "F3": {
            "scope_declined": ("applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones":
                    "F3.1.1 'Land and development where this chapter applies' (PDF p6), verbatim: 'This chapter applies to all land within the Woollahra Municipality.' CORRECTED 2026-10-04 from E1 and MU1: the chapter also says 'In the Woollahra Municipality there are existing licensed premises located in zones where they are no longer permitted', which are exactly the sites a centre-zone list hid it from.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table.
                "applicable_dev_types":
                    "F3.1.2 'Development to which this chapter applies' (PDF p6), verbatim: 'This chapter applies to all development proposals involving licensed premises.' DECLINED: licensed premises are defined by the Liquor Act, not by land use, and span pubs, hotels, clubs, small bars and licensed restaurants. The previous food_and_drink_premises hid the chapter from a pub or hotel application. No term expresses the licence, so the served value stays ALL.",
            },
            "layer": "use_specific",
            "topic": "licensed_premises",
            "applicable_zones": ["ALL"],
        },
        "F4": {
            "scope_declined": ("applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones":
                    "F4.1.2 'Land where this chapter applies' (PDF p5), verbatim: 'This chapter applies to all land within the Woollahra Municipality.'",
                "applicable_dev_types":
                    "F4.1.3 'Development to which this chapter applies' (PDF p5), verbatim: 'This chapter applies to development for telecommunications facilities that require consent' -- DECLINED: the serving taxonomy has no telecommunications term, so no query can name the one use this chapter is for. Added 2026-10-04: the chapter had no entry, so its 8 served rows fell to no_config.",
            },
            "layer": "use_specific",
            "topic": "telecommunications",
            "applicable_zones": ["ALL"],
        },
    },
}
