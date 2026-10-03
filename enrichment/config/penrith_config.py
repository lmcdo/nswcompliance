"""Penrith DCP 2014 — applicability config.

WHY THIS EXISTS
---------------
81 served Penrith provisions had no applicability config, so 55 of them
applied to EVERY development type by fallthrough (DQ-105, 2026-09-23).

Every scope below is quoted from the chapter's own scope section in the PDF the
registry points at, read 2026-09-23 — not inferred from its title. That
distinction is not pedantry: canterbury_bankstown's chapter 9.1 was configured
as industrial on the strength of its position in the numbering, and its own
first page scopes it to Zone E4 while its controls govern food premises and
vehicle body repair workshops.

BOTH KEYS ARE HARD FILTERS on the served answer
------------------------------------------------
  v2_applicable_zones      frontend-nextjs/app/api/provisions/for-property/route.ts:1012
  v2_applicable_dev_types  frontend-nextjs/app/api/provisions/for-property/route.ts:1222

A row survives only if the column is NULL, holds 'ALL', or overlaps the query.
Naming a value does not improve that value's answer — it DELETES the row from
every other answer. So a key is declared only where the chapter states it, and
OMITTED where the chapter's own list cannot be expressed without dropping part
of it. Omitting yields `config_silent` — "an entry matched and nobody decided
this key" — which is true, auditable, and NOT `no_config`.

⚠ An entry that declares neither key is an EMPTY DICT, and `_resolve` opens with
`if not entry: return ['ALL'], 'no_config'`. Such an entry carries `layer` so it
stays truthy; deleting that line sends its rows back to the state this file
exists to clear.
"""

PENRITH_CONFIG: dict = {
    "chapter_topics": {
        # C10's General Objectives address traffic-generating development at
        # large — "to minimise the impacts of traffic generating developments
        # and manage road safety issues" — and the Part states no narrowing of
        # zone or development type anywhere in its 29 pages. A transport and
        # parking Part binds anything that generates a trip, so ALL is a
        # decision here rather than a fallthrough, the same reading given to
        # canterbury_bankstown's chapter_3_2_parking.
        "c10_transport_access_parking": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },

        # BOTH KEYS ARE ["ALL"] -- DECISIONS, and the reason is in the Part's own
        # contents. "D2 Residential Development" reads like a residential-only
        # Part and is not one: its sections are 2.1 Single Dwellings, 2.2 Dual
        # Occupancies, 2.4 Multi Dwelling Housing, 2.5 Residential Flat Buildings
        # — and 2.6 NON RESIDENTIAL DEVELOPMENTS. Declaring the residential types
        # would delete section 2.6 from every non-residential application it
        # governs, which is the asymmetric failure this file is most careful to
        # avoid. The Part states no zones either.
        #
        # Declared 2026-10-03. They were OMITTED, which is the same value by a
        # route that records `config_silent` -- "nobody decided this key" -- on 75
        # served rows, counted by DQ-114. The decision was made; it was just kept
        # in a comment no consumer can read.
        "penrith_dcp_2014_part_d2": {
            "scope_evidence": {
                "applicable_dev_types":
                    "The Part's own table of contents (PDF pp1-2) runs '2.1. SINGLE DWELLINGS', "
                    "'2.2 DUAL OCCUPANCIES', '2.3. SECONDARY DWELLINGS', '2.4 MULTI DWELLING "
                    "HOUSING', '2.5 RESIDENTIAL FLAT BUILDINGS' and then '2.6 NON RESIDENTIAL "
                    "DEVELOPMENTS'. Section 2.6 (PDF p79, printed D2-79) states its own scope "
                    "verbatim: 'The following developments are covered by this section: a) Any "
                    "proposed non residential development proposed in a residential zone. This "
                    "section provides specific controls for non residential development in "
                    "residential zones in addition to the general controls elsewhere in this DCP.' "
                    "So the five residential terms are NOT the Part's scope -- declaring them "
                    "would delete section 2.6 from every non-residential application it governs. "
                    "ALL is the Part's own breadth.",
                "applicable_zones":
                    "NO land-application clause exists. All 84 pages were read 2026-10-03 and the "
                    "Part carries no 'land to which this Part applies' section; its first pages are "
                    "table of contents straight into section 2.1. The only zone sentence in the "
                    "Part is section 2.6's (PDF p79): 'Any proposed non residential development "
                    "proposed in a residential zone' -- and that WIDENS what the Part reaches "
                    "rather than bounding it, because it brings non-residential development on "
                    "residential land into a Part whose other sections are residential types. "
                    "Penrith DCP 2014's own introductory Part, which would carry the plan-level "
                    "sentence, is not in dcp_chapter_registry (only part-d2 and "
                    "c10-transport-access-parking are), so the inherited sentence cannot be quoted "
                    "and is NOT guessed. ALL records that this Part states no zone narrowing, "
                    "which is true and checkable; a zone list inferred from the Part's TITLE would "
                    "be interpretation, and it would hide the Part from the non-residential "
                    "development section 2.6 covers.",
            },
            "applicable_dev_types": ["ALL"],
            "applicable_zones": ["ALL"],
            "layer": "generic",
        },
    },
}
