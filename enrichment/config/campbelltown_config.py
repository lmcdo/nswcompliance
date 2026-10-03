"""Campbelltown (Sustainable City) DCP 2015 — applicability config.

WHY THIS EXISTS
---------------
268 served Campbelltown provisions carried `v2_dev_type_source='no_config'` on
2026-09-23 — every one of them, because the council had no config file at all,
so `_get_config_driven` returned None and each row applied to EVERY development
type by fallthrough rather than by decision. 231 of them arrived on 2026-09-22
when the re-read chapters were published. Same shape as Canterbury-Bankstown,
same day, and the same rule applies: a number made green by a false assertion is
the defect DQ-33 exists to catch.

Campbelltown serves exactly two chapters (`dcp_chapter_registry` WHERE
council='campbelltown'), so this file is short by fact, not by omission.

WHAT A NARROWING COSTS — the reason both entries look sparse
------------------------------------------------------------
Both keys are HARD FILTERS on the served answer:

  v2_applicable_zones      frontend-nextjs/app/api/provisions/for-property/route.ts:1012
  v2_applicable_dev_types  frontend-nextjs/app/api/provisions/for-property/route.ts:1222

A row survives only if the column is NULL, holds 'ALL', or overlaps the query.
Naming a development type here does not improve that type's answer — it DELETES
the row from every other type's answer. The query side is also wider than the
tagger's 16-term DEV_TYPE_PATTERNS: `frontend-nextjs/lib/see/devTypeHierarchy.ts`
also offers subdivision, pool, fence, carport, deck, outbuilding, demolition and
trees as selectable types, and each expands to itself before any parent. So an
enumerated list can look complete against the tagger and still hide a chapter
from a development type a user can actually pick.

Where the chapter's own Application section names a scope, it is recorded.
Where it names one the taxonomy cannot express without dropping part of it, the
key is OMITTED — which yields `config_silent`, "an entry matched and nobody has
decided this key", a different and weaker claim than ALL. That is exactly true,
and it is not `no_config`, which means nothing matched at all.

Both scopes below are quoted from the PDFs the registry points at, read
2026-09-23, not inferred from the chapter titles.
"""

