"""Inner West Local Environmental Plan 2022: who each CLAUSE applies to, in the Plan's own words (DQ-140).

prior-art-checked: reuse not viable because the existing scope configs are per DCP chapter; an LEP
states its reach per clause. Read by enrichment/extractors/applicability_tagger.py
(_get_inner_west_lep_config) using each row's section_header (its verbatim clause heading).

Each entry was read from the in-force text on legislation.nsw.gov.au (2026-10-10) and every quote in
scope_evidence was checked to occur verbatim in that text before this file was written.
  applicable_zones / applicable_dev_types = ['ALL']  -> the clause states no limit (quote: the clause,
      or cl 1.3 'This Plan applies to the land identified on the Land Application Map.')
  a list                                              -> the clause NAMES those zones / covers exactly
      those development types
  scope_declined                                      -> read, but the reach is a site, map area or
      development type the stored labels cannot express; served to all, recorded as a decision
"""
import re


def clause_key(section_header):
    """'6.34 Development of ...' -> '6.34'; 'Schedule 5 ...' -> 'Schedule 5';
    'Land Use Table Zone R1 ...' -> 'LUT:R1'."""
    s = (section_header or '').strip()
    m = re.match(r'^Land Use Table Zone ([A-Z]{1,3}\d?)\b', s)
    if m:
        return 'LUT:' + m.group(1)
    m = re.match(r'^(Schedule \d+[A-Z]?|\d+\.\d+[A-Z]{0,2})\b', s)
    return m.group(1) if m else None


