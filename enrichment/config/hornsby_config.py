"""Hornsby DCP 2024 — applicability config.

WHY THIS EXISTS
---------------
58 served Hornsby provisions had no applicability config, so 24 of them
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

HORNSBY_CONFIG: dict = {
    "chapter_topics": {
        # Introduction, verbatim: "This Development Control Plan (DCP) applies
        # to all land" within the Hornsby Shire. A general-provisions Part binds
        # every application, so ALL is a decision.
        "part_1_general": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "scope_evidence": {
                "applicable_zones":
                    "Introduction, verbatim: 'This Development Control Plan (DCP) applies to "
                    "all land' within the Hornsby Shire. A general-provisions Part binds every "
                    "application, so ALL is a decision.",
                "applicable_dev_types":
                    "Introduction, verbatim: 'This Development Control Plan (DCP) applies to "
                    "all land' -- the scope is stated once and binds both keys.",
            },
            "layer": "generic",
        },

        # Introduction, verbatim: "This Part of the DCP applies to residential
        # development within the Residential zones of the Hornsby Local
        # Government Area."
        #
        # R2/R3/R4 are the residential zones that EXIST for this LGA in
        # lep_zone_coverage — Hornsby has no R1 and no R5, so neither is
        # declared. applicable_dev_types is ["ALL"] -- a DECISION. The Part binds
        # residential development as a whole, and the same page splits its controls
        # by density, not by type: low density follows the NSW Housing Code, medium
        # and high density follow the Housing Strategy. A type list this vocabulary
        # can express does not exist. Declared 2026-10-03; OMITTED recorded
        # `config_silent` (DQ-114).
        "hornsby_dcp_2024_part3_residential": {
            "scope_declined": ("applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones":
                    "Introduction, verbatim: 'This Part of the DCP applies to residential development within the Residential zones of the Hornsby Local Government Area.' R2/R3/R4 are the residential zones that EXIST for this LGA in lep_zone_coverage — Hornsby has no R1 and no R5, so neither is declared.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table. The zone names are the council's own words; rewriting them to import from the taxonomy would falsify the quote.
                "applicable_dev_types":
                    "Introduction (PDF p3), verbatim: 'This Part of the DCP applies to "
                    "residential development within the Residential zones of the Hornsby Local "
                    "Government Area.' The Part binds residential development AS A WHOLE and "
                    "enumerates no type; the same page splits its controls by DENSITY, not by "
                    "type: 'The planning controls for the low density residential areas are "
                    "informed by the NSW Housing Code, while the planning controls for the "
                    "medium and high density residential areas are informed by the Hornsby "
                    "Shire Housing Strategy (2010) and Hornsby Local Housing Strategy (2020).' "
                    "A five-term residential list would be a NEW narrowing this Part never "
                    "states, and would delete it from every other use permitted in the three "
                    "residential zones declared above. ALL is the Part's own breadth, read "
                    "2026-10-03. Previously OMITTED, "
                    "which recorded `config_silent` on 101 served rows (DQ-114).",
            },
            "applicable_zones": ["R2", "R3", "R4"],  # noqa: zone-codes (the LGA's residential zones, per lep_zone_coverage)
            # Sections 3.2 to 3.4 each open by naming their zone (read from the live PDF 2026-11-27); the row's PDF
            # page picks the section. 3.1 (says R2 only) and 3.5 stay on the Part's zones: narrowing 3.1 would hide
            # house rules from houses in R3/R4, and 3.5 also covers seniors housing on a height-map "Area 3" whose
            # zone is not established (the current height map shows no 20.5 m area).
            "page_sections": (
                {"first_page": 17, "last_page": 39, "applicable_zones": ["R3"],  # noqa: zone-codes - the council's words
                 "scope_evidence": {"applicable_zones":
                     "Section 3.2 (PDF p17), verbatim: 'This section provides controls for erecting and undertaking "
                     "alterations and additions to medium density housing except for three storey residential flat "
                     "buildings in the R3 Medium Density Residential Zone'"}},  # noqa: zone-codes - verbatim quote
                {"first_page": 40, "last_page": 51, "applicable_zones": ["R3", "R4"],  # noqa: zone-codes - the council's words
                 "scope_evidence": {"applicable_zones":
                     "Section 3.3 (PDF p40), verbatim: 'a residential flat building in the R3 Medium Density "
                     "Residential Zone and the R4 High Density Residential Zone'"}},  # noqa: zone-codes - verbatim quote
                {"first_page": 52, "last_page": 82, "applicable_zones": ["R4"],  # noqa: zone-codes - the council's words
                 "scope_evidence": {"applicable_zones":
                     "Section 3.4 (PDF p52), verbatim: 'residential flat buildings in the R4 High Density "
                     "Residential Zone'"}},  # noqa: zone-codes - verbatim quote
            ),
            "layer": "generic",
        },
    },
}
