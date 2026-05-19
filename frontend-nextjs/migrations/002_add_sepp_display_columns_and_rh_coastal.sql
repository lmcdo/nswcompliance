-- Migration 002: Add SEPP display columns + R&H 2021 Chapter 2 coastal assessment triggers
--
-- Context: The API route /api/sepp/structured-requirements queries columns (sepp_id,
-- sepp_name, schedule, schedule_name, section, section_name, development_type_category,
-- requirement_data, source_provision_id) that do not exist in the table. This migration
-- adds them. The existing 553 relational rows (used by pattern-book eligibility) are
-- unaffected — they get NULL for all new columns and are excluded from API queries
-- by the WHERE sepp_id = $1 filter.
--
-- Then inserts 7 rows for SEPP (Resilience and Hazards) 2021 Chapter 2 coastal
-- assessment triggers, linking spatial overlay data to specific statutory requirements.
--
-- Date: 2026-05-18
-- Author: lawrence mcdonell

BEGIN;

-- ============================================================
-- Part A: Add display columns (idempotent)
-- ============================================================

ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS sepp_id TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS sepp_name TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS schedule TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS schedule_name TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS section TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS section_name TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS development_type_category TEXT;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS requirement_data JSONB;
ALTER TABLE sepp_structured_requirements ADD COLUMN IF NOT EXISTS source_provision_id INTEGER REFERENCES regulatory_provisions(id);

-- Relax NOT NULL on columns that only apply to relational (Schema A) rows.
-- JSONB display rows don't use these columns. Idempotent — dropping NOT NULL
-- from an already-nullable column is a no-op.
ALTER TABLE sepp_structured_requirements ALTER COLUMN requirement_category DROP NOT NULL;
ALTER TABLE sepp_structured_requirements ALTER COLUMN applies_to DROP NOT NULL;
ALTER TABLE sepp_structured_requirements ALTER COLUMN source_clause DROP NOT NULL;
ALTER TABLE sepp_structured_requirements ALTER COLUMN extraction_confidence DROP NOT NULL;

-- Indexes for the API query pattern
CREATE INDEX IF NOT EXISTS idx_ssr_sepp_id ON sepp_structured_requirements(sepp_id);
CREATE INDEX IF NOT EXISTS idx_ssr_dev_type_cat ON sepp_structured_requirements(development_type_category);
CREATE INDEX IF NOT EXISTS idx_ssr_source_provision ON sepp_structured_requirements(source_provision_id);

-- ============================================================
-- Part B: Insert R&H 2021 Chapter 2 coastal assessment triggers
-- ============================================================
-- Design principle: verbatim statutory text only, no interpretation.
-- overlay_triggers links spatial_overlays.layer_type to the clause.
-- development_type_category = 'all' because R&H applies regardless
-- of development type (confirmed by API route line 129 special-case).

