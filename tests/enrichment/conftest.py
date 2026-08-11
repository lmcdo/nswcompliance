"""
Pytest fixtures for enrichment tests.

Provides golden set provisions and test data for QA validation.
"""
import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ============================================================================
# GOLDEN SET: Provisions with known correct classifications
# ============================================================================

@pytest.fixture
def golden_set_actionable():
    """
    Golden set of provisions that MUST be classified as actionable.

    These test false negative prevention - if any of these are marked
    as boilerplate, we have a critical bug.
    """
    return [
        # Definitive control language ("must"/"shall")
        {
            "id": "must_setback_1",
            "text": "Buildings must be setback a minimum of 6 metres from the front boundary.",
            "document_id": "Marrickville_DCP_2011_-_2_5_Setbacks",
            "expected_actionable": True,
            "expected_reason": "definitive_control_language",
            "category": "definitive_control",
        },
        {
            "id": "shall_height_1",
            "text": "The maximum building height shall not exceed 9 metres or 2 storeys.",
            "document_id": "Ashfield_DCP_2016_Chapter_F_Part_1",
            "expected_actionable": True,
            "expected_reason": "definitive_control_language",
            "category": "definitive_control",
        },
        {
            "id": "must_landscaping_1",
            "text": "Development must provide a minimum of 30% of the site area as deep soil landscaping.",
            "document_id": "Leichhardt_DCP_2013_Part_C_Section_1",
            "expected_actionable": True,
            "expected_reason": "definitive_control_language",
            "category": "definitive_control",
        },

        # C-marker controls (Leichhardt)
        {
            "id": "c_marker_parking_1",
            "text": "C14 One car parking space is required per dwelling.",
            "document_id": "Leichhardt_DCP_2013_Part_C_Section_1",
            "expected_actionable": True,
            "expected_reason": "dcp_with_control_language",
            "category": "c_marker",
        },
        {
            "id": "c_marker_setback_1",
            "text": "C8 The front setback must be consistent with the established streetscape.",
            "document_id": "Leichhardt_DCP_2013_Part_C_Section_1",
            "expected_actionable": True,
            "expected_reason": "definitive_control_language",
            "category": "c_marker",
        },

        # O-marker objectives
        {
            "id": "o_marker_1",
            "text": "O1 To ensure development maintains the established character of the streetscape.",
            "document_id": "Marrickville_DCP_2011_-_2_4_Building_Design",
            "expected_actionable": True,
            "expected_reason": "dcp_with_control_language",
            "category": "objective",
        },

        # Numeric controls without must/shall
        {
            "id": "numeric_fsr_1",
            "text": "The floor space ratio for residential flat buildings is 0.75:1.",
            "document_id": "Marrickville_DCP_2011_-_4_2_Multi_Dwelling",
            "expected_actionable": True,
            "expected_reason": "dcp_with_control_language",
            "category": "numeric",
        },
        {
            "id": "numeric_height_1",
            "text": "Maximum height: 8.5m",
            "document_id": "Ashfield_DCP_2016_Chapter_F_Part_1",
            "expected_actionable": True,
            "expected_reason": "dcp_with_control_language",
            "category": "numeric",
        },
        {
            "id": "numeric_parking_1",
            "text": "Parking requirement: 1 space per 40m2 of gross floor area.",
            "document_id": "Marrickville_DCP_2011_-_2_10_Parking",
            "expected_actionable": True,
            "expected_reason": "dcp_with_control_language",
            "category": "numeric",
        },

        # Prohibited/permitted language
        {
            "id": "prohibited_1",
            "text": "Development is prohibited on land identified as environmentally sensitive.",
            "document_id": "Marrickville_DCP_2011_-_2_14_Environmental",
            "expected_actionable": True,
            "expected_reason": "dcp_with_control_language",
            "category": "prohibition",
        },
    ]


