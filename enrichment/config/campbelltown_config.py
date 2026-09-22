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
        # DEV TYPES follow directly from that sentence and are recorded.
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
        # zone-migration data with its own citation, and until it lands the
        # honest state is that nobody has decided this key.
        "part_4_rfb_mixed_use": {
            "applicable_dev_types": ["residential_flat_building", "shop_top_housing",
                                     "commercial_premises", "office_premises",
                                     "retail_premises"],
        },
    },
}
