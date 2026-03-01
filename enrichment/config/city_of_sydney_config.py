"""
City of Sydney DCP 2012 Configuration

Structure (6 per-section PDFs):
- Section 1: Introduction / General Provisions — administrative, applies to ALL
- Section 2: Locality Statements — precinct-specific (includes HCAs, ~75 total)
- Section 3: General Provisions — generic controls applying to all development
- Section 4: Development Types — use-specific (residential, commercial, etc.)
- Section 5: Specific Areas / Precincts — location-filtered
- Section 6: Schedules / Appendices — reference material (generic)

Scale note: Section 2 (Locality Statements) is ~12.88 MB — 75 HCAs covered.
This is the largest per-section PDF and the main HCA coverage for this LGA.

Source: https://www.cityofsydney.nsw.gov.au/development-control-plans/sydney-dcp-2012
Registry pattern: per-section PDFs (6 rows in dcp_chapter_registry)
Chapter keys: section-1-introduction, section-2-locality-statements,
              section-3-general-provisions, section-4-development-types,
              section-5-specific-areas, section-6-schedules
"""

CITY_OF_SYDNEY_CONFIG = {
    "council": "city_of_sydney",
    "dcp_name": "Sydney DCP 2012",
    # City of Sydney has per-section PDFs — topic/layer is encoded in the chapter key
    # (which PDF it came from), not in section headers within each PDF.
    # Uses chapter_topics pattern: keyed by chapter_key slug matched against document_id.
    "chapter_topics": {
        "section_1": {"layer": "generic",      "topic": "general"},
        "section_2": {"layer": "precinct",     "topic": None},   # Locality Statements (HCAs)
        "section_3": {"layer": "generic",      "topic": None},   # General Provisions
        "section_4": {"layer": "use_specific", "topic": None},   # Development Types
        "section_5": {"layer": "precinct",     "topic": None},   # Specific Areas / Precincts
        "section_6": {"layer": "generic",      "topic": None},   # Schedules / Appendices
    },
}
