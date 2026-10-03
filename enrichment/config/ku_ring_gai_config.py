"""
Ku-ring-gai Development Control Plan 2024 Configuration

Structure: Single consolidated DCP (adopted March 2024) with three sections:
  Section A — Residential & General (Parts 1–13)
  Section B — Character Areas & Environmental (Parts 15–20)
  Section C — Design & Technical Standards (Parts 21–25)

Per-Part PDFs uploaded as separate chapters. Parts 10, 11, and 14A-14O
(Child Care, Sex Industry, 15 precinct PDFs) excluded from initial onboarding.

chapter_topics keys are substrings matched against document_id.lower().
document_id pattern: "ku_ring_gai_dcp_2024__{chapter_key_underscored}"
Hyphens in chapter_key are normalised to underscores in document_id.

Note: "part_4_1" must appear before any "part_4" key in the dict to prevent
the shorter key matching Part 4.1 documents first.

Source: https://www.krg.nsw.gov.au/Development/Planning-controls/Development-Control-Plan
"""

#: Why no entry below declares a zone. Every Part was read 2026-10-03 and not one
#: states a zone: they scope themselves by development, by a mapped category, or
#: by a named place. The plan-level sentence cannot be quoted either --
#: `part-1-introduction` carries r2_public_pdf_url NULL in dcp_chapter_registry,
#: so the document that would hold it is not in our corpus. Declaring
#: Ku-ring-gai's R-codes from a Part's title would be the mistake
#: waverley_config.py records: an inference that silently hides rules.
_NO_ZONE = ("This Part states NO zone. Read 2026-10-03. Ku-ring-gai's plan-level sentence "
            "cannot be quoted as inherited scope either, because `part-1-introduction` is "
            "registered with r2_public_pdf_url NULL and is not in our corpus -- so ALL records "
            "that no zone narrowing is stated, which is checkable, rather than a zone list "
            "inferred from the Part's title. Its own scope sentence is: ")

