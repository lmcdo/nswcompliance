"""Blacktown DCP 2015 — applicability config.

WHY THIS EXISTS
---------------
125 served Blacktown provisions had no applicability config, so 56 of them
applied to EVERY development type by fallthrough rather than by decision
(DQ-105, measured 2026-09-23).

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

BLACKTOWN_CONFIG: dict = {
    "chapter_topics": {
        # Section 1.1 "Land to which this Part applies", verbatim: "This Part of
        # the DCP applies to all land within the Blacktown Local Government Area
        # zoned for residential purposes under Blacktown LEP 2015."
        #
        # The R-series is what "zoned for residential purposes" names, and the
        # four below are the ones that EXIST for this LGA in lep_zone_coverage —
        # taken from the data rather than assumed, so a zone Blacktown does not
        # have is never declared. applicable_dev_types is OMITTED: the Part binds
        # ALL development in those zones, not a list of types, and naming types
        # would delete it from every type left out.
        "blacktown_dcp_2015_part_c": {
            "scope_evidence": {
                "applicable_zones":
                    "Section 1.1 'Land to which this Part applies', verbatim: 'This Part of the DCP applies to all land within the Blacktown Local Government Area zoned for residential purposes under Blacktown LEP 2015.' The R-series is what 'zoned for residential purposes' names, and the four below are the ones that EXIST for this LGA in lep_zone_coverage — taken from the data rather than assumed, so a zone Blacktown does not have is never declared. applicable_dev_types is OMITTED: the Part binds ALL development in those zones, not a list of types, and naming types would delete it from every type left out.",
            },
            "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes (the LGA's residential zones, per lep_zone_coverage)
            "layer": "generic",
        },

        # Section 1.1 "Land to which this DCP applies", verbatim: "Blacktown DCP
        # 2015 applies to all land within the Blacktown Local Government Area
        # that is zoned under Blacktown Local Environmental Plan (LEP) 2015."
        #
        # ALL on both keys is a real assertion here, not a fallthrough: a car
        # parking Part binds any development that generates a parking demand,
        # and the chapter says so itself.
        "part_a_car_parking": {
            "scope_evidence": {
                "applicable_dev_types":
                    "Section 1.1 'Land to which this DCP applies', verbatim: 'Blacktown DCP 2015 applies to all land within the Blacktown Local Government Area that is zoned under Blacktown Local Environmental Plan (LEP) 2015.' ALL on both keys is a real assertion here, not a fallthrough: a car parking Part binds any development that generates a parking demand, and the chapter says so itself.",
                "applicable_zones":
                    "Section 1.1 'Land to which this DCP applies', verbatim: 'Blacktown DCP 2015 applies to all land within the Blacktown Local Government Area that is zoned under Blacktown Local Environmental Plan (LEP) 2015.' ALL on both keys is a real assertion here, not a fallthrough: a car parking Part binds any development that generates a parking demand, and the chapter says so itself.",
            },
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },
    },
}
