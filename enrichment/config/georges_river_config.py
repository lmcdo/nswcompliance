"""Georges River DCP 2021 — applicability config.

WHY THIS EXISTS
---------------
33 served Georges River provisions had no applicability config, so 19 of
them applied to EVERY development type by fallthrough (DQ-105, 2026-09-23).

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

GEORGES_RIVER_CONFIG: dict = {
    "chapter_topics": {
        # Part 3, verbatim: this Part "applies to all forms of development."
        # A general-planning-considerations Part binds every application, so ALL
        # is a decision rather than a fallthrough.
        "part_3_general_planning_considerations": {
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "layer": "generic",
        },

        # Section 6.1.1 Introduction, verbatim: "This part applies to dwelling
        # houses, dual occupancy development, secondary dwellings and narrow lot
        # housing."
        #
        # Three of the four have a term in the vocabulary. "Narrow lot housing"
        # does not — and, checked 2026-09-23, neither does the SERVING taxonomy
        # in frontend-nextjs/lib/see/devTypeHierarchy.ts, so no query can ask for
        # it and naming the other three hides nothing. That check is the whole
        # test: a missing term matters only when somebody can select it.
        #
        # applicable_zones is OMITTED — the Part names development forms, not
        # zones, and Georges River's R2/R3/R4 would be an inference rather than a
        # quotation.
        "grdcp_part_6_1_low_density": {
            "scope_evidence": {
                "applicable_dev_types":
                    "Section 6.1.1 Introduction, verbatim: 'This part applies to dwelling houses, dual occupancy development, secondary dwellings and narrow lot housing.' Three of the four have a term in the vocabulary. 'Narrow lot housing' does not — and, checked 2026-09-23, neither does the SERVING taxonomy in frontend-nextjs/lib/see/devTypeHierarchy.ts, so no query can ask for it and naming the other three hides nothing. That check is the whole test: a missing term matters only when somebody can select it. applicable_zones is OMITTED — the Part names development forms, not zones, and Georges River's R2/R3/R4 would be an inference rather than a quotation.",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table. The zone names are the council's own words; rewriting them to import from the taxonomy would falsify the quote.
            },
            "applicable_dev_types": ["dwelling_house", "dual_occupancy",
                                     "secondary_dwelling"],
        },
    },
}
