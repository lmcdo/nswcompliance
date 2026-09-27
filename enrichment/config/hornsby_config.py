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
            "layer": "generic",
        },

        # Introduction, verbatim: "This Part of the DCP applies to residential
        # development within the Residential zones of the Hornsby Local
        # Government Area."
        #
        # R2/R3/R4 are the residential zones that EXIST for this LGA in
        # lep_zone_coverage — Hornsby has no R1 and no R5, so neither is
        # declared. applicable_dev_types is OMITTED: the Part binds residential
        # development as a whole, and the same page records that its low-density
        # controls follow the NSW Housing Code while its medium and high density
        # controls follow the Housing Strategy — a split by density, not a list
        # of types this vocabulary can express.
        "hornsby_dcp_2024_part3_residential": {
            "scope_evidence": {
                "applicable_zones":
                    "Introduction, verbatim: 'This Part of the DCP applies to residential development within the Residential zones of the Hornsby Local Government Area.' R2/R3/R4 are the residential zones that EXIST for this LGA in lep_zone_coverage — Hornsby has no R1 and no R5, so neither is declared. applicable_dev_types is OMITTED: the Part binds residential development as a whole, and the same page records that its low-density controls follow the NSW Housing Code while its medium and high density controls follow the Housing Strategy — a split by density, not a list of types this vocabulary can express.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table. The zone names are the council's own words; rewriting them to import from the taxonomy would falsify the quote.
            },
            "applicable_zones": ["R2", "R3", "R4"],  # noqa: zone-codes (the LGA's residential zones, per lep_zone_coverage)
            "layer": "generic",
        },
    },
}
