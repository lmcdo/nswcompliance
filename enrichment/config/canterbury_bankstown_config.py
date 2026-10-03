"""Canterbury-Bankstown DCP 2023 — applicability config.

WHY THIS EXISTS
---------------
883 served Canterbury-Bankstown provisions across 44 documents carried
`v2_dev_type_source='no_config'`: they applied to EVERY development type because
nothing matched, not because anything decided so. 713 of those arrived on
2026-09-22 when two re-read chapters were published, which pushed DQ-33 above its
floor and flipped OC-17 from passing to CONTRADICTED. The rows were not wrong
before that — there were simply fewer of them.

THE THREE STATES USED HERE, AND WHY NOT ONE
-------------------------------------------
`ApplicabilityTagger._resolve` distinguishes four outcomes, and the difference is
the whole point of this file:

  config_specific — the config named actual development types.
  config_all      — the config EXPLICITLY said ALL. "A real assertion of
                    universality; trust it."
  config_silent   — an entry matched but omitted the key. Nobody decided.
  no_config       — nothing matched at all. The weakest state.

Declaring `['ALL']` everywhere would have cleared the count in one line and been
a lie: `config_all` asserts universality, so asserting it for
`chapter_10_7_sex_services_premises` would be worse than the `no_config` it
replaced. A number made green by a false assertion is the defect DQ-33 exists to
catch, not a fix for it.

So:
  * Place- and topic-scoped chapters say ALL, because they genuinely bind any
    development in their area or on their topic. Their scoping is GEOGRAPHIC or
    by SUBJECT, not by development type.
  * Land-use chapters (10.x) are narrowed where the tagger's vocabulary has a
    matching type.
  * Where it does NOT — schools, places of public worship, home businesses have
    no term in DEV_TYPE_PATTERNS — the key is OMITTED on purpose. That yields
    `config_silent`: "this chapter matched, and nobody has decided its
    development types." That is exactly true, and it is not the same claim as
    ALL. Adding those three terms to the vocabulary is the real fix; inventing a
    scope here would hide a binding control from the properties it binds, which
    is the asymmetric failure this config is most careful to avoid.

Verified against the chapters' own provisions on 2026-09-22, not their titles —
7.5 and 7.6 carry dwelling mix, non-residential building separation, flood
controls, tree canopy and named key-site design principles side by side, which is
what a precinct chapter looks like and why ALL is the honest answer for them.

WHAT A NARROWING ACTUALLY COSTS — measured 2026-09-23, read this before editing
------------------------------------------------------------------------------
Both keys are HARD FILTERS on the served answer, not ranking hints:

  v2_applicable_zones      frontend-nextjs/app/api/provisions/for-property/route.ts:1012
  v2_applicable_dev_types  frontend-nextjs/app/api/provisions/for-property/route.ts:1222
                           frontend-nextjs/app/api/permissibility/check/route.ts:207

A row survives only if the column is NULL, contains 'ALL', or overlaps the
query. So naming a type here does not make that type's answer better — it
DELETES the row from every other type's answer. `relevance_level` elsewhere in
the same file ranks rather than filters, which is what makes this easy to
misread.

And the query side is WIDER than DEV_TYPE_PATTERNS in the tagger: the serving
taxonomy (frontend-nextjs/lib/see/devTypeHierarchy.ts) also carries
neighbourhood_shop, serviced_apartment, educational_establishment, subdivision,
pool, fence, carport, deck, demolition and trees. A list written against the
tagger's 16 terms therefore looks complete and still hides the chapter from
real, selectable development types. Chapters 9.1 and 10.4 were both wrong this
way on 2026-09-22 and are corrected below.
"""

#: Chapters whose scope is a PLACE or a SUBJECT, so every development within them
#: is bound. Keys are matched as substrings of document_id.lower().
_ALL = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"]}