-- s2.7 — Coastal wetlands and littoral rainforests area
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.7',
    'Coastal wetlands and littoral rainforests area',
    'all',
    '{
        "title": "Coastal Wetlands and Littoral Rainforests Area",
        "description": "Development on land identified as coastal wetlands or littoral rainforest on the Coastal Wetlands and Littoral Rainforests Area Map.",
        "overlay_triggers": ["coastal_wetlands", "littoral_rainforest"],
        "categories": [
            {
                "name": "Development Consent Required",
                "reference": "s 2.7(1)",
                "requirements": [
                    {"consent_gate": "The following may be carried out on land identified as coastal wetlands or littoral rainforest on the Coastal Wetlands and Littoral Rainforests Area Map only with development consent: clearing of native vegetation, harm of marine vegetation, earthworks, draining of land, environmental protection works."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.7(1)"
            },
            {
                "name": "Designated Development Declaration",
                "reference": "s 2.7(2)",
                "requirements": [
                    {"designation": "Development for which consent is required by subsection (1), other than development for the purpose of environmental protection works, is declared to be designated development for the purposes of the Act."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.7(2)"
            },
            {
                "name": "Consent Gate — Ecological Integrity",
                "reference": "s 2.7(4)",
                "requirements": [
                    {"satisfaction_test": "A consent authority must not grant consent for development referred to in subsection (1) unless the consent authority is satisfied that sufficient measures have been, or will be, taken to protect, and where possible enhance, the biophysical, hydrological and ecological integrity of the coastal wetland or littoral rainforest."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.7(4)"
            }
        ],
        "pdf_references": [
            {"section": "2.7", "description": "Coastal wetlands and littoral rainforests area"}
        ]
    }'::jsonb,
    12645
);

-- s2.8 — Proximity to coastal wetlands or littoral rainforest
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.8',
    'Proximity to coastal wetlands or littoral rainforest',
    'all',
    '{
        "title": "Land in Proximity to Coastal Wetlands or Littoral Rainforest",
        "description": "Development on land identified as proximity area for coastal wetlands or littoral rainforest.",
        "overlay_triggers": ["coastal_wetlands", "littoral_rainforest"],
        "categories": [
            {
                "name": "No Significant Impact Test",
                "reference": "s 2.8(1)",
                "requirements": [
                    {"satisfaction_test": "Development consent must not be granted to development on land identified as proximity area for coastal wetlands or proximity area for littoral rainforest on the Coastal Wetlands and Littoral Rainforests Area Map unless the consent authority is satisfied that the proposed development will not significantly impact on:"},
                    {"criterion_a": "(a) the biophysical, hydrological or ecological integrity of the adjacent coastal wetland or littoral rainforest"},
                    {"criterion_b": "(b) the quantity and quality of surface and ground water flows to and from the adjacent coastal wetland or littoral rainforest"}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.8(1)"
            }
        ],
        "pdf_references": [
            {"section": "2.8", "description": "Proximity to coastal wetlands or littoral rainforest"}
        ]
    }'::jsonb,
    12651
);

-- s2.9 — Coastal vulnerability area
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.9',
    'Coastal vulnerability area',
    'all',
    '{
        "title": "Development on Land within the Coastal Vulnerability Area",
        "description": "Engineering and resilience requirements for development in areas identified as coastal vulnerability area.",
        "overlay_triggers": ["coastal_land_application"],
        "categories": [
            {
                "name": "Engineering Resilience",
                "reference": "s 2.9(a)",
                "requirements": [
                    {"satisfaction_test": "If the proposed development comprises the erection of a building or works — the building or works are engineered to withstand current and projected coastal hazards for the design life of the building or works."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.9(a)"
            },
            {
                "name": "Environmental and Access Protection",
                "reference": "s 2.9(b)",
                "requirements": [
                    {"criterion_i": "(i) is not likely to alter coastal processes to the detriment of the natural environment or other land"},
                    {"criterion_ii": "(ii) is not likely to reduce the public amenity, access to and use of any beach, foreshore, rock platform or headland adjacent to the proposed development"},
                    {"criterion_iii": "(iii) incorporates appropriate measures to manage risk to life and public safety from coastal hazards"}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.9(b)"
            },
            {
                "name": "Coastal Hazard Management",
                "reference": "s 2.9(c)",
                "requirements": [
                    {"satisfaction_test": "Measures are in place to ensure that there are appropriate responses to, and management of, anticipated coastal processes and current and future coastal hazards."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.9(c)"
            }
        ],
        "pdf_references": [
            {"section": "2.9", "description": "Coastal vulnerability area"}
        ]
    }'::jsonb,
    12653
);

-- s2.10 — Coastal environment area
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.10',
    'Coastal environment area',
    'all',
    '{
        "title": "Development on Land within the Coastal Environment Area",
        "description": "Seven-criteria consideration requirement with avoid/minimise/mitigate hierarchy for development in the coastal environment area.",
        "overlay_triggers": ["coastal_environment_area"],
        "categories": [
            {
                "name": "Adverse Impact Consideration (7 criteria)",
                "reference": "s 2.10(1)",
                "requirements": [
                    {"criterion_a": "(a) the integrity and resilience of the biophysical, hydrological (surface and groundwater) and ecological environment"},
                    {"criterion_b": "(b) coastal environmental values and natural coastal processes"},
                    {"criterion_c": "(c) the water quality of the marine estate (within the meaning of the Marine Estate Management Act 2014), in particular, the cumulative impacts of the proposed development on any of the sensitive coastal lakes identified in Schedule 1"},
                    {"criterion_d": "(d) marine vegetation, native vegetation and fauna and their habitats, undeveloped headlands and rock platforms"},
                    {"criterion_e": "(e) existing public open space and safe access to and along the foreshore, beach, headland or rock platform for members of the public, including persons with a disability"},
                    {"criterion_f": "(f) Aboriginal cultural heritage, practices and places"},
                    {"criterion_g": "(g) the use of the surf zone"}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.10(1)"
            },
            {
                "name": "Avoid / Minimise / Mitigate Hierarchy",
                "reference": "s 2.10(2)",
                "requirements": [
                    {"hierarchy_a": "(a) the development is designed, sited and will be managed to avoid an adverse impact referred to in subsection (1), or"},
                    {"hierarchy_b": "(b) if that impact cannot be reasonably avoided — the development is designed, sited and will be managed to minimise that impact, or"},
                    {"hierarchy_c": "(c) if that impact cannot be minimised — the development will be managed to mitigate that impact"}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.10(2)"
            }
        ],
        "pdf_references": [
            {"page": 6, "section": "2.10", "description": "Coastal environment area"}
        ]
    }'::jsonb,
    22381
);

-- s2.11 — Coastal use area
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.11',
    'Coastal use area',
    'all',
    '{
        "title": "Development on Land within the Coastal Use Area",
        "description": "Five-criteria consideration requirement with avoid/minimise/mitigate hierarchy for development in the coastal use area.",
        "overlay_triggers": ["coastal_use_area"],
        "categories": [
            {
                "name": "Adverse Impact Consideration (5 criteria)",
                "reference": "s 2.11(1)(a)",
                "requirements": [
                    {"criterion_i": "(i) existing, safe access to and along the foreshore, beach, headland or rock platform for members of the public, including persons with a disability"},
                    {"criterion_ii": "(ii) overshadowing, wind funnelling and the loss of views from public places to foreshores"},
                    {"criterion_iii": "(iii) the visual amenity and scenic qualities of the coast, including coastal headlands"},
                    {"criterion_iv": "(iv) Aboriginal cultural heritage, practices and places"},
                    {"criterion_v": "(v) cultural and built environment heritage"}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.11(1)(a)"
            },
            {
                "name": "Avoid / Minimise / Mitigate Hierarchy",
                "reference": "s 2.11(1)(b)",
                "requirements": [
                    {"hierarchy_i": "(i) the development is designed, sited and will be managed to avoid an adverse impact referred to in paragraph (a), or"},
                    {"hierarchy_ii": "(ii) if that impact cannot be reasonably avoided — the development is designed, sited and will be managed to minimise that impact, or"},
                    {"hierarchy_iii": "(iii) if that impact cannot be minimised — the development will be managed to mitigate that impact"}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.11(1)(b)"
            },
            {
                "name": "Surrounding Context",
                "reference": "s 2.11(1)(c)",
                "requirements": [
                    {"consideration": "The consent authority has taken into account the surrounding coastal and built environment, and the bulk, scale and size of the proposed development."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.11(1)(c)"
            }
        ],
        "pdf_references": [
            {"section": "2.11", "description": "Coastal use area"}
        ]
    }'::jsonb,
    12655
);

-- s2.12 — Development not to increase risk of coastal hazards
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.12',
    'Development not to increase risk of coastal hazards',
    'all',
    '{
        "title": "Development in Coastal Zone — Not to Increase Risk of Coastal Hazards",
        "description": "Blanket requirement applying to all development in the coastal zone: must not increase risk of coastal hazards.",
        "overlay_triggers": ["coastal_wetlands", "littoral_rainforest", "coastal_land_application", "coastal_environment_area", "coastal_use_area"],
        "categories": [
            {
                "name": "Coastal Hazard Risk Gate",
                "reference": "s 2.12",
                "requirements": [
                    {"satisfaction_test": "Development consent must not be granted to development on land within the coastal zone unless the consent authority is satisfied that the proposed development is not likely to cause increased risk of coastal hazards on that land or other land."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.12"
            }
        ],
        "pdf_references": [
            {"section": "2.12", "description": "Development not to increase risk of coastal hazards"}
        ]
    }'::jsonb,
    12656
);

-- s2.13 — Coastal management programs to be considered
INSERT INTO sepp_structured_requirements (
    sepp_id, sepp_name, schedule, schedule_name, section, section_name,
    development_type_category, requirement_data, source_provision_id
) VALUES (
    'resilience_hazards_2021',
    'SEPP (Resilience and Hazards) 2021',
    'chapter_2',
    'Coastal Management',
    '2.13',
    'Coastal management programs',
    'all',
    '{
        "title": "Development in Coastal Zone — Coastal Management Programs",
        "description": "Requirement to consider any certified coastal management program that applies to the land.",
        "overlay_triggers": ["coastal_wetlands", "littoral_rainforest", "coastal_land_application", "coastal_environment_area", "coastal_use_area"],
        "categories": [
            {
                "name": "Coastal Management Program Consideration",
                "reference": "s 2.13",
                "requirements": [
                    {"consideration": "Development consent must not be granted to development on land within the coastal zone unless the consent authority has taken into consideration the relevant provisions of any certified coastal management program that applies to the land."}
                ],
                "legal_citation": "SEPP (Resilience and Hazards) 2021, s 2.13"
            }
        ],
        "pdf_references": [
            {"section": "2.13", "description": "Coastal management programs"}
        ]
    }'::jsonb,
    12657
);

COMMIT;
