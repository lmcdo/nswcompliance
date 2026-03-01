"""
Ku-ring-gai Development Control Plans Configuration

Structure: Multiple numbered topic-DCPs (structurally distinct from single-DCP LGAs).
Topic is encoded in the DCP name / chapter key, not in section headers.

Known DCPs:
- Principal DCP: General controls applying across the LGA
- DCP 28: Signs and Advertising
- DCP 31: Access and Mobility
- DCP 38: Residential Design
- DCP 40: Demolition and Site Waste Management
- DCP 43: Car Parking
- DCP 46: Exempt and Complying Development
- DCP 47: Water Management
- DCP 48: Medium Density Housing

Heritage location: assumed to be in the Principal DCP (confirm from profiling).
Each DCP is a separate chapter in dcp_chapter_registry.

Source: https://www.krg.nsw.gov.au/Planning-and-development/Planning-policies-and-guidelines/Ku-ring-gai-Development-Control-Plan
"""

KU_RING_GAI_CONFIG = {
    "council": "ku_ring_gai",
    "dcp_name": "Ku-ring-gai DCP",
    # Topic is encoded in the DCP name → use chapter_topics pattern.
    # Keys are chapter_key slugs (with underscores, as built by resolve_document_id).
    # Matched against document_id from the provision's source chapter.
    "chapter_topics": {
        "principal_dcp":           {"layer": "generic",      "topic": None},
        "dcp_28_signs":            {"layer": "generic",      "topic": "signage"},
        "dcp_31_access":           {"layer": "generic",      "topic": "access"},
        "dcp_38_residential":      {"layer": "use_specific", "topic": "residential"},
        "dcp_40_demolition_waste": {"layer": "generic",      "topic": "waste"},
        "dcp_43_car_parking":      {"layer": "generic",      "topic": "parking"},
        "dcp_46_exempt_complying": {"layer": "generic",      "topic": "exempt_complying"},
        "dcp_47_water":            {"layer": "generic",      "topic": "water"},
        "dcp_48_medium_density":   {"layer": "use_specific", "topic": "medium_density"},
    },
}