@pytest.fixture
def golden_set_boilerplate():
    """
    Golden set of provisions that MUST be classified as boilerplate.

    These test false positive prevention - these should NOT appear
    in the compliance results.
    """
    return [
        # Legislative headers
        {
            "id": "boilerplate_header_1",
            "text": "This version of the legislation is compiled and maintained by the Parliamentary Counsel's Office",
            "document_id": "SEPP_Housing_2021",
            "expected_actionable": False,
            "expected_reason": "boilerplate_pattern",
            "category": "legislative_header",
        },
        {
            "id": "boilerplate_update_1",
            "text": "Legislation on this site is usually updated within 3 working days",
            "document_id": "SEPP_Housing_2021",
            "expected_actionable": False,
            "expected_reason": "boilerplate_pattern",
            "category": "legislative_header",
        },

        # TOC entries
        {
            "id": "boilerplate_toc_1",
            "text": "Part 1 Preliminary...................................1",
            "document_id": "Inner_West_LEP_2022",
            "expected_actionable": False,
            "expected_reason": "boilerplate_pattern",
            "category": "toc",
        },
        {
            "id": "boilerplate_page_1",
            "text": "Page 42",
            "document_id": "Marrickville_DCP_2011",
            "expected_actionable": False,
            "expected_reason": "boilerplate_pattern",
            "category": "page_number",
        },

        # PDF artifacts
        {
            "id": "boilerplate_figure_1",
            "text": "Figure 3.1 - Site Context Diagram",
            "document_id": "Marrickville_DCP_2011",
            "expected_actionable": False,
            "expected_reason": "boilerplate_pattern",
            "category": "pdf_artifact",
        },

        # Too short (must be < 10 chars when stripped)
        {
            "id": "boilerplate_short_1",
            "text": "See.",
            "document_id": "Marrickville_DCP_2011",
            "expected_actionable": False,
            "expected_reason": "too_short",
            "category": "too_short",
        },
    ]


@pytest.fixture
def golden_set_layers():
    """
    Golden set of provisions with known correct layer assignments.
    """
    return [
        # Marrickville layers
        {
            "document_id": "Marrickville__DCP__2011__-__2__10__Parking",
            "text": "One car parking space is required per dwelling.",
            "expected_layer": "generic",
            "expected_part": "Part 2",
            "expected_topic": "parking",
            "council": "marrickville",
        },
        {
            "document_id": "Marrickville__DCP__2011__-__4_1__Low__Density__Residential",
            "text": "Setback minimum 6m from front boundary.",
            "expected_layer": "use_specific",
            "expected_part": "Part 4.1",
            "expected_topic": "setbacks",
            "council": "marrickville",
        },
        {
            "document_id": "Marrickville__DCP__2011__-__8.0__Heritage",
            "text": "Heritage items must be conserved.",
            "expected_layer": "condition",
            "expected_part": "Part 8",
            "expected_topic": "heritage",
            "council": "marrickville",
        },
        {
            "document_id": "Marrickville__DCP__2011__-__9__6__Petersham__South__Precinct",
            "text": "Development in this precinct must maintain character.",
            "expected_layer": "precinct",
            "expected_part": "Part 9",
            "expected_topic": None,  # Text-based topic extraction
            "council": "marrickville",
        },

        # Leichhardt layers
        {
            "document_id": "Leichhardt_DCP_2013_Part_C_Section_1_Parking",
            "text": "C14 Parking spaces must be provided at the rear.",
            "expected_layer": "generic",
            "expected_part": "Part C Section 1",
            "expected_topic": "parking",
            "council": "leichhardt",
        },
        {
            "document_id": "Leichhardt_DCP_2013_Part_C_Section_3_Residential",
            "text": "Residential development setbacks.",
            "expected_layer": "use_specific",
            "expected_part": "Part C Section 3",
            "expected_topic": "setbacks",
            "council": "leichhardt",
        },
        {
            "document_id": "Leichhardt_DCP_2013_Part_G_Neighbourhood",
            "text": "Development in this neighbourhood must respect character.",
            "expected_layer": "precinct",
            "expected_part": "Part G",
            "expected_topic": None,
            "council": "leichhardt",
        },

        # Ashfield layers
        {
            "document_id": "Inner_West_Ashfield_DCP_2016_Chapter_F_Part_1",
            "text": "Dwelling houses must have rear setback of 4m.",
            "expected_layer": "use_specific",
            "expected_part": "Chapter F Part 1",
            "expected_topic": "setbacks",
            "council": "ashfield",
        },
        {
            "document_id": "Inner_West_Ashfield_DCP_2016_Chapter_E1_Heritage",
            "text": "Heritage items require conservation.",
            "expected_layer": "condition",
            "expected_part": "Chapter E1",
            "expected_topic": "heritage",
            "council": "ashfield",
        },
        {
            "document_id": "Inner_West_Ashfield_DCP_2016_Chapter_D_Precinct",
            "text": "This precinct has special controls.",
            "expected_layer": "precinct",
            "expected_part": "Chapter D",
            "expected_topic": None,
            "council": "ashfield",
        },
    ]