CAMPBELLTOWN_CONFIG: dict = {
    "chapter_topics": {
        # Part 3 — Low and Medium Density Residential Development and Ancillary
        # Residential Structures. Section 3.1 Application, verbatim, sets out:
        #   "General Requirements for all Types of Residential Development in
        #    areas zoned R2, R3, R4 and R5";
        #   development controls for fencing, outbuildings and swimming
        #    pools/spas "in areas zoned R2, R3, R4 and R5 where they are
        #    associated with low and medium density residential development";
        #   dwelling houses (R2, R3), secondary dwellings (R2, R3, R4, R5), dual
        #    occupancies, semi-detached dwellings, attached dwellings, multi
        #    dwelling housing (R3); and section 3.8 residential subdivision.
        #
        # ZONES are therefore stated by the chapter itself and uniform across
        # every one of those lists: R2, R3, R4, R5. All four are current codes in
        # `lep_zone_coverage` for this LGA.
        #
        # applicable_dev_types is OMITTED -> config_silent. The chapter's own
        # scope is "all Types of Residential Development" PLUS its ancillary
        # structures PLUS subdivision, and no enumeration of that survives the
        # hard filter intact: semi-detached and attached dwellings have no term
        # in the tagger vocabulary at all, and a list of the residential terms
        # alone would hide section 3.3 fencing from a `fence` DA, section 3.5
        # outbuildings from an `outbuilding` DA, the pool controls from a `pool`
        # DA and section 3.8 from a `subdivision` DA — all four selectable in the
        # DA scope input (frontend-nextjs/lib/see/ancillaryWorks.ts).
        "campbelltown_dcp_part3_low_medium": {
            "scope_evidence": {
                "applicable_dev_types":
                    "Section 3.1 Application names the Part's development as 'General "
                    "Requirements for all Types of Residential Development' plus its ancillary "
                    "structures plus subdivision, and section 3.5 (PDF p14) states its own "
                    "scope verbatim: 'This section applies to ancillary residential structures "
                    "including outbuildings, swimming pools/spas and fencing in areas zoned R2, "
                    "R3, R4 and R5, where these type of developments are associated with low "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "and medium density residential development.' No enumeration survives the "
                    "hard filter intact: semi-detached and attached dwellings have no term in "
                    "the vocabulary at all, and a list of the residential terms alone would "
                    "hide section 3.3 fencing from a `fence` DA, section 3.5 outbuildings from "
                    "an `outbuilding` DA, the pool controls from a `pool` DA and section 3.8 "
                    "from a `subdivision` DA -- all four selectable in the DA scope input "
                    "(frontend-nextjs/lib/see/ancillaryWorks.ts). ALL is this Part's own "
                    "breadth. Read 2026-10-03; previously OMITTED, which recorded "
                    "`config_silent` on 561 served rows (DQ-114).",
                "applicable_zones":
                    "Part 3 — Low and Medium Density Residential Development and Ancillary Residential Structures. Section 3.1 Application, verbatim, sets out: 'General Requirements for all Types of Residential Development in areas zoned R2, R3, R4 and R5'; development controls for fencing, outbuildings and swimming pools/spas 'in areas zoned R2, R3, R4 and R5 where they are associated with low and medium density residential development'; dwelling houses (R2, R3), secondary dwellings (R2, R3, R4, R5), dual occupancies, semi-detached dwellings, attached dwellings, multi dwelling housing (R3); and section 3.8 residential subdivision. ZONES are therefore stated by the chapter itself and uniform across every one of those lists: R2, R3, R4, R5. All four are current codes in `lep_zone_coverage` for this LGA. applicable_dev_types is OMITTED -> config_silent. The chapter's own scope is 'all Types of Residential Development' PLUS its ancillary structures PLUS subdivision, and no enumeration of that survives the hard filter intact: semi-detached and attached dwellings have no term in the tagger vocabulary at all, and a list of the residential terms alone would hide section 3.3 fencing from a `fence` DA, section 3.5 outbuildings from an `outbuilding` DA, the pool controls from a `pool` DA and section 3.8 from a `subdivision` DA — all four selectable in the DA scope input (frontend-nextjs/lib/see/ancillaryWorks.ts).",  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence, not a lookup table. The zone names are the council's own words; rewriting them to import from the taxonomy would falsify the quote.
            },
            "applicable_dev_types": ["ALL"],
            "applicable_zones": ["R2", "R3", "R4", "R5"],  # noqa: zone-codes (the four zones section 3.1 Application names, on every one of its sub-lists)
            "layer": "generic",
        },

        # Part 4 in the registry; the PDF renumbers itself "Part 5 — Residential
        # Flat Buildings and Mixed-Use Development". Section 5.1 Application,
        # verbatim, covers "residential flat buildings in areas zoned R4; mixed
        # use development in areas zoned B3 and B4; and mixed use development in
        # areas zoned RU5, B1 and B2", and defines mixed use development as
        # development "which includes residential uses (such as shop top housing
        # where relevant) in conjunction with one or more uses such as, business
        # premises, commercial offices, retail shops, community facilities and
        # medical centres".
        #
        # BOTH keys are ["ALL"] -- DECISIONS, declared 2026-10-03. They were OMITTED,
        # which records `config_silent` ("nobody decided this key") on 14 served rows
        # and is counted by DQ-114. The decision is NOT "this applies to everything":
        # it is that the chapter states a scope this field cannot express without
        # either hiding the chapter or interpreting a retired zone code, and ALL is
        # the non-hiding choice. Both reasons below are now carried in scope_evidence
        # so a consumer can read them; a comment is exactly as trustworthy as whoever
        # typed it and is invisible to every check and every page.
        #
        # applicable_dev_types was first written as residential_flat_building,
        # shop_top_housing, commercial_premises, office_premises and
        # retail_premises. That list drops the last two items of the chapter's
        # own definition -- "community facilities and medical centres" -- and
        # the serving taxonomy has no term for either, so there is nothing
        # honest to add. It is not merely incomplete: `child_care_centre` and
        # `educational_establishment` expand only to THEMSELVES in
        # frontend-nextjs/lib/see/devTypeHierarchy.ts (unlike pub, neighbourhood
        # shop or serviced apartment, which all expand through
        # commercial_premises), so a childcare or school DA inside a mixed-use
        # centre would have matched nothing in the list and lost the chapter
        # entirely. Exactly the defect corrected in canterbury_bankstown's
        # chapter_10_4 in the same change; caught here by the cross-review
        # because the same rule had not been applied twice.
        #
        # applicable_zones is OMITTED -> config_silent, and this is the point of
        # having the state: four of the six zones the chapter names — B1, B2, B3,
        # B4 — are RETIRED codes. The 2022 employment-zone reform replaced them,
        # and none of the four appears in `lep_zone_coverage` for Campbelltown
        # today (C1 C2 C3 C4 E1 E2 E3 E4 MU1 R2 R3 R4 R5 RE1 RE2 RU2 RU5 RU6 SP1
        # SP2 W1). Declaring ["R4", "RU5"] alone would hide every mixed-use
        # control from the centres the chapter was written for; mapping B3 and B4
        # onto E2 and MU1 here would be interpreting the instrument, which this
        # repo does not do in a config file. The successor mapping belongs in the
        # zone-migration data with its own citation. That is why the declared value
        # is ALL rather than a translated list -- recorded as a decision, with the
        # retired codes quoted, instead of left to `.get` to invent.
        #
        # `layer` is NOT decoration. `_resolve` opens with `if not entry:
        # return ['ALL'], 'no_config'`, so an entry that declares neither
        # applicability key is an EMPTY DICT and collapses straight back to
        # no_config -- the state this whole file exists to clear, reached by
        # writing the config that was supposed to clear it.
        "part_4_rfb_mixed_use": {
            "scope_evidence": {
                "applicable_zones":
                    "Section 5.1 Application (PDF p2) verbatim: 'Part 5 sets out the "
                    "following: - Desired future character for high density residential "
                    "neighbourhoods in areas zoned R4. - Desired future character for mixed use "
                    "precincts in areas zoned B3 and B4. - General Requirements for residential "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "flat buildings and mixed use development in areas zoned R4, B3 and B4 "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "zones. - Development controls for: residential flat buildings in areas "
                    "zoned R4; mixed use development in areas zoned B3 and B4; and mixed use "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "development in areas zoned RU5, B1 and B2.' FOUR of the six zones it names "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "are RETIRED codes. The 2022 employment-zone reform replaced B1, B2, B3 and "  # noqa: zone-codes - VERBATIM council sentence quoted as scope_evidence; rewriting it to import from the taxonomy would falsify the quote.
                    "B4, and none of the four appears in `lep_zone_coverage` for Campbelltown "
                    "today. Declaring only the two that survive would hide every mixed-use "
                    "control from the centres this chapter was written for, and translating the "
                    "four would be interpreting the instrument in a config file -- B1 "
                    "Neighbourhood Centre and B2 Local Centre BOTH map onto E1 Local Centre, so "  # noqa: zone-codes - names the RETIRED codes in order to say why they are not translated here.
                    "the mapping is not even one-to-one. ALL is the non-hiding answer and is "
                    "now recorded as the decision; the successor mapping belongs in the "
                    "zone-migration data with its own citation.",
                "applicable_dev_types":
                    "The same section 5.1 scopes the development to 'residential flat buildings "
                    "and mixed use development', and the chapter defines its own term on the "
                    "same page, verbatim: 'For the purposes of this part, mixed use development "
                    "is development which includes residential uses (such as shop top housing "
                    "where relevant) in conjunction with one or more uses such as, business "
                    "premises, commercial offices, retail shops, community facilities and "
                    "medical centres.' The last two items have NO term in the serving taxonomy, "
                    "so a list drops them. It is not merely incomplete: `child_care_centre` and "
                    "`educational_establishment` expand only to themselves in "
                    "frontend-nextjs/lib/see/devTypeHierarchy.ts, unlike pub, neighbourhood "
                    "shop or serviced apartment which expand through commercial_premises, so a "
                    "childcare or school DA inside a mixed-use centre would match nothing in "
                    "the list and lose the chapter entirely. ALL is the chapter's own breadth.",
            },
            "applicable_dev_types": ["ALL"],
            "applicable_zones": ["ALL"],
            "layer": "generic",
        },
    },
}
