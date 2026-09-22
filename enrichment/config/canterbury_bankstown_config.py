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
"""

#: Chapters whose scope is a PLACE or a SUBJECT, so every development within them
#: is bound. Keys are matched as substrings of document_id.lower().
_ALL = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"]}

CANTERBURY_BANKSTOWN_CONFIG: dict = {
    "chapter_topics": {
        # --- 2.x site-wide matters: bind any development on an affected site ---
        "chapter_2_1_site_analysis": {**_ALL, "layer": "generic"},
        "chapter_2_2_flood_risk_management": {**_ALL, "layer": "generic",
                                              "site_conditions": ["flood"]},
        "chapter_2_3_tree_management": {**_ALL, "layer": "generic"},
        "chapter_2_4_pipeline_corridors": {**_ALL, "layer": "generic"},

        # --- 3.x general development standards ---
        "chapter_3_1_development_engineering_standards": {**_ALL, "layer": "generic"},
        "chapter_3_2_parking": {**_ALL, "layer": "generic"},
        "chapter_3_4_sustainable_development": {**_ALL, "layer": "generic"},
        "chapter_3_5_subdivision": {**_ALL, "layer": "generic"},
        "chapter_3_6_signs": {**_ALL, "layer": "generic"},
        "chapter_3_7_landscape": {**_ALL, "layer": "generic"},

        # --- 4.x heritage: binds any development on/near a heritage item or HCA ---
        "chapter_4_1_introduction": {**_ALL, "layer": "heritage"},
        "chapter_4_2_heritage_items": {**_ALL, "layer": "heritage"},
        "chapter_4_3_heritage_conservation_areas": {**_ALL, "layer": "heritage"},
        "chapter_4_4_vicinity_of_places_of_heritage_significance": {**_ALL,
                                                                    "layer": "heritage"},

        # --- 6.x / 7.x / 8.x centres and corridors: PRECINCT scoped ---
        "chapter_6_1_general_requirements": {**_ALL, "is_precinct_specific": True},
        "chapter_6_2_bankstown_city_centre": {**_ALL, "is_precinct_specific": True},
        "chapter_6_3_campsie_town_centre": {**_ALL, "is_precinct_specific": True},
        "chapter_7_1_general_requirements": {**_ALL, "is_precinct_specific": True},
        "chapter_7_2_city_west": {**_ALL, "is_precinct_specific": True},
        "chapter_7_3_city_east": {**_ALL, "is_precinct_specific": True},
        "chapter_7_4_neighbourhood_centres": {**_ALL, "is_precinct_specific": True},
        "chapter_7_5_canterbury_local_centre": {**_ALL, "is_precinct_specific": True},
        "chapter_7_6_belmore_and_lakemba": {**_ALL, "is_precinct_specific": True},
        "chapter_8_1_general_requirements": {**_ALL, "is_precinct_specific": True},
        "chapter_8_2_canterbury_road": {**_ALL, "is_precinct_specific": True},
        "chapter_8_3_hume_highway": {**_ALL, "is_precinct_specific": True},

        # --- 9.x industrial ---
        "chapter_9_1_general_requirements": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["industrial_development", "light_industry",
                                     "warehouse"],
        },

        # --- 10.x SPECIFIC LAND USES: narrowed where the vocabulary allows ---
        "chapter_10_1_child_care_centres": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["child_care_centre"],
        },
        "chapter_10_4_non_residential_land_uses": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["commercial_premises", "retail_premises",
                                     "office_premises", "food_and_drink_premises",
                                     "industrial_development", "warehouse"],
        },
        "chapter_10_7_sex_services_premises": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["sex_services_premises"],
        },
        # applicable_dev_types deliberately ABSENT below -> config_silent, not ALL.
        # DEV_TYPE_PATTERNS has no term for a school, a place of public worship or a
        # home business, so there is nothing honest to narrow to. Saying ALL here
        # would assert that a school control binds a warehouse.
        "chapter_10_2_schools": {"applicable_zones": ["ALL"]},
        "chapter_10_3_home_businesses": {"applicable_zones": ["ALL"]},
        "chapter_10_5_places_of_public_worship": {"applicable_zones": ["ALL"]},

        # --- 11.x site-specific precincts: one named site each, any development ---
        "chapter_11_1_milton_street": {**_ALL, "is_precinct_specific": True},
        "chapter_11_3_roberts_road": {**_ALL, "is_precinct_specific": True},
        "chapter_11_4_croydon_street_precinct": {**_ALL, "is_precinct_specific": True},
        "chapter_11_5_riverlands": {**_ALL, "is_precinct_specific": True},
        "chapter_11_8_boorea": {**_ALL, "is_precinct_specific": True},
        "chapter_11_9_revesby_hospital": {**_ALL, "is_precinct_specific": True},
        "chapter_11_10_chullora_marketplace": {**_ALL, "is_precinct_specific": True},
        "chapter_11_11_brighton_avenue": {**_ALL, "is_precinct_specific": True},
        "chapter_11_12_445_canterbury_road": {**_ALL, "is_precinct_specific": True},
        "chapter_11_13_former_wsu_campus_milperra": {**_ALL, "is_precinct_specific": True},
        "chapter_11_14_riverwood_estate": {**_ALL, "is_precinct_specific": True},
        "chapter_11_15_marco_avenue": {**_ALL, "is_precinct_specific": True},
    },
}
