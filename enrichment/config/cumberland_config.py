"""Cumberland DCP 2021 -- applicability config (Part B, Residential Zones).

WHY THIS EXISTS
---------------
170 served Cumberland rows carried `v2_dev_type_source='no_config'` on 2026-10-15
(DQ-33): the council had no config file, so `_get_config_driven` returned None and
every row of the one ingested document fell through to ALL development types
because nothing matched, not because anything decided it.

WHY THE DEVELOPMENT-TYPE KEY IS DECLINED, NOT ALL AND NOT A LIST
-----------------------------------------------------------------
The document is Part B -- FIVE sub-Parts in one PDF, and the plan scopes each to a
different development type in its own "1.1 Land to which this Part applies"
(chapter PDF pages 8, 31, 39, 45, 53):

  B1  dwelling house, secondary dwelling and associated outbuildings
  B2  "low rise dual occupancy development"
  B3  "residential flat building development"
  B4  "development of land for the purposes of a boarding house"
  B5  "all residential development types except for single dwelling house"

A row's sub-Part cannot be told from the row: each sub-Part restarts its section
numbers at 1.x/2.x, so `# 2.1 Setbacks` exists in the first sub-Part and `# 1.2` in each
of the other four. Naming any one list would DELETE the row from every other type's answer (a
hard filter, see campbelltown_config.py), and ALL would assert universality the
plan itself contradicts. `scope_declined` is the true state: a person read the
Part and narrowing cannot be done without hiding rules. It is ALL as a value, a
recorded decision rather than a fallthrough, and it stops being `no_config`.
Resolving the sub-Part from the PDF page would let this narrow properly; that
needs the page threaded into the tagger and is not done here.

ZONES are stated once for the whole Part (p8) and are the values the 291 rows
already carry, so declaring them changes no served zone.
"""

CUMBERLAND_CONFIG: dict = {
    "chapter_topics": {
        "cumberland_dcp_part_b_residential": {
            "applicable_zones": ["R2", "R3", "R4"],  # noqa: zone-codes (the LGA's residential zones, per lep_zone_coverage)
            "scope_declined": ("applicable_dev_types",),
            "scope_evidence": {
                "applicable_zones":
                    "Part B1 section 1.1 'Land to which this Part applies' (chapter PDF p8) "
                    "verbatim: 'This Part applies to development types detailed within this Part "
                    "within land zoned Residential under Cumberland Local Environmental Plan "
                    "2021.' The residential zones recorded for Cumberland in lep_zone_coverage "
                    "are the three R zones declared above.",
                "applicable_dev_types":
                    "Five sub-Parts, five different scopes, one document. B1 section 1.2 (PDF p8) "
                    "verbatim: 'This Part is intended to guide the assessment of the development "
                    "of a dwelling house, secondary dwelling and associated outbuildings.' B2 "
                    "section 1.1 (p31): 'This Part applies to low rise dual occupancy development "
                    "under the Cumberland Local Environment Plan 2021.' B3 (p39): 'This Part "
                    "applies to residential flat building development under the Cumberland Local "
                    "Environment Plan 2021.' B4 (p45): 'This Part applies to development of land "
                    "for the purposes of a boarding house under the Cumberland Local Environmental "
                    "Plan 2021.' B5 (p53): 'This Part applies to all residential development "
                    "types except for single dwelling house development under the Cumberland "
                    "Local Environmental Plan 2021.' A row's sub-Part is not recoverable from the "
                    "row (each restarts at 1.x/2.x), so any list would hide rules from the types "
                    "left out; ALL would contradict the first four sub-Parts. Declined.",
            },
        },
    },
}