@pytest.fixture
def golden_set_applicability():
    """
    Golden set of provisions with known correct zone/dev-type applicability.
    """
    return [
        # Marrickville Part 4.1 - Low Density
        {
            "document_id": "Marrickville__DCP__2011__-__4_1__Low__Density__Residential",
            "text": "Setback minimum 6m.",
            "expected_zones": ["R2"],
            "expected_dev_types": ["dwelling_house", "secondary_dwelling", "dual_occupancy"],
            "council": "marrickville",
        },
        # Marrickville Part 4.2 - Multi Dwelling
        {
            "document_id": "Marrickville__DCP__2011__-__4_2__Multi__Dwelling",
            "text": "Multi-dwelling setbacks.",
            "expected_zones": ["R3", "R4"],
            "expected_dev_types": ["multi_dwelling_housing", "residential_flat_building", "attached_dwelling"],
            "council": "marrickville",
        },
        # Marrickville Part 5 - Commercial. DQ-30: zones were ["B1","B2","B4",
        # "MU1"] — B1/B2/B4 are retired NSW zone codes (April 2023 Employment
        # Zones Reform); real current equivalents are E1 (was B1/B2) and MU1
        # (was B4). See .claude/DATA_QUALITY_TRACKER.md.
        {
            "document_id": "Marrickville__DCP__2011__-__5_0__Commercial",
            "text": "Commercial setbacks.",
            "expected_zones": ["E1", "MU1"],  # noqa: zone-codes -- golden-set expected-output fixture, not a shared constant
            "expected_dev_types": ["commercial_premises", "retail_premises", "office_premises", "shop_top_housing", "mixed_use"],
            "council": "marrickville",
        },
        # Marrickville Part 6 - Industrial. DQ-30: zones were ["IN1","IN2"] —
        # both retired; real current equivalent is E4. This was the most
        # severe DQ-30 finding: with no fallback, these provisions matched
        # zero real properties (Inner West has had no IN-zones since 2023).
        {
            "document_id": "Marrickville__DCP__2011__-__6_0__Industrial",
            "text": "Industrial setbacks.",
            "expected_zones": ["E4"],
            "expected_dev_types": ["industrial_development", "warehouse", "light_industry", "heavy_industry"],
            "council": "marrickville",
        },
        # Marrickville Part 2 - Generic (ALL)
        {
            "document_id": "Marrickville__DCP__2011__-__2__10__Parking",
            "text": "General parking requirements.",
            "expected_zones": ["ALL"],
            "expected_dev_types": ["ALL"],
            "council": "marrickville",
        },
        # Text-based zone extraction
        {
            "document_id": None,
            "text": "This control applies to R2 and R3 zones.",
            "expected_zones": ["R2", "R3"],
            "expected_dev_types": ["ALL"],
            "council": None,
        },
        # Text-based dev type extraction
        {
            "document_id": None,
            "text": "Dwelling houses must have minimum setback.",
            "expected_zones": ["ALL"],
            "expected_dev_types": ["dwelling_house"],
            "council": None,
        },
    ]


@pytest.fixture
def topic_keywords_test_cases():
    """
    Test cases for keyword-based topic extraction.

    Each case has text and expected topic based on earliest keyword match.
    """
    return [
        # Clear single topic
        {"text": "The front setback must be 6m.", "expected_topic": "setbacks"},
        {"text": "Building height is limited to 9m.", "expected_topic": "height"},
        {"text": "Parking must be provided at rear.", "expected_topic": "parking"},
        {"text": "Solar access to neighbours must be maintained.", "expected_topic": "solar"},
        {"text": "Privacy screening is required.", "expected_topic": "privacy"},
        {"text": "Landscaping must cover 30% of site.", "expected_topic": "landscaping"},
        {"text": "Heritage items must be conserved.", "expected_topic": "heritage"},
        {"text": "Tree removal requires approval.", "expected_topic": "trees"},
        {"text": "Front fencing must be transparent.", "expected_topic": "fencing"},
        {"text": "Vehicle access from rear lane.", "expected_topic": "access"},
        {"text": "Stormwater must be managed on-site.", "expected_topic": "stormwater"},
        {"text": "Waste storage at rear.", "expected_topic": "waste"},
        {"text": "Signage must not exceed 2m2.", "expected_topic": "signage"},
        {"text": "Building bulk and scale must be appropriate.", "expected_topic": "building_form"},
        {"text": "Private open space minimum 25m2.", "expected_topic": "open_space"},
        {"text": "Flood-prone land requires assessment.", "expected_topic": "flooding"},
        {"text": "Contaminated land must be remediated.", "expected_topic": "contamination"},
        {"text": "Crime prevention through environmental design.", "expected_topic": "safety"},

        # Multiple keywords - earliest wins
        {"text": "Setback and height controls apply.", "expected_topic": "setbacks"},  # setback appears first
        {"text": "Height and setback controls apply.", "expected_topic": "height"},  # height appears first
        {"text": "Parking and landscaping requirements.", "expected_topic": "parking"},  # parking appears first
    ]
