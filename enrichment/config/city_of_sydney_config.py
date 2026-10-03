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

#: Every chapter here is a whole PDF section of one plan, so every entry shares
#: the plan's own scope sentence. Written once and referenced, rather than pasted
#: seven times, so a correction to the quote cannot land on some entries only.
_SCOPE = (
    "Section 1 Introduction, clause 1.4 'Land to which this DCP applies', page 4, verbatim: "
    "'This development control plan applies to the land identified in Figure 1.1 Land covered "
    "by this DCP where the City of Sydney is the consent authority.' "
    "EIGHT AREAS ARE EXCLUDED and no key in this config can express that: Figure 1.1 (page 5) "
    "names Barangaroo, Bays Precinct/Wentworth Park, Harold Park, Redfern/Waterloo, Various "
    "Sites (South Sydney), Green Square Town Centre, Moore Park Showground and Glebe "
    "(Affordable Housing) as land excluded from this DCP, each keeping its own plan. The "
    "exclusion is a mapped boundary, not a zone, so ALL is a known over-reach at those eight "
    "sites -- recorded rather than approximated, because no zone list excludes them without "
    "also removing the DCP from land it does bind."
)
_SCOPE_DT = (
    "Section 1 Introduction, clause 1.4, page 4: the plan applies to 'the land identified in "
    "Figure 1.1 ... where the City of Sydney is the consent authority' and states no "
    "development-type limit of its own."
)
_ALL = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"]}

CITY_OF_SYDNEY_CONFIG = {
    "council": "city_of_sydney",
    "dcp_name": "Sydney DCP 2012",
    # City of Sydney has per-section PDFs — topic/layer is encoded in the chapter key
    # (which PDF it came from), not in section headers within each PDF.
    # Uses chapter_topics pattern: keyed by chapter_key slug matched against document_id.
    # ── SCOPE, added 2026-10-03 ────────────────────────────────────────────────
    # Until now these entries declared neither applicable_zones nor
    # applicable_dev_types, so all 2,407 served City of Sydney rows carried
    # v2_dev_type_source = v2_zone_source = 'config_silent': an entry matched and
    # nobody had decided either key. That is a third of DQ-114's whole count.
    #
    # THE AUTHORITY, read from the PDF on 2026-10-03. Section 1 Introduction,
    # clause 1.4 "Land to which this DCP applies", page 4:
    #
    #   "This development control plan applies to the land identified in
    #    Figure 1.1 Land covered by this DCP where the City of Sydney is the
    #    consent authority."
    #
    # ⚠ EIGHT AREAS ARE EXCLUDED and this config cannot express that. Figure 1.1
    # on page 5 names them, each keeping its own DCP: 1 Barangaroo, 2 Bays
    # Precinct/Wentworth Park, 3 Harold Park, 4 Redfern/Waterloo, 5 Various Sites
    # (South Sydney), 6 Green Square Town Centre, 7 Moore Park Showground,
    # 8 Glebe (Affordable Housing). The exclusion is a MAPPED BOUNDARY, not a zone
    # or a development type, so neither declared key can carry it. ALL is
    # therefore a known over-reach at those eight sites, recorded rather than
    # approximated: there is no zone list that would exclude them without also
    # removing the DCP from land it does bind.
    #
    # WHY ALL ON BOTH KEYS IS HONEST HERE, not a fallthrough. The config keys on
    # the chapter, and a City of Sydney chapter is a whole PDF section. Section 4
    # Development Types is use-specific INSIDE itself, chapter by chapter, which
    # is a granularity this file cannot reach -- narrowing the whole section to
    # any one type would delete it from every other type's answer. Sections 2, 5
    # and 6 are precinct-scoped and their geography is carried by v2_precinct_id
    # on each rule, not by a zone list.
    "chapter_topics": {
        "section_1": {
            "layer": "generic", "topic": "general",
            "scope_evidence": {
                "applicable_zones": _SCOPE + " Section 1 is the introduction and administration of the plan itself, so it binds the same land the plan does.",
                "applicable_dev_types": _SCOPE_DT + " Section 1 is administrative and type-neutral.",
            },
            **_ALL,
        },
        "section_2": {   # Locality Statements (HCAs)
            "layer": "precinct", "topic": None,
            "scope_evidence": {
                "applicable_zones": _SCOPE + " Section 2 Locality Statements is scoped to ~75 named localities and heritage conservation areas; that geography is carried by v2_precinct_id on each rule, not by a zone list. A zone list would hide a locality statement from any lot inside the locality carrying another zone.",
                "applicable_dev_types": _SCOPE_DT + " A locality statement binds whatever is developed within its locality, so no development type is excluded.",
            },
            **_ALL,
        },
        "section_3": {   # General Provisions
            "layer": "generic", "topic": None,
            "scope_evidence": {
                "applicable_zones": _SCOPE + " Section 3 General Provisions carries the controls that apply across the plan, so it binds the plan's whole area.",
                "applicable_dev_types": _SCOPE_DT + " General provisions are written for development generally; this section holds 1,411 of the council's served rules and narrowing it would remove them from every type left out.",
            },
            **_ALL,
        },
        "section_4": {   # Development Types
            "layer": "use_specific", "topic": None,
            "scope_evidence": {
                "applicable_zones": _SCOPE + " Section 4 is organised by development type rather than by zone, and names none of its own.",
                "applicable_dev_types": _SCOPE_DT + " ⚠ Section 4 IS use-specific, but chapter by chapter INSIDE the PDF -- residential, commercial and the rest sit side by side in one file. This config keys on the chapter, which is the whole section, so it cannot reach that granularity. ALL is the only non-destructive answer available here: naming any one type would delete the section from every other type's answer. The real fix is per-chapter keys within Section 4, not a list at this level.",
            },
            **_ALL,
        },
        "section_5": {   # Specific Areas / Precincts
            "layer": "precinct", "topic": None,
            "scope_evidence": {
                "applicable_zones": _SCOPE + " Section 5 Specific Areas is precinct-scoped; the geography is carried by v2_precinct_id, not by a zone list.",
                "applicable_dev_types": _SCOPE_DT + " A specific-area control binds whatever is developed in that area.",
            },
            **_ALL,
        },
        "section_6": {   # Specific Sites
            "layer": "precinct", "topic": None,
            "scope_evidence": {
                "applicable_zones": _SCOPE + " Section 6 Specific Sites is scoped to named sites; the geography is carried by v2_precinct_id, not by a zone list.",
                "applicable_dev_types": _SCOPE_DT + " A site-specific control binds whatever is developed on that site.",
            },
            **_ALL,
        },
        "schedules": {   # Schedules / Appendices
            "layer": "generic", "topic": None,
            "scope_evidence": {
                "applicable_zones": _SCOPE + " The schedules are reference material to the plan and share its extent.",
                "applicable_dev_types": _SCOPE_DT + " The schedules are referenced from controls across the plan, so they are type-neutral.",
            },
            **_ALL,
        },
    },
}