KU_RING_GAI_CONFIG = {
    "council": "ku_ring_gai",
    "dcp_name": "Ku-ring-gai DCP 2024",
    "chapter_topics": {
        # Part 1 and Part 25 are deliberately left undeclared: neither serves an
        # unscoped rule, and `part-1-introduction` has no PDF in the registry, so
        # a declaration here would be a DQ-115 key with nothing behind it.
        "part_1_introduction":          {"layer": "generic",      "topic": None},

        # ── Section A: Residential & General ───────────────────────────────
        "part_2_site_analysis": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'Development applications are to contain a site "
                    "analysis that includes: i) a sketch/diagrammatic plan with a legend' "
                    "(PDF p3) -- it binds the APPLICATION, not land.",
                "applicable_dev_types": "Same sentence (PDF p3): 'Development applications are to "
                    "contain a site analysis'. Every DA, with no type named; the Part also "
                    "requires the application to 'show how the proposed development responds to "
                    "the site analysis'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": None,
        },
        "part_3_subdivision": {
            "scope_declined": ("applicable_zones", "applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This part applies to the subdivision of land "
                    "identified on the \"Minimum Lot Depth Map\" (Refer to maps in 3R.1 of this "
                    "Part)' (PDF p5) -- a MAP, which a zone list cannot express.",
                "applicable_dev_types": "The same sentence scopes it to 'the subdivision of "
                    "land'. `subdivision` is selectable in the DA scope input "
                    "(frontend-nextjs/lib/see/worksScope.ts, field is_subdivision), so declaring "
                    "it would be a truthful narrowing -- recorded as a candidate and NOT made "
                    "here, because narrowing hides and this change widens nothing.",
            },
            "layer": "generic", "topic": None,
        },
        # DQ-30 (.claude/DATA_QUALITY_TRACKER.md): these were labelled
        # "use_specific" but never had applicable_dev_types set, so
        # _get_config_driven() silently defaulted every one to ALL/ALL
        # regardless of the label — genuinely dev-type-specific rules showed
        # for every dev type. Fixed for the 5 parts below because each
        # part's own name IS the dev type, in the tagger's own vocabulary
        # (DEV_TYPE_PATTERNS in applicability_tagger.py) — not an
        # interpretation, just wiring the name that was already there.
        #
        # 2026-10-03: their ZONE key was still silent, and is declared below.
        # "part_4_1" must stay ahead of "part_4" — substring matching.
        "part_4_1_secondary_dwellings": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part provides guidance for development of "
                    "secondary dwellings to meet the aims and objectives within the KLEP' "
                    "(INTRODUCTION, PDF p2).",
                "applicable_dev_types": "The same sentence names the development: 'development of "
                    "secondary dwellings'. `secondary_dwelling` is the vocabulary's own term, so "
                    "the declaration is the Part's own words rather than an interpretation.",
            },
            "applicable_dev_types": ["secondary_dwelling"],
            "layer": "use_specific", "topic": "residential",
        },
        "part_4_dwelling_houses": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part applies to development for a detached "
                    "dwelling house and development ancillary to a dwelling house' (PDF p2).",
                "applicable_dev_types": "The same sentence (PDF p2) verbatim: 'This Part applies "
                    "to development for a detached dwelling house and development ancillary to a "
                    "dwelling house.' `dwelling_house` is the vocabulary's own term. Note the "
                    "'ancillary' half: fence, carport, pool and deck all expand up to "
                    "dwelling_house through frontend-nextjs/lib/see/devTypeHierarchy.ts, so the "
                    "single term does not hide the ancillary controls.",
            },
            "applicable_dev_types": ["dwelling_house"],
            "layer": "use_specific", "topic": "residential",
        },
        "part_5_dual_occupancy": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part applies to development for dual "
                    "occupancy dwellings and associated ancillary development' (PDF p2).",
                "applicable_dev_types": "PDF p2 verbatim: 'This Part applies to development for "
                    "dual occupancy dwellings and associated ancillary development. Applications "
                    "for semi-detached dwellings are to be considered under this Part.' "
                    "`dual_occupancy` is declared; SEMI-DETACHED has no term in the vocabulary "
                    "and none in the serving taxonomy either, so nothing can ask for it and the "
                    "single term hides nothing a query can express.",
            },
            "applicable_dev_types": ["dual_occupancy"],
            "layer": "use_specific", "topic": "residential",
        },
        "part_6_multi_dwelling": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is titled 'MULTI DWELLING HOUSING' and "
                    "its controls bind 'all development regardless of the steepness of the site' "
                    "(PDF p29); no land is named anywhere.",
                "applicable_dev_types": "The Part's own name is the development type and it is "
                    "the vocabulary's own term, `multi_dwelling_housing` -- the DQ-30 wiring "
                    "recorded in the comment above, not an interpretation.",
            },
            "applicable_dev_types": ["multi_dwelling_housing"],
            "layer": "use_specific", "topic": "residential",
        },
        "part_7_residential_flat": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'The objectives and controls in this Part guide "
                    "development for residential flat buildings in meeting the aims and "
                    "objectives within the KLEP' (PDF p2).",
                "applicable_dev_types": "PDF p2 verbatim: 'The objectives and controls in this "
                    "Part guide development for residential flat buildings in meeting the aims "
                    "and objectives within the KLEP. The development of residential flat "
                    "buildings is covered by this Part.' `residential_flat_building` is the "
                    "vocabulary's own term.",
            },
            "applicable_dev_types": ["residential_flat_building"],
            "layer": "use_specific", "topic": "residential",
        },
        # part_8_mixed_use and part_9_non_residential are still NOT narrowed on
        # development type: "mixed use" and "non-residential" each span several
        # types, and the Parts name uses the vocabulary cannot express.
        "part_8_mixed_use": {
            "scope_declined": ("applicable_zones", "applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'The objectives and controls in this Part guide "
                    "development of retail, business and mixed use buildings in meeting the aims "
                    "and objectives within the KLEP' (PDF p2).",
                "applicable_dev_types": "PDF p2 verbatim: 'The objectives and controls in this "
                    "Part guide development of retail, business and mixed use buildings in "
                    "meeting the aims and objectives within the KLEP.' Three categories, and "
                    "'mixed use buildings' is not a type at all -- its own section 8C.14 scopes "
                    "by composition rather than use: 'This section applies to all development "
                    "that: i) does not provide commercial uses to the entire ground floor' (PDF "
                    "p15). `retail_premises` and `commercial_premises` exist, but a two-term "
                    "list would drop the mixed-use half the Part is named for. ALL.",
            },
            "layer": "use_specific", "topic": None,
        },
        "part_9_non_residential": {
            "scope_declined": ("applicable_zones", "applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part 'applies to all buildings that are "
                    "soley non-residential, including office building developments' (PDF p2; the "
                    "spelling is the council's).",
                "applicable_dev_types": "PDF p2 verbatim: this Part 'applies to all buildings "
                    "that are soley non-residential, including office building developments. "
                    "Where a development involves refurbishment works or alterations/[additions]'. "
                    "'All buildings that are solely non-residential' is a category, not a type: "
                    "it reaches every non-residential use the LEP permits, and the vocabulary "
                    "has terms for only a handful of them. Naming those would delete the Part "
                    "from every other non-residential use. ALL.",
            },
            "layer": "use_specific", "topic": None,
        },
        "part_12_signage": {
            "scope_declined": ("applicable_zones", "applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'Part 12 relates to signage for identification "
                    "and advertising purposes' (INTRODUCTION, PDF p2).",
                "applicable_dev_types": "PDF p2 verbatim: 'Part 12 relates to signage for "
                    "identification and advertising purposes.' Signage attaches to whatever is "
                    "being built or occupied, and `signage` is an ANCILLARY devTypeTag in the DA "
                    "scope input (frontend-nextjs/lib/see/ancillaryWorks.ts:24) rather than a "
                    "primary type, so declaring it as a primary type would hide the Part from "
                    "every application that carries signage alongside another use. ALL.",
            },
            "layer": "generic", "topic": "signage",
        },
        "part_13_trees": {
            "scope_declined": ("applicable_zones", "applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part establishes 'a framework for the "
                    "submission of applications for tree and other vegetation works in "
                    "Ku-ring-gai' (PDF p3) -- the whole LGA, by its own words, and no zone.",
                "applicable_dev_types": "PDF p3 verbatim: the Part is 'establishing a framework "
                    "for the submission of applications for tree and other vegetation works in "
                    "Ku-ring-gai ... Where a development application is required, the works will "
                    "be assessed as part of the Development Application'. It binds any "
                    "application involving tree works; `trees` is an ancillary devTypeTag, not a "
                    "primary type, so it cannot be declared here without hiding the Part.",
            },
            "layer": "generic", "topic": "trees",
        },

        # ── Section B: Character Areas & Environmental ──────────────────────
        "part_15_contamination": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part covers 'applications, rezoning and "
                    "remediation works on contaminated land' (PDF p2) -- CONTAMINATED LAND is a "
                    "site condition, not a zone.",
                "applicable_dev_types": "PDF p2 verbatim: the Part addresses 'applications, "
                    "rezoning and remediation works on contaminated land' and exists 'to ensure "
                    "that changes to land use will not' create risk. Scoped by the land's "
                    "condition, so it binds whatever is proposed on it.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "contamination",
        },
        "part_16_bushfire": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part guides development on land identified "
                    "on the Ku-ring-gai Bushfire Prone Land Map and/or to land identified on the "
                    "Ku-ring-gai Bushfire Risk Evacuation Map' (INTRODUCTION, PDF p2) -- two "
                    "MAPS, which a zone list cannot express.",
                "applicable_dev_types": "The same sentence guides 'development' on the mapped "
                    "land and names no type; it extends further by its own words -- 'For other "
                    "areas not identified as bush fire prone land but within 700m proximity of "
                    "the aforementioned, the controls are recommended'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "bushfire",
        },
        "part_17_riparian": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part guides development on land "
                    "identified within the Natural Resource - Riparian Lands Map in the KLEP "
                    "(see clause 6.4) and supports the achievement of the aims and objectives "
                    "within the LEP' (INTRODUCTION, PDF p2) -- a MAP, which a zone list cannot "
                    "express.",
                "applicable_dev_types": "Its controls bind land-shaping and layout whatever the "
                    "use -- PDF p3: 'Subdivisions and amalgamations are to provide for a "
                    "development footprint outside the riparian land' -- and no development type "
                    "is named.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "stormwater",
        },
        "part_18_biodiversity": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'The objectives and controls in this Part "
                    "applies to development activities or works that will have an impact on areas "
                    "identified as Greenweb, mapped in this DCP' (PDF p3; the grammar is the "
                    "council's) -- a MAP, not a zone.",
                "applicable_dev_types": "The same sentence scopes it to 'development activities "
                    "or works that will have an impact on areas identified as Greenweb'. An "
                    "impact test, not a type list.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "biodiversity",
        },
        "part_19_heritage": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'Part 19 applies to any development associated "
                    "with a Heritage Item or within a Heritage Conservation Area (HCA) identified "
                    "on the KLEP Heritage Map' (PDF p2) -- a heritage LISTING, which can carry "
                    "any zone.",
                "applicable_dev_types": "PDF p2 verbatim: 'This Part applies to any development "
                    "that is: i) a Heritage Item listed under Schedule 5 Environmental Heritage "
                    "within KLEP'. 'Any development' is the Part's own words, and it adds 'Where "
                    "there is inconsistency between the controls in Part 19 and controls in other "
                    "parts of this DCP, the controls in Part 19 prevail.'",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": None,
        },
        "part_20_rail_roads": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "section 20.1 scopes it by PROXIMITY: 'All "
                    "development that is in, or immediately adjacent to, the rail corridor or a "
                    "busy road is to be designed in accordance with the SEPP (Transport and "
                    "Infrastructure) 2021' (PDF p2).",
                "applicable_dev_types": "The same sentence begins 'All development that is in, or "
                    "immediately adjacent to, the rail corridor or a busy road' -- 'all "
                    "development' is the council's own phrase.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "acoustic",
        },

        # PART 14 — ALL FIFTEEN CONFIGURED 2026-10-03. The docstring above says
        # the 14A-14O precinct PDFs were "excluded from initial onboarding"; every
        # one of them serves rules (94 served rows), so none of them was excluded
        # in the only sense that matters. Leaving them unconfigured sent them to
        # text extraction, which read the retired codes B2 and B4 out of their own
        # text as NSW zones: the retag dry run on the committed config narrowed
        # SEVEN served rows onto a zone no Ku-ring-gai property has. Configuring
        # them takes that to zero. Each is scoped to a named place.
        "section_b_part_14a_st_ives_local_centre": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to a NAMED CENTRE. Its own heading is "
                    "'14A St Ives Local Centre' and its opening section is '14A.1 St Ives Local Centre Context', whose page is a "
                    "cadastral figure of the centre. A mapped local centre contains several "
                    "zones, so a zone list would hide the Part from the lots inside it carrying "
                    "any other zone -- and the only zone codes the Part 14 series names are B2 "
                    "and B4, both retired by the employment-zone reform and absent from "
                    "lep_zone_coverage for this LGA.",
                "applicable_dev_types": "A local-centre Part binds what is built in the centre and names no "
                    "development type; Section B is titled 'URBAN PRECINCT AND SITES'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14b_turramurra_local_centre": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to a NAMED CENTRE. Its own heading is "
                    "'14B Turramurra Local Centre' and its opening section is '14B.1 Turramurra Local Centre Context', whose page is a "
                    "cadastral figure of the centre. A mapped local centre contains several "
                    "zones, so a zone list would hide the Part from the lots inside it carrying "
                    "any other zone -- and the only zone codes the Part 14 series names are B2 "
                    "and B4, both retired by the employment-zone reform and absent from "
                    "lep_zone_coverage for this LGA.",
                "applicable_dev_types": "A local-centre Part binds what is built in the centre and names no "
                    "development type; Section B is titled 'URBAN PRECINCT AND SITES'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14c_pymble_local_centre": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to a NAMED CENTRE. Its own heading is "
                    "'14C Pymble Local Centre' and its opening section is '14C.1 Pymble Local Centre Context', whose page is a "
                    "cadastral figure of the centre. A mapped local centre contains several "
                    "zones, so a zone list would hide the Part from the lots inside it carrying "
                    "any other zone -- and the only zone codes the Part 14 series names are B2 "
                    "and B4, both retired by the employment-zone reform and absent from "
                    "lep_zone_coverage for this LGA.",
                "applicable_dev_types": "A local-centre Part binds what is built in the centre and names no "
                    "development type; Section B is titled 'URBAN PRECINCT AND SITES'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14d_gordon_local_centre": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to a NAMED CENTRE. Its own heading is "
                    "'14D Gordon Local Centre' and its opening section is '14D.1 Gordon Local Centre Context', whose page is a "
                    "cadastral figure of the centre. A mapped local centre contains several "
                    "zones, so a zone list would hide the Part from the lots inside it carrying "
                    "any other zone -- and the only zone codes the Part 14 series names are B2 "
                    "and B4, both retired by the employment-zone reform and absent from "
                    "lep_zone_coverage for this LGA.",
                "applicable_dev_types": "A local-centre Part binds what is built in the centre and names no "
                    "development type; Section B is titled 'URBAN PRECINCT AND SITES'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14e_lindfield_local_centre": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to a NAMED CENTRE. Its own heading is "
                    "'14E Lindfield Local Centre' and its opening section is '14E.1 Lindfield Local Centre Context', whose page is a "
                    "cadastral figure of the centre. A mapped local centre contains several "
                    "zones, so a zone list would hide the Part from the lots inside it carrying "
                    "any other zone -- and the only zone codes the Part 14 series names are B2 "
                    "and B4, both retired by the employment-zone reform and absent from "
                    "lep_zone_coverage for this LGA.",
                "applicable_dev_types": "A local-centre Part binds what is built in the centre and names no "
                    "development type; Section B is titled 'URBAN PRECINCT AND SITES'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14f_roseville_local_centre": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to a NAMED CENTRE. Its own heading is "
                    "'14F Roseville Local Centre' and its opening section is '14F.1 Roseville Local Centre Context', whose page is a "
                    "cadastral figure of the centre. A mapped local centre contains several "
                    "zones, so a zone list would hide the Part from the lots inside it carrying "
                    "any other zone -- and the only zone codes the Part 14 series names are B2 "
                    "and B4, both retired by the employment-zone reform and absent from "
                    "lep_zone_coverage for this LGA.",
                "applicable_dev_types": "A local-centre Part binds what is built in the centre and names no "
                    "development type; Section B is titled 'URBAN PRECINCT AND SITES'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14g_pymble_business_park": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14G Pymble Business Park' and its opening section is '14G.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14h_screen_australia_site": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14H Screen Australia site' and its opening section is '14H.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14i_killara_golf_club": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14I Killara Golf Club' and its opening section is '14I.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14j_holford_crescent_gordon": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14J Holford Crescent, Gordon' and its opening section is '14J.1 Building Setbacks'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14k_45_47_tennyson_avenue_and_105_eastern_road_turramurra": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14K 45-47 Tennyson Avenue and 105 Eastern Road, Turramurra' and its opening section is '14K.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14l_62_and_64_66_pacific_highway_roseville": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14L 62 and 64-66 Pacific Highway, Roseville' and its opening section is '14L.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14m_47_warrane_road_roseville_chase": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14M 47 Warrane Road, Roseville Chase' and its opening section is '14M.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14n_8a_14_16_buckingham_road_killara": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14N 8A, 14-16 Buckingham Road, Killara' and its opening section is '14N.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },
        "section_b_part_14o_pymble_golf_club": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped to ONE NAMED SITE. Its own heading is "
                    "'14O Pymble Golf Club' and its opening section is '14O.1 Urban Precinct'. A site boundary is not "
                    "a zone, and a zone list would hide the Part from the site it was written "
                    "for if that site's zone ever changed.",
                "applicable_dev_types": "A site-specific Part binds what is built on the named land and enumerates "
                    "no development type.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "precinct", "topic": None,
        },

        # ── Section C: Design & Technical Standards ────────────────────────
        "part_21_site_design": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part applies to all types of development, "
                    "and provides a consistent area wide approach to issues that all developments "
                    "are to address' (PDF p2) -- 'area wide' is the council's own word for the "
                    "whole LGA.",
                "applicable_dev_types": "PDF p2 verbatim: 'This Part applies to all types of "
                    "development, and provides a consistent area wide approach to issues that all "
                    "developments are to address and provides guidance on meeting the aims and "
                    "objectives within the LEP.' ALL is the Part's own words, not a fallthrough.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": None,
        },
        "part_22_parking": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This part applies to all types of development, "
                    "and provides a consistent area wide approach to access and parking issues "
                    "that all developments are to address' (PDF p2).",
                "applicable_dev_types": "The same sentence: 'all types of development'. ALL is "
                    "stated, and the Part distinguishes by scale rather than type -- PDF p3: "
                    "'Applications for development, other than single dwellings, are to "
                    "demonstrate how access to and within developments meets the [standards]'.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "parking",
        },
        "part_23_building_design": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "'This Part applies to all development types "
                    "whether or not it is individually specified in Section A of this DCP' (PDF "
                    "p2).",
                "applicable_dev_types": "PDF p2 verbatim: 'This Part applies to all development "
                    "types whether or not it is individually specified in Section A of this DCP. "
                    "It also supplements the objectives and controls for each development type in "
                    "Section A', and 'Each section within this Part applies to a range of "
                    "development types, and some sections to all development.' ALL is explicit, "
                    "including the types the DCP does not name elsewhere.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": None,
        },
        "part_24_water": {
            "scope_declined": ("applicable_zones",),
            "scope_evidence": {
                "applicable_zones": _NO_ZONE + "the Part is scoped by DRAINAGE PATTERN, not "
                    "zone: 'Part 24A categorises: i) development types, eg new dwellings or "
                    "retail premises, and ii) site location by drainage patterns, eg draining "
                    "towards the road, or draining towards bushland' (INTRODUCTION, PDF p2). Its "
                    "own locations A-D are drainage categories.",
                "applicable_dev_types": "PDF p2 verbatim: 'This Part facilitates development in "
                    "achieving the requirements of KLEP Clause 5.21 - Floodwater Planning [and] "
                    "Clause 6.5 - Stormwater and Water Sensitive Urban Design.' It categorises "
                    "development types itself rather than excluding any, naming 'new dwellings or "
                    "retail premises' only as examples, so every type is reached.",
            },
"applicable_dev_types": ["ALL"],
            "layer": "generic", "topic": "stormwater",
        },
        "part_25_waste":                {"layer": "generic",      "topic": None},
    },
}