INNER_WEST_LEP_CLAUSES = {
    "1.7": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "1.8": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "1.8A": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "1.9A": {
        "scope_evidence": {
            "applicable_zones": "development on land in any zone",
            "applicable_dev_types": "any agreement, covenant or other similar instrument that restricts the carrying out of that development does not apply"
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "2.1": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "2.3": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "2.4": {
        "scope_evidence": {
            "applicable_zones": "Development may be carried out on unzoned land only with development consent.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "unzoned land has no zone code",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "2.5": {
        "scope_evidence": {
            "applicable_zones": "Development on particular land that is described or referred to in Schedule 1",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "2.6": {
        "scope_evidence": {
            "applicable_zones": "Land to which this Plan applies may be subdivided, but only with development consent.",
            "applicable_dev_types": "Land to which this Plan applies may be subdivided, but only with development consent."
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "2.8": {
        "scope_evidence": {
            "applicable_zones": "development consent may be granted for development on land in any zone for a temporary use",
            "applicable_dev_types": "development consent may be granted for development on land in any zone for a temporary use"
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "2.9": {
        "scope_evidence": {
            "applicable_zones": "Canal estate development is prohibited on land to which this Plan applies.",
            "applicable_dev_types": "Canal estate development is prohibited on land to which this Plan applies."
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "pack text also contains the Land Use Table, not read here",
        "applicable_zones": [
            "ALL"
        ]
    },
    "3.1": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "Development specified in Schedule 2 that meets the standards for the development contained in that Schedule and that complies with the requirements of this Part is exempt development."
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "3.2": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "Development specified in Part 1 of Schedule 3 that is carried out in compliance with"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "3.3": {
        "scope_evidence": {
            "applicable_zones": "Exempt or complying development must not be carried out on any environmentally sensitive area for exempt or complying development.",
            "applicable_dev_types": "Exempt or complying development must not be carried out on any environmentally sensitive area for exempt or complying development."
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "4.1": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to a subdivision of any land shown on the Lot Size Map",
            "applicable_dev_types": "This clause applies to a subdivision of any land shown on the Lot Size Map"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "4.1A": {
        "scope_evidence": {
            "applicable_zones": "land identified as “Area 1” on the Lot Size Map",
            "applicable_dev_types": "The minimum lot size for subdivision of land identified as “Area 1” on the Lot Size Map"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "4.3": {
        "scope_evidence": {
            "applicable_zones": "The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map.",
            "applicable_dev_types": "The height of a building on any land is not to exceed the maximum height shown for the land on the Height of Buildings Map."
        },
        "scope_declined": [],
        "notes": "(2A)/(2B) apply to Areas 1-3 on the Height of Buildings Map",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "4.3A": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to development for the following purposes on land identified as “Area 1” or “Area 3” on the Height of Buildings Map.",
            "applicable_dev_types": "the building will be used for the purposes of a residential flat building or shop top housing"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "residential_flat_building",
            "shop_top_housing"
        ]
    },
    "4.3B": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Area 1” or “Area 3” on the Height of Buildings Map.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "4.3C": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to development for the purposes of residential accommodation on land in Zone R1 General Residential and identified as “Area 1” on the Key Sites Map.",
            "applicable_dev_types": "This clause applies to development for the purposes of residential accommodation on land in Zone R1 General Residential"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "residential accommodation is not a stored label; zone R1 AND Key Sites Area 1"
    },
    "4.4": {
        "scope_evidence": {
            "applicable_zones": "The maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown for the land on the Floor Space Ratio Map.",
            "applicable_dev_types": "The maximum floor space ratio for a building on any land is not to exceed the floor space ratio shown for the land on the Floor Space Ratio Map."
        },
        "scope_declined": [],
        "notes": "(2A)-(2E) carry area/type limits",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "4.4A": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Area 1” on the Floor Space Ratio Map.",
            "applicable_dev_types": "is mixed use development that includes residential accommodation"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "also Zone E1 per objective"
    },
    "4.5": {
        "scope_evidence": {
            "applicable_zones": "In determining the site area of proposed development for the purpose of applying a floor space ratio, the site area is taken to be",
            "applicable_dev_types": "In determining the site area of proposed development for the purpose of applying a floor space ratio, the site area is taken to be"
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "4.6": {
        "scope_evidence": {
            "applicable_zones": "Development consent may, subject to this clause, be granted for development even though the development would contravene a development standard",
            "applicable_dev_types": "Development consent may, subject to this clause, be granted for development even though the development would contravene a development standard"
        },
        "scope_declined": [],
        "notes": "(6) lists non-Inner-West zones only",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "5.1": {
        "scope_evidence": {
            "applicable_zones": "in relation to the land shown on the Land Reservation Acquisition Map",
            "applicable_dev_types": "Development on land acquired by an authority of the State under the owner-initiated acquisition provisions may, before it is used for the purpose for which it is reserved, be carried out, with development consent, for any purpose."
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "land acquisition clause, not a development rule",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "5.10": {
        "scope_evidence": {
            "applicable_zones": "a building, work, relic or tree within a heritage conservation area",
            "applicable_dev_types": "demolishing or moving any of the following or altering the exterior of any of the following"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "heritage items / conservation areas"
    },
    "5.12": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "any development, by or on behalf of a public authority"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "5.19": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "development for the purpose of pond-based aquaculture or tank-based aquaculture"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "zone lists inside are conditions, not scope",
        "applicable_zones": [
            "ALL"
        ]
    },
    "5.1A": {
        "scope_evidence": {
            "applicable_zones": "identified on the Land Reservation Acquisition Map",
            "applicable_dev_types": "other than development for a purpose specified opposite the land in the table to this clause"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "5.2": {
        "scope_evidence": {
            "applicable_zones": "The public land described in Part 1 or Part 2 of Schedule 4 is classified, or reclassified, as operational land",
            "applicable_dev_types": "to enable the Council to classify or reclassify public land"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "not a development clause; land classification"
    },
    "5.20": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "development in relation to licensed premises"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "5.21": {
        "scope_evidence": {
            "applicable_zones": "development on land the consent authority considers to be within the flood planning area",
            "applicable_dev_types": "Development consent must not be granted to development on land the consent authority considers to be within the flood planning area"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "5.22": {
        "scope_evidence": {
            "applicable_zones": "land between the flood planning area and the probable maximum flood",
            "applicable_dev_types": "Development consent must not be granted to development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "5.3": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to so much of any land that is within the relevant distance of a boundary between any 2 zones.",
            "applicable_dev_types": "development consent may be granted to development of land to which this clause applies for any purpose that may be carried out in the adjoining zone"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "5.4": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "If development for the purposes of a home business is permitted under this Plan"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "subclauses cover B&B, home business, kiosk etc; only (9) names a stored type (secondary_dwelling)",
        "applicable_zones": [
            "ALL"
        ]
    },
    "5.7": {
        "scope_evidence": {
            "applicable_zones": "any land below the mean high water mark of any body of water subject to tidal influence",
            "applicable_dev_types": "Development consent is required to carry out development on any land below the mean high water mark"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "5.8": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "converting a fire alarm system from connection with the alarm monitoring system of Fire and Rescue NSW"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "5.9": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land in the following zones—",
            "applicable_dev_types": "dwelling house or secondary dwelling that has been damaged or destroyed by a natural disaster"
        },
        "scope_declined": [],
        "notes": "",
        "applicable_zones": [
            "R1",
            "R2",
            "R3"
        ],
        "applicable_dev_types": [
            "dwelling_house",
            "secondary_dwelling"
        ]
    },
    "6.1": {
        "scope_evidence": {
            "applicable_zones": "on land shown on the Acid Sulfate Soils Map as being of the class specified",
            "applicable_dev_types": "the carrying out of works"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "6.10": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "Development consent must not be granted for the purposes of restricted premises or sex services premises"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "also restricted premises, which has no vocab label | 'restricted premises' has no stored label, so a list would be partial",
        "applicable_zones": [
            "ALL"
        ]
    },
    "6.11": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land in the following zones— (a) Zone R1 General Residential, (b) Zone R2 Low Density Residential, (c) Zone R3 Medium Density Residential, (d) Zone R4 High Density Residential.",  # noqa: zone-codes - VERBATIM LEP sentence quoted as scope_evidence
            "applicable_dev_types": "Development for the purposes of business premises, office premises, restaurants or cafes, shops, small bars or take away food and drink premises"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "mix of vocab-absent types",
        "applicable_zones": [
            "R1",
            "R2",
            "R3",
            "R4"
        ]
    },
    "6.12": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to a building lawfully constructed for a purpose other than residential accommodation in the following zones— (a) Zone R1 General Residential, (b) Zone R2 Low Density Residential, (c) Zone R3 Medium Density Residential, (d) Zone R4 High Density Residential.",  # noqa: zone-codes - VERBATIM LEP sentence quoted as scope_evidence
            "applicable_dev_types": "Development consent must not be granted to a change of use to residential accommodation"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "change of use to residential accommodation / multi dwelling housing / RFB",
        "applicable_zones": [
            "R1",
            "R2",
            "R3",
            "R4"
        ]
    },
    "6.13": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land in the following zones— (a) Zone E1 Local Centre, (b) Zone E2 Commercial Centre, (c) Zone MU1 Mixed Use.",  # noqa: zone-codes - VERBATIM LEP sentence quoted as scope_evidence
            "applicable_dev_types": "development for the purposes of residential accommodation"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "E1",
            "E2",
            "MU1"
        ]
    },
    "6.14": {
        "scope_evidence": {
            "applicable_zones": "land identified as “Area 1” on the Key Sites Map",
            "applicable_dev_types": "provision of a mix of dwelling types in residential flat buildings and mixed use development that includes shop top housing"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "residential_flat_building",
            "shop_top_housing"
        ]
    },
    "6.15": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Area 1” on the Key Sites Map if",
            "applicable_dev_types": "Development consent must not be granted to development to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.16": {
        "scope_evidence": {
            "applicable_zones": "Lot 1, DP 632522, 141 Allen Street, Leichhardt, identified as “Area 3” on the Key Sites Map,",
            "applicable_dev_types": "Development consent must not be granted to development on land identified as"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.17": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to the following land at 168 Norton Street, Leichhardt, identified as “Area 5” on the Key Sites Map",
            "applicable_dev_types": "development for the purposes of seniors housing involving only a group of self-contained dwellings"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "6.18": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to Lot 1, DP 432612, 101–103 Lilyfield Road, Lilyfield, identified as “Area 6” on the Key Sites Map.",
            "applicable_dev_types": "development for the purposes of restaurants or cafes or takeaway food and drink premises"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "sub-types of food and drink premises, not the exact label"
    },
    "6.19": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to Lots 21, 22, 24 and 25, Section 1, DP 328 and Lots A and B, DP 377714, 17 Marion Street, Leichhardt, identified as “Area 7” on the Key Sites Map.",
            "applicable_dev_types": "development for the purposes of seniors housing"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "6.2": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "Development consent is required for earthworks"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "6.20": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “C54” on the Heritage Map.",
            "applicable_dev_types": "development for the purposes of dwelling houses"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "dwelling_house"
        ]
    },
    "6.21": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land in Zone E3 Productivity Support and Zone E4 General Industrial and identified as “Area 19” on the Key Sites Map.",  # noqa: zone-codes - VERBATIM LEP sentence quoted as scope_evidence
            "applicable_dev_types": "development for the purposes of business premises or office premises"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "zones E3,E4 AND Area 19 only; zone list alone would over-state"  # noqa: zone-codes - VERBATIM LEP sentence quoted as scope_evidence
    },
    "6.22": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land in Zone E3 Productivity Support and identified as “Area 20” on the Key Sites Map.",
            "applicable_dev_types": "development for the purposes of dwellings or residential flat buildings"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "zone E3 AND Area 20 only"
    },
    "6.23": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Area 8”, “Area 9”, “Area 10”, “Area 11” and “Area 12” on the Key Sites Map.",
            "applicable_dev_types": "development for the purposes of residential accommodation"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "6.24": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land at Lot 11, DP 499846, 1–5 Chester Street, Annandale, identified as “Area 2” on the Key Sites Map.",
            "applicable_dev_types": "Development consent must not be granted to development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.25": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to Lot 2, DP 1015843, 469–483 Balmain Road, Lilyfield, identified as “Area 15” on the Key Sites Map.",
            "applicable_dev_types": "mixed use development on land to which this clause applies that includes a residential flat building"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "(3) limited to mixed use incl RFB but (6) applies to all development | dev_types unsure on reading, declined"
    },
    "6.26": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to Lot 1, DP 1208130 and Lot 10, DP 1004198, 287–309 Trafalgar Street, Petersham, identified as “46” on the Additional Permitted Use Map.",
            "applicable_dev_types": "Development for the purposes of registered clubs"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    },
    "6.27": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to Lot 100, DP 1283113, 50–52 Edith Street, 67 and 73–83 Mary Street and 43 Roberts Street, St Peters, identified as “Area 16” on the Key Sites Map",
            "applicable_dev_types": "Development consent must not be granted to development on the subject land"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.3": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to all land in residential, employment and mixed use zones.",
            "applicable_dev_types": "Development consent must not be granted to development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "residential=R1-R4, employment=E1-E4, mixed use=MU1 per group words | zone categories ('residential, employment and mixed use zones') are not named zones",  # noqa: zone-codes - VERBATIM LEP sentence quoted as scope_evidence
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.30": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to the following land in Lilyfield, identified as “Area 17” on the Key Sites Map",
            "applicable_dev_types": "Development consent must not be granted to development that will result in a dwelling on the ground floor"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "(2) height/FSR apply to any building",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.31": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Area 13” on the Key Sites Map.",
            "applicable_dev_types": "Development consent must not be granted for development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.33": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to development on land identified as “Stage 1 Bays West Precinct” on the Land Application Map",
            "applicable_dev_types": "the erection of a new building with a gross floor area of more than 200m"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "limited by floor area works, not use type",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.34": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Area L” on the Key Sites Map.",
            "applicable_dev_types": "Development consent must not be granted for development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.4": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Biodiversity” on the Natural Resource—Biodiversity Map.",
            "applicable_dev_types": "Development consent must not be granted to development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.5": {
        "scope_evidence": {
            "applicable_zones": "This clause applies to land identified as “Foreshore Area” on the Foreshore Building Line Map.",
            "applicable_dev_types": "Development consent must not be granted for development on land to which this clause applies"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "purposes in (3) are exceptions, not an application limit",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.6": {
        "scope_evidence": {
            "applicable_zones": "development in the foreshore area",
            "applicable_dev_types": "Development consent must not be granted for development in the foreshore area"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "6.7": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "development that is a controlled activity within the meaning of the Airports Act 1996"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "6.8": {
        "scope_evidence": {
            "applicable_zones": "in an ANEF contour of 20 or greater",
            "applicable_dev_types": "the erection of a new building"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "limited by works/change of use to non-vocab uses"
    },
    "6.9": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "This clause applies to development involving the construction of a new building, or external alterations to an existing building, that will result in a building that is equal to, or greater than, 14m in height."
        },
        "scope_declined": [],
        "notes": "limited by building work and 14m height, not by use type",
        "applicable_zones": [
            "ALL"
        ],
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "7.2": {
        "scope_evidence": {
            "applicable_zones": "The maximum building height for a building on Dulwich Grove land",
            "applicable_dev_types": "Development consent must not be granted to development that results in a building on Dulwich Grove land"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "7.3": {
        "scope_evidence": {
            "applicable_zones": "The maximum floor space ratio for a building on Dulwich Grove land",
            "applicable_dev_types": "Development consent must not be granted to development that results in a building on Block A"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "7.4": {
        "scope_evidence": {
            "applicable_zones": "permitted with development consent on Dulwich Grove land",
            "applicable_dev_types": "Development for the following purposes is permitted with development consent on Dulwich Grove land— (a) residential flat buildings, (b) retail premises, (c) shop top housing."
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "residential_flat_building",
            "retail_premises",
            "shop_top_housing"
        ]
    },
    "7.5": {
        "scope_evidence": {
            "applicable_zones": "development on Dulwich Grove land",
            "applicable_dev_types": "Development consent must not be granted to development on Dulwich Grove land"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "8.2": {
        "scope_evidence": {
            "applicable_zones": "This part applies to the following land in Camperdown, identified as “Area M” on the Key Sites Map",
            "applicable_dev_types": "a building on the land may have a height of up to 80m"
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "land per cl 8.1 (iw_paras); height/FSR bonus not use-limited",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "LUT:E1": {
        "applicable_zones": [
            "E1"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone E1 Local Centre",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:E2": {
        "applicable_zones": [
            "E2"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone E2 Commercial Centre",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:E3": {
        "applicable_zones": [
            "E3"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone E3 Productivity Support",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:MU1": {
        "applicable_zones": [
            "MU1"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone MU1 Mixed Use",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:R1": {
        "applicable_zones": [
            "R1"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone R1 General Residential",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:R4": {
        "applicable_zones": [
            "R4"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone R4 High Density Residential",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:SP1": {
        "applicable_zones": [
            "SP1"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone SP1 Special Activities",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "LUT:SP2": {
        "applicable_zones": [
            "SP2"
        ],
        "applicable_dev_types": [
            "ALL"
        ],
        "scope_evidence": {
            "applicable_zones": "Zone SP2 Infrastructure",
            "applicable_dev_types": "The Land Use Table at the end of this Part specifies for each zone"
        },
        "scope_declined": [],
        "notes": "Land Use Table rows for one zone"
    },
    "Schedule 1": {
        "scope_evidence": {
            "applicable_zones": "Schedule 1 sets out additional permitted uses for particular land.",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": " | items permit specific uses on specific sites"
    },
    "Schedule 2": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "Schedule 2 sets out exempt development"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "Schedule 3": {
        "scope_evidence": {
            "applicable_zones": "This Plan applies to the land identified on the Land Application Map.",
            "applicable_dev_types": "Schedule 3 sets out complying development"
        },
        "scope_declined": [
            "applicable_dev_types"
        ],
        "notes": "",
        "applicable_zones": [
            "ALL"
        ]
    },
    "Schedule 4": {
        "scope_evidence": {
            "applicable_zones": "Part 3 Land classified, or reclassified, as community land",
            "applicable_dev_types": "(Clause 5.2)"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": "all parts Nil; land classification, no development rule | dev_types unsure on reading, declined"
    },
    "Schedule 5": {
        "scope_evidence": {
            "applicable_zones": "Part 1 Heritage items",
            "applicable_dev_types": "This Plan applies to the land identified on the Land Application Map."
        },
        "scope_declined": [
            "applicable_zones"
        ],
        "notes": "site-specific heritage items; listing applies via cl 5.10",
        "applicable_dev_types": [
            "ALL"
        ]
    },
    "Schedule 6": {
        "scope_evidence": {
            "applicable_zones": "vacant Crown land",
            "applicable_dev_types": "Part 1 Pond-based and tank-based aquaculture"
        },
        "scope_declined": [
            "applicable_zones",
            "applicable_dev_types"
        ],
        "notes": ""
    }
}