CANTERBURY_BANKSTOWN_CONFIG: dict = {
    "chapter_topics": {
        # --- 2.x site-wide matters: bind any development on an affected site ---
        "chapter_2_1_site_analysis": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },
        # ⚠ SECTIONS 1-8 BIND THE FORMER BANKSTOWN LGA ONLY, and nothing in this
        # config can express that. Canterbury-Bankstown is a merged council; the
        # chapter's own scope section limits sections 1-8 to the Bankstown half.
        # ALL is therefore wider than the council wrote for those sections, and
        # is recorded as a known over-reach rather than approximated away: the
        # geography is a former-LGA boundary, not a zone or a development type,
        # so neither declared key can carry it.
        "chapter_2_2_flood_risk_management": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 2.2 page 4, 'Land to which sections 1-8 apply', verbatim: 'Sections 1-8 of Chapter 2.2 apply to flood liable land in the former Bankstown Local Government Area: (a) Catchments affected by floodplain risk management plans and flood studies...' TWO narrowings the zone list cannot carry, recorded here rather than lost: the land must be FLOOD LIABLE, which site_conditions ['flood'] expresses, and sections 1-8 are limited to the FORMER BANKSTOWN LGA, which nothing in this config expresses. ALL is a known over-reach for those sections, not a decision that they bind the whole merged council.",
                "applicable_dev_types":
                    "Chapter 2.2 states no development-type scope of its own; its controls are addressed to development on flood liable land generally, so ALL. The flood condition and the former-LGA boundary, not the development type, are what limit this chapter.",
            },
            **_ALL, "layer": "generic",
            "site_conditions": ["flood"]},
        "chapter_2_3_tree_management": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 2.3 page 5, verbatim: 'Chapter 2.3 of this DCP applies to: (a) all trees regardless of size, species or origin, located on: (i) public land; or (ii) public places; or (iii) public reserves; or (iv) public roads; and (b) trees on all other land that satisfy one or more of the following criteria...' The scope is TREES, not zones, and it reaches all other land, so ALL.",
                "applicable_dev_types":
                    "Chapter 2.3 page 5, same sentence: the scope is an attribute of a TREE, not of a development type. The serving taxonomy's 'trees' term does not appear in this config's vocabulary, and tree works accompany development of any type, so narrowing would hide the tree controls from the applications that trigger them.",
            },
           **_ALL, "layer": "generic"
        },
        "chapter_2_4_pipeline_corridors": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },

        # --- 3.x general development standards ---
        "chapter_3_1_development_engineering_standards": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },
        "chapter_3_2_parking": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },
        "chapter_3_4_sustainable_development": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 3.4 page 4, 'Application of this chapter', verbatim: 'Chapter 3.4 of this DCP (this chapter) applies to buildings with a classification of Class 5 to Class 9 under the Building Code of Australia in the following situations: new proposals requiring an application; extensions to existing development that is greater than or equal to 5,000m2 of gross floor area...' The scope is a BCA BUILDING CLASS, not a zone, so no zone list is declared.",
                "applicable_dev_types":
                    "Chapter 3.4 page 4, same sentence. BCA Class 5-9 is the whole non-residential range (office, shop, car park, warehouse, health, assembly) and has no equivalent in the serving taxonomy. ALL is recorded with that gap stated rather than approximated by a list, which would silently drop whichever classes the list missed.",
            },
           **_ALL, "layer": "generic"
        },
        "chapter_3_5_subdivision": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },
        "chapter_3_6_signs": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },
        "chapter_3_7_landscape": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "generic"
        },

        # --- 4.x heritage: binds any development on/near a heritage item or HCA ---
        "chapter_4_1_introduction": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "heritage"
        },
        "chapter_4_2_heritage_items": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 4.2 page 4, verbatim: 'Chapter 4.2 of this DCP applies to heritage items listed in the Canterbury-Bankstown Local Environmental Plan 2023 (Schedule 5, Part 1). The controls also apply to draft heritage items, IHO affected properties and section 170 Register affected properties.' The scope is a HERITAGE LISTING, not a zone -- a listed item can sit in any zone, so a zone list would hide the chapter from items outside it.",
                "applicable_dev_types":
                    "Chapter 4.2 page 4, same sentence: the trigger is the heritage status of the property, not the type of development proposed, so ALL.",
            },
           **_ALL, "layer": "heritage"
        },
        "chapter_4_3_heritage_conservation_areas": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "layer": "heritage"
        },
        "chapter_4_4_vicinity_of_places_of_heritage_significance": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' The chapter states no development-type scope of its own, so it inherits the plan's. ALL is the plan's statement, not a decision about this chapter.",
            },
            **_ALL, "layer": "heritage"},

        # --- 6.x / 7.x / 8.x centres and corridors: PRECINCT scoped ---
        "chapter_6_1_general_requirements": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_6_2_bankstown_city_centre": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_6_3_campsie_town_centre": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_7_1_general_requirements": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_7_2_city_west": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_7_3_city_east": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_7_4_neighbourhood_centres": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_7_5_canterbury_local_centre": {**_ALL, "is_precinct_specific": True},
        "chapter_7_6_belmore_and_lakemba": {**_ALL, "is_precinct_specific": True},
        "chapter_8_1_general_requirements": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_8_2_canterbury_road": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_8_3_hume_highway": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },

        # --- 9.x industrial precincts: scoped by ZONE, not by development type ---
        # Chapter 9.1 section 1 Introduction, verbatim: the DCP "supports the LEP
        # by providing additional objectives and development controls to enhance
        # the function, design and amenity of the industrial precincts within
        # Zone E4 General Industrial". E4 is the only zone the chapter names as
        # its own scope (checked against the whole PDF, not the introduction
        # alone: the sole other zone reference is a control about adjoining land).
        #
        # applicable_dev_types is OMITTED on purpose -> config_silent. The same
        # page says "Non-industrial development will be limited to land uses that
        # are compatible with the primary employment role of the precinct", and
        # the chapter's own controls bear that out: 3.16 governs vehicle body
        # repair workshops and 5.10 food premises. The first draft of this entry
        # declared ["industrial_development", "light_industry", "warehouse"],
        # which would have hidden 5.10 from a food_and_drink_premises DA inside
        # E4 -- v2_applicable_dev_types is a HARD filter in
        # frontend-nextjs/app/api/provisions/for-property/route.ts, not a ranking
        # hint, so that narrowing removes the row from the answer entirely.
        "chapter_9_1_general_requirements": {
            "scope_evidence": {
                "applicable_zones":
                    "--- 9.x industrial precincts: scoped by ZONE, not by development type --- Chapter 9.1 section 1 Introduction, verbatim: the DCP 'supports the LEP by providing additional objectives and development controls to enhance the function, design and amenity of the industrial precincts within Zone E4 General Industrial'. E4 is the only zone the chapter names as its own scope (checked against the whole PDF, not the introduction alone: the sole other zone reference is a control about adjoining land). applicable_dev_types is OMITTED on purpose -> config_silent. The same page says 'Non-industrial development will be limited to land uses that are compatible with the primary employment role of the precinct', and the chapter's own controls bear that out: 3.16 governs vehicle body repair workshops and 5.10 food premises. The first draft of this entry declared ['industrial_development', 'light_industry', 'warehouse'], which would have hidden 5.10 from a food_and_drink_premises DA inside E4 -- v2_applicable_dev_types is a HARD filter in frontend-nextjs/app/api/provisions/for-property/route.ts, not a ranking hint, so that narrowing removes the row from the answer entirely.",
            },
            "applicable_zones": ["E4"],  # noqa: zone-codes (the zone chapter 9.1 section 1 names as its own scope)
        },

        # --- 10.x SPECIFIC LAND USES: narrowed where the vocabulary allows ---
        "chapter_10_1_child_care_centres": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["child_care_centre"],
        },
        # Chapter 10.4 section 1 Introduction, verbatim: controls "to manage the
        # design and operation of non-residential land uses within Zone R2 Low
        # Density Residential, Zone R3 Medium Density Residential and Zone R4
        # High Density Residential". Its sections are Health consulting rooms (2),
        # Neighbourhood shops (3), Serviced apartments (4), Other non-residential
        # development (5) and Site facilities (6).
        #
        # applicable_dev_types is OMITTED -> config_silent. The first draft named
        # commercial/retail/office/food-and-drink/industrial/warehouse, which was
        # wrong in both directions: industrial and warehouse development does not
        # occur in R2/R3/R4, and three of the chapter's own five subject sections
        # were missing. `neighbourhood_shop` and `serviced_apartment` both exist
        # in the serving taxonomy (frontend-nextjs/lib/see/devTypeHierarchy.ts),
        # so that list did not merely lose precision -- it hid the chapter from
        # exactly the two development types sections 3 and 4 are written for.
        "chapter_10_4_non_residential_land_uses": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 10.4 section 1 Introduction, verbatim: controls 'to manage the design and operation of non-residential land uses within Zone R2 Low Density Residential, Zone R3 Medium Density Residential and Zone R4 High Density Residential'. Its sections are Health consulting rooms (2), Neighbourhood shops (3), Serviced apartments (4), Other non-residential development (5) and Site facilities (6). applicable_dev_types is OMITTED -> config_silent. The first draft named commercial/retail/office/food-and-drink/industrial/warehouse, which was wrong in both directions: industrial and warehouse development does not occur in R2/R3/R4, and three of the chapter's own five subject sections were missing. `neighbourhood_shop` and `serviced_apartment` both exist in the serving taxonomy (frontend-nextjs/lib/see/devTypeHierarchy.ts), so that list did not merely lose precision -- it hid the chapter from exactly the two development types sections 3 and 4 are written for.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table. The zone names are the council's own words; rewriting them to import from the taxonomy would falsify the quote.
            },
            "applicable_zones": ["R2", "R3", "R4"],  # noqa: zone-codes (the three zones chapter 10.4 section 1 names as its own scope)
        },
        "chapter_10_7_sex_services_premises": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["sex_services_premises"],
        },
        # applicable_dev_types deliberately ABSENT below -> config_silent, not ALL.
        # DEV_TYPE_PATTERNS has no term for a school, a place of public worship or a
        # home business, so there is nothing honest to narrow to. Saying ALL here
        # would assert that a school control binds a warehouse.
        "chapter_10_2_schools": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           "applicable_zones": ["ALL"]
        },
        "chapter_10_3_home_businesses": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           "applicable_zones": ["ALL"]
        },
        "chapter_10_5_places_of_public_worship": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           "applicable_zones": ["ALL"]
        },

        # --- 11.x site-specific precincts: one named site each, any development ---
        "chapter_11_1_milton_street": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_3_roberts_road": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 11.3 of this DCP, verbatim: 'Chapter 11.3 of this DCP applies to 52-60 Roberts Road, Greenacre as shown in Figure 1.' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
                "applicable_dev_types":
                    "Chapter 11.3 of this DCP, verbatim: 'Chapter 11.3 of this DCP applies to 52-60 Roberts Road, Greenacre as shown in Figure 1.' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_4_croydon_street_precinct": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 11.4 of this DCP, verbatim: 'Chapter 11.4 of this DCP applies to the site as shown in the Land Application Map (Figure 1a).' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
                "applicable_dev_types":
                    "Chapter 11.4 of this DCP, verbatim: 'Chapter 11.4 of this DCP applies to the site as shown in the Land Application Map (Figure 1a).' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_5_riverlands": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 11.5 of this DCP, verbatim: 'Chapter 11.5 of this DCP applies to the site as shown in the Land Application Map (Figure 1a).' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
                "applicable_dev_types":
                    "Chapter 11.5 of this DCP, verbatim: 'Chapter 11.5 of this DCP applies to the site as shown in the Land Application Map (Figure 1a).' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_8_boorea": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_9_revesby_hospital": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 11.9 page 4, verbatim: 'Chapter 11.9 of this DCP applies to 297-299 Canterbury Road in Revesby legally described as Lot 9, DP 663160 and Lot 202, DP 840245.' Two named lots; is_precinct_specific carries the geography, so no zone list.",
                "applicable_dev_types":
                    "Chapter 11.9 page 4, verbatim: 'This chapter applies to development for the purposes of a hospital. For other development types, the other parts of the DCP apply.' ALL IS WIDER THAN THE COUNCIL WROTE, and is left in place deliberately: 'hospital' does not exist in frontend-nextjs/lib/see/devTypeHierarchy.ts, so declaring it would match nothing and hide this chapter from every application, including a hospital one. Recorded as a known over-reach with the council's own narrowing quoted, so it can be fixed when the taxonomy gains the term, rather than resolved silently now in the direction that loses the chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_10_chullora_marketplace": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 11.10 of this DCP, verbatim: 'Chapter 11.10 of this DCP applies to the Chullora Marketplace site at 353-355 Waterloo Road, Greenacre as shown in Figure 1.' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
                "applicable_dev_types":
                    "Chapter 11.10 of this DCP, verbatim: 'Chapter 11.10 of this DCP applies to the Chullora Marketplace site at 353-355 Waterloo Road, Greenacre as shown in Figure 1.' The scope is a SITE, which no zone list or development-type list expresses; is_precinct_specific carries it. ALL on both keys is correct here rather than permissive -- narrowing either would hide the chapter from development on the very site it governs.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_11_brighton_avenue": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_12_445_canterbury_road": {
            "scope_evidence": {
                "applicable_zones":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
                "applicable_dev_types":
                    "Chapter 1.1 Introduction and Administration, page 5, verbatim: 'This DCP applies to land within the Canterbury-Bankstown Local Government Area.' THIS CHAPTER STATES NO SCOPE OF ITS OWN -- read 2026-10-03, its first 12 pages carry no 'Chapter N.N of this DCP applies to', no 'Application of this chapter' and no 'Land to which ... applies' section -- so it inherits the plan's scope, which is the whole LGA. Recorded as INHERITED rather than declared: ALL here is the plan's statement, not a decision anybody made about this chapter.",
            },
           **_ALL, "is_precinct_specific": True
        },
        "chapter_11_13_former_wsu_campus_milperra": {**_ALL, "is_precinct_specific": True},
        "chapter_11_14_riverwood_estate": {**_ALL, "is_precinct_specific": True},
        "chapter_11_15_marco_avenue": {**_ALL, "is_precinct_specific": True},
    },
}
