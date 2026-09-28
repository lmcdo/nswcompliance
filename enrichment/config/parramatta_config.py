r"""Parramatta DCP 2023 (Amendment 4) — applicability config.

SHAPE: the `parts` path, not `chapter_topics`. The whole DCP is stored as ONE
1,563-page document (`Parramatta_DCP_2023_(Amendment_4)__parramatta_dcp_2023`),
so there is no per-chapter document_id to key on. The Part is already in each
rule's own section reference — `# 8.2.3 GRANVILLE LOCAL CENTRE`, `# 7.2 CONSENT
REQUIREMENTS`, `# 4.2 BUSINESS AND COMMERCIAL DEVELOPMENT` — and
`_extract_section_code` reads one on 584 of 616 served rows (measured
2026-09-24). Same decision as Northern Beaches, for the same reason: splitting
the PDF to recover structure the data already holds would mean re-extracting,
and a re-read has gutted a chapter before.

WHERE EACH SCOPE COMES FROM — every one quoted from the plan itself
-------------------------------------------------------------------
* Part 4 states its own reach outright: "This Part of this DCP applies to all
  non-residential types of development. All controls contained in this Part
  must be read in conjunction with Part 2 – Design in Context, Part 5 –
  Environmental Management and Part 6 – Traffic and Parking." That sentence is
  also what establishes Parts 2, 5 and 6 as GENERAL rather than residential:
  the non-residential Part is told to read them too.
* Part 5: "controls to address the environmental impact of development on sites
  and surrounding areas to ensure hazard and pollution is managed appropriately
  throughout the City."
* Part 6: "requirements for sustainable transport measures such as carshare,
  travel plans and electric vehicle charging infrastructure ... across the City."
* Part 7: "the consent requirements for various types of works on heritage
  items, archaeological site or a building or place within a heritage
  conservation area." A SITE CONDITION — it binds whatever is proposed on land
  carrying the listing, not a class of development.
* Part 8 is a series of named places: "The provisions of this Section of this
  DCP apply to development within Granville Local Centre (shown in Figure
  8.2.3.1)"; Carlingford is "referred to in this Section of this DCP as the
  Carlingford Precinct ... for a range of built forms that allow for a mix of
  housing styles, commercial, retail and community uses."
* Part 9 is the Parramatta City Centre, likewise geographic, and carries its own
  carve-outs internally ("A further exception to the application of this Part is
  that the controls for the Park Edge Highly Sensitive Area ...").

A geographic scope is a real assertion of universality on development type —
every development inside the named area is bound — so Parts 8 and 9 are recorded
as `config_all` with `is_precinct_specific`, exactly as Warringah's Part G is.

WHY THE MISREADS CANNOT DO ANY DAMAGE HERE
-------------------------------------------
`_extract_section_code` matches a leading number, so content lines beginning
with a digit parse as bare section codes: `# 1 Bedroom 10 – 20% of total
dwellings` (really Melrose Park, Part 8), `# 6 Metre Wide Lanes` (really
Granville, Part 8), `# 3 Design excellence ...` (really Site Specific, Part 9),
`# 772 Parramatta Development Control Plan 2023` (a page footer). A bare `1`
hits `parts["1"]` directly, so a config that narrowed Part 1 would silently
narrow Melrose Park rows onto it.

Nothing here narrows: every entry declares `["ALL"]` on both axes, so a misread
inherits a scope that cannot hide it from anyone. That is why Part 1 is ABSENT
rather than declared — its 8 rows are all bare-number misreads belonging to
Melrose Park and Epping, and an entry would be a statement about rows that are
not its own.
The progressive strip is what keeps the rest safe — `re.sub(r'\.?\d+$','',...)`
turns `772` into `''`, not `7`, so a page footer never inherits the heritage
Part.

WHAT IS DELIBERATELY ABSENT, AND WHY A `layer` FILLER WOULD HAVE BEEN WORSE
----------------------------------------------------------------------------
Parts 1, 3, 4, 10 and 12-17 have NO entry at all. The first draft of this file
gave them `{"layer": "generic"}` — the Campbelltown pattern, a filler key that
keeps an entry truthy so `_resolve` records `config_silent` ("an entry matched
but omitted this key") instead of `no_config` ("nothing matched"). That looked
like an improvement in provenance at no cost.

It is not free, and the dry run said so. **`config_silent` still returns
`['ALL']`.** An entry that declares nothing does not defer to the text — it
REPLACES whatever the text regex derived. Measured 2026-09-24, the filler
version destroyed 63 rows' worth of text-derived dev types:

  Part  3   47 rows   e.g. id=105101 lost ['residential_flat_building']
  Part 10    9 rows   e.g. id=105630 lost ['food_and_drink_premises', ...]
  Part  4    7 rows   e.g. id=105112 lost ['commercial_premises',
                          'office_premises', 'retail_premises',
                          'shop_top_housing', ...]

That id=105112 list is a good reading of a Part whose own words are "this Part
of this DCP applies to all non-residential types of development". Overwriting it
with an invented ALL would put a commercial control in front of a dwelling
house. No entry at all leaves the text regex in place and lets DQ-33 keep
counting the row, which is the truthful state: nobody has decided this Part's
scope yet.

The rule this file adds to the pattern: **a filler key is only free when the
rows under it have nothing text-derived to lose.** Check before adding one.

Part 1 is absent for a different reason — all 8 of its rows are bare-number
misreads that belong to Melrose Park and Epping, so any entry would be a
statement about rows that are not its own. The 32 rows carrying no readable code
stay unmatched too. Guessing a Part for them to improve the numbers is the
behaviour DQ-33 exists to refuse.
"""

#: A general control, binding any development anywhere in the LGA.
_GENERAL = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"]}

#: A named place: every development inside the area is bound by it.
_AREA = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
         "is_precinct_specific": True}


PARRAMATTA_CONFIG: dict = {
    "parts": {
        # Part 2 Design in Context — Part 4 is directed to read it, so it is
        # not a residential-only chapter.
        "2": _GENERAL,

        # Part 5 Environmental Management — "throughout the City".
        "5": _GENERAL,

        # Part 6 Traffic and Transport — "across the City".
        "6": _GENERAL,

        # Part 7 Heritage and Archaeology — a site condition. It binds whatever
        # is proposed on a heritage item, archaeological site, or a building or
        # place in a conservation area.
        "7": {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
              "site_conditions": ["heritage"]},

        # Part 8 Strategic Centres and Local Centres — Epping, Melrose Park,
        # Granville, Carlingford and the rest. Scoped geographically, so every
        # development within the named centre is bound. 8.x.y.z all reach this
        # through the progressive strip.
        "8": _AREA,

        # Part 9 Parramatta City Centre — likewise geographic, with its
        # exceptions stated inside the Part rather than here.
        "9": _AREA,
    },
}
