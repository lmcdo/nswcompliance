"""Warringah DCP 2011 (Northern Beaches) — applicability config.

WHY THIS ONE IS DIFFERENT FROM THE OTHERS IN THIS DIRECTORY
------------------------------------------------------------
The whole DCP is stored as ONE document — `warringah_dcp_2011_full` — so there
is no per-chapter document_id to key on, and the `chapter_topics` shape every
other council here uses cannot express it. That looked like a reason to split
the PDF into Parts and re-extract.

It is not. **The Part is already recorded in every rule's own section
reference**: `# G9.1.5.1.14 C2 Signage`, `# E11 C1 Flood Prone Land`,  # noqa: zone-codes (Warringah DCP PART letters, not NSW zone codes)
`# D23 O4 Signs`. Measured 2026-09-23, `_extract_section_code` reads a code on
1,560 of 1,602 served rows. So this uses the EXISTING `parts` path — the one
Woollahra and Waverley use — which reads that code out of the text and strips it
progressively (`G9.1` -> `G9` -> `G`).

That matters beyond tidiness. Re-extracting to recover structure the data
already holds would have risked the thing `dcp_commit_approved`'s section-loss
guard exists to catch: a re-read has gutted a chapter before. This needed no new
code, no new registry rows, and no change to a single provision's provenance.

WHERE EACH SCOPE COMES FROM
---------------------------
Section A.6 "Parts of the DCP", in the plan's own words:

  * "A series of built form controls, including setbacks and landscaped open
    space, is contained in Part C, D and E" — general controls, binding any
    development.
  * "Part F covers development and activities in certain zones and sensitive
    areas e.g. local and neighbourhood centres" — a scope this file does NOT
    enumerate; see the entry.
  * "Part G applies controls to special areas of Warringah e.g. parts of Dee
    Why, Warringah Mall" and, decisively, "where there is inconsistency with
    Parts C, D and E, the requirements of Part G will prevail."
  * "Part H is a compilation of relevant appendices e.g. carparking and
    vegetation matters."

The G-series are named places — G3 Belrose Corridor, G4 Warringah Mall, G5
Freshwater Village, G6 Dee Why RSL Club, G8 Narrabeen, G9 Frenchs Forest Town
Centre, G10 Low and Mid-Rise Housing Areas. Scoped GEOGRAPHICALLY, so every
development inside one is bound by it: that is a real assertion of universality
on development type, not a fallthrough, and it is recorded as `config_all`.

⚠ WHAT IS DELIBERATELY NOT HERE. 110 served rows carry a bare numeric code
(`# 5.4.7 C9 Basement entries`, `# 8 C5.2 Green roofs`, `# 6 C10.1 Car share`)
which belongs to no Part letter in this plan's structure, and 42 carry no code
at all. Guessing a Part for them to improve the numbers is the behaviour DQ-33
exists to refuse, so they stay unmatched and keep being counted.
"""

#: Place-scoped: every development within the named area is bound.
_AREA = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
         "is_precinct_specific": True}

#: A general built-form control, binding any development in the LGA.
_GENERAL = {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"]}

NORTHERN_BEACHES_CONFIG: dict = {
    "parts": {
        # Matched before the letter-only fallback, so this wins over "E".
        # Part E11 Flood Prone Land: a SITE CONDITION, not a development type —
        # it binds whatever is proposed on land the flood maps cover.
        "E11": {"applicable_zones": ["ALL"], "applicable_dev_types": ["ALL"],
                "site_conditions": ["flood"]},

        # Part A Introduction and administration: objectives, interpretation,
        # how the Parts relate. Binds every application by construction.
        "A": _GENERAL,

        # Parts C, D and E — "a series of built form controls, including
        # setbacks and landscaped open space". General, so ALL is a decision.
        "C": _GENERAL,
        "D": _GENERAL,
        "E": _GENERAL,

        # Part F — "development and activities in certain zones and sensitive
        # areas e.g. local and neighbourhood centres". BOTH KEYS OMITTED: the
        # plan names "certain zones" without listing them, and the sections
        # underneath differ (F1 Local and Neighbourhood Centres is a centre
        # scope; others are sensitive-area scopes). Declaring ALL would assert a
        # universality the plan explicitly qualifies, and naming a zone list
        # would be inventing one. `layer` keeps the entry truthy — an entry
        # declaring neither key is an empty dict, and `_resolve` opens with
        # `if not entry: return ['ALL'], 'no_config'`.
        "F": {"layer": "generic"},

        # Part G — special areas, and it PREVAILS over C, D and E where they
        # conflict. G1..G10 all reach this through the progressive strip.
        "G": _AREA,

        # Part H — appendices (carparking, vegetation). Referenced by the
        # controls above rather than scoped away from them.
        "H": _GENERAL,
    },
}
