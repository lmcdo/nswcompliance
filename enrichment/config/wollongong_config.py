"""Wollongong DCP 2009 — applicability config.

WHY THIS EXISTS
---------------
Wollongong's chapters were read 2026-09-24 but nothing could serve: with no
config every row would apply to every development type by fallthrough
(`no_config`, the DQ-105 failure). Plan ce-citation-integrity §7 step 6.

Every scope below is quoted from the chapter's own scope section in the PDF the
registry points at, read 2026-09-25 -- not inferred from its title (see the
Hornsby config for why that matters).

BOTH KEYS ARE HARD FILTERS on the served answer, so a key is declared only where
the chapter states it. A chapter that states no scope keeps `layer` only, so
its entry stays truthy and resolves to `config_silent`, not `no_config`.

The LGA's zone list is not copied here: query lep_zone_coverage (lga
like 'wollongong%').
"""

WOLLONGONG_CONFIG: dict = {
    "chapter_topics": {
        # A1 s5, verbatim: "This plan applies to all lands within the Wollongong LGA."
        "chapter_a1_introduction": {
            "scope_evidence": {
                "applicable_dev_types":
                    "A1 s5, verbatim: 'This plan applies to all lands within the Wollongong LGA.'",
                "applicable_zones":
                    "A1 s5, verbatim: 'This plan applies to all lands within the Wollongong LGA.'",
            },
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },

        # B1 s1, verbatim: "This chapter of the DCP applies to all residential
        # zoned land within the City of Wollongong Local Government Area (LGA)
        # including E4 Environmental Living." R1-R5 are the residential zones
        # that exist for this LGA. The chapter's "E4 Environmental Living" is the
        # PRE-2023 code: the NSW employment-zone reform renamed it C4, and E4 now
        # means General Industrial -- declaring "E4" would bind these dwelling
        # controls to industrial land. applicable_dev_types is OMITTED: sections
        # 4-6 each cover different types, and the chapter as a whole names none.
        "chapter_b1_residential": {
            "scope_declined": ("applicable_dev_types",),
            "scope_evidence": {
                "applicable_dev_types":
                    "B1 section 1 Introduction (PDF p3) verbatim: 'This chapter contains "
                    "residential development controls for dwelling-house, secondary dwelling, "
                    "semi-detached dwelling, dual occupancy, attached dwelling, multi-dwelling "
                    "housing (villas and townhouses), residential flat building developments in "
                    "standard residential zones.' The same page scopes its sections: 'Section 4 "
                    "provides general development controls which apply to the erection of all "
                    "dwelling-house, dual occupancy, secondary dwelling, ancillary structures "
                    "and semi detached dwellings within urban areas. Section 5 provides "
                    "controls for Attached dwellings and Multi-dwelling housing. Section 6 "
                    "provides controls for Residential Flat Buildings.' Five of the seven types "
                    "have a vocabulary term; semi-detached and attached dwellings have none, "
                    "and neither appears in the serving taxonomy, so nothing can ask for them. "
                    "The reason the five are NOT declared is section 4's 'ancillary "
                    "structures': `fence`, `carport`, `pool` and `deck` ARE selectable "
                    "devTypeTags (frontend-nextjs/lib/see/ancillaryWorks.ts:17-20), so a "
                    "five-term list would delete section 4 from every one of them. ALL is the "
                    "chapter's own breadth, read 2026-10-03; previously OMITTED, which recorded "
                    "`config_silent` on 584 served rows -- DQ-114's largest single population.",
                "applicable_zones":
                    "B1 s1, verbatim: 'This chapter of the DCP applies to all residential zoned land within the City of Wollongong Local Government Area (LGA) including E4 Environmental Living.' R1-R5 are the residential zones that exist for this LGA. The chapter's 'E4 Environmental Living' is the PRE-2023 code: the NSW employment-zone reform renamed it C4, and E4 now means General Industrial -- declaring 'E4' would bind these dwelling controls to industrial land. applicable_dev_types is OMITTED: sections 4-6 each cover different types, and the chapter as a whole names none.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table. The zone names are the council's own words; rewriting them to import from the taxonomy would falsify the quote.
            },
            "applicable_zones": ["R1", "R2", "R3", "R4", "R5", "C4"],  # noqa: zone-codes (quoted scope; E4 renamed C4 in 2023)
            "layer": "generic",
        },

        # E3 s1.1.2, verbatim: "This DCP Chapter applies to any development
        # requiring development consent under Part 4 or approval under Part 5 of
        # the Environmental Planning and Assessment Act 1979 in the Wollongong
        # Local Government Area (LGA)."
        "chapter_e3_car_parking": {
            "scope_evidence": {
                "applicable_dev_types":
                    "E3 s1.1.2, verbatim: 'This DCP Chapter applies to any development requiring development consent under Part 4 or approval under Part 5 of the Environmental Planning and Assessment Act 1979 in the Wollongong Local Government Area (LGA).'",
                "applicable_zones":
                    "E3 s1.1.2, verbatim: 'This DCP Chapter applies to any development requiring development consent under Part 4 or approval under Part 5 of the Environmental Planning and Assessment Act 1979 in the Wollongong Local Government Area (LGA).'",
            },
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },

        # E6 s1 states no land or development scope: it "outlines Council's
        # requirements for the lodgement of landscaping plans ... in support of
        # a Development Application". BOTH keys are ["ALL"] -- declared 2026-10-03,
        # and here ALL is the literal reading rather than a concession: a chapter
        # governing any application that needs a landscaping plan, named as read
        # alongside the residential, subdivision, mixed-use, business AND industrial
        # chapters, binds every land use. They were OMITTED, which records
        # `config_silent` ("nobody decided") on 248 served keys, counted by DQ-114.
        "chapter_e6_landscaping": {
            "scope_evidence": {
                "applicable_zones":
                    "E6 section 1 Introduction (PDF p3) verbatim: 'This chapter outlines "
                    "Council's requirements for the lodgement of landscaping plans and other "
                    "information in support of a Development Application.' No land is named. "
                    "The same section lists the chapters it is read with -- 'A1 Introduction; "
                    "B1 Residential Development; B2 Residential Subdivision; B3 Mixed Use "  # noqa: zone-codes - DCP chapter keys (B1 Residential Development, B2 Residential Subdivision, ...), not zone codes.
                    "Development; B4 Development in Business Zones; B5 Industrial Development; "  # noqa: zone-codes - DCP chapter keys (B1 Residential Development, B2 Residential Subdivision, ...), not zone codes.
                    "E2 Crime Prevention Through Environmental Design; E11 Heritage "
                    "Conservation; E15 Water Sensitive Urban Design; E17 Management of Trees; "
                    "and E22 Riparian Land Management' -- which spans residential, business and "
                    "industrial land. ALL is the chapter's own reach, not a fallthrough.",
                "applicable_dev_types":
                    "The same sentence is the development scope: the chapter attaches to 'a "
                    "Development Application' generally, and its objective (a) is 'To define "
                    "the landscaping provisions necessary for the Development Application "
                    "process.' It enumerates no development type anywhere, and naming any "
                    "would delete a landscaping requirement from every application left out. "
                    "Read 2026-10-03. Note for the extraction ledger, not this decision: PDF "
                    "p2 of this chapter has no text layer at all.",
            },
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },

        # E11 s3, verbatim: applies "where: (i) An item of environmental heritage
        # as listed under Schedule 5 ... is contained; or (ii) The land is located
        # within one of the Heritage Conservation Areas ...; or (iii) The land is
        # located adjacent to or within the vicinity of a heritage item". A site
        # condition, not a zone or a use.
        "chapter_e11_heritage_conservation": {
            "scope_evidence": {
                "applicable_dev_types":
                    "E11 s3, verbatim: applies 'where: (i) An item of environmental heritage as listed under Schedule 5 ... is contained; or (ii) The land is located within one of the Heritage Conservation Areas ...; or (iii) The land is located adjacent to or within the vicinity of a heritage item'. A site condition, not a zone or a use.",
                "applicable_zones":
                    "E11 s3, verbatim: applies 'where: (i) An item of environmental heritage as listed under Schedule 5 ... is contained; or (ii) The land is located within one of the Heritage Conservation Areas ...; or (iii) The land is located adjacent to or within the vicinity of a heritage item'. A site condition, not a zone or a use.",
            },
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },

        # E17 s3, verbatim: "This Chapter of the DCP applies to all lands within
        # the City of Wollongong Local Government Area." s4 splits the approval
        # PATHWAY by rural/non-rural land, not whether the chapter applies.
        "chapter_e17_trees_and_vegetation": {
            "scope_evidence": {
                "applicable_dev_types":
                    "E17 s3, verbatim: 'This Chapter of the DCP applies to all lands within the City of Wollongong Local Government Area.' s4 splits the approval PATHWAY by rural/non-rural land, not whether the chapter applies.",
                "applicable_zones":
                    "E17 s3, verbatim: 'This Chapter of the DCP applies to all lands within the City of Wollongong Local Government Area.' s4 splits the approval PATHWAY by rural/non-rural land, not whether the chapter applies.",
            },
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },
    },
}
