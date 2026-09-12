"""Real contents-page text from real DCP chapters, plus the confusable negatives.

Every positive here is text pdfplumber actually returned, sampled 2026-09-12 from
the R2 copy of the chapter named in the label. They are trimmed, not paraphrased:
a fixture rewritten into what the parser expects is a test that cannot fail.

The three negatives are the load-bearing half. A contents parser that is widened
until everything parses produces a fabricated contents list, and a fabricated
contents list produces a fabricated "sections missing" finding -- which is worse
than the fail-open check it replaces, because it looks like evidence.
"""

# ── positives: six shapes that must READ ─────────────────────────────────────

# waverley/waverley-dcp-2022 -- code, title, page number after ONE space.
WAVERLEY = """A1 Statutory Information 1
B1 Waste 4
B15 Public Domain 132
B16 Inter-War Buildings 143
C1 Low Density Residential Development 184
E7 Edina Estate 391
F1 Shared Accommodation 454
F5 Horticulture 467"""

# leichhardt -- dot leaders and a trailing page number.
LEICHHARDT = """Contents
1.0 INTRODUCTION 3
1.1 Name of the Plan and Commencement .......................................... 3
1.2 Land to Which this Plan Applies ........................................... 4
1.3 Relationship with Other Plans ............................................. 4
2.0 PROVISIONS 6
2.1 Site Layout and Built Form................................................. 6"""

# ashfield/chapter-a-miscellaneous -- no page numbers at all.
ASHFIELD = """General Contents
1 Site and Context Analysis
2 Good Design
3 Flood Hazard
4 Solar Access and Overshadowing
5 Landscaping
6 Safety by Design
7 Access and Mobility"""

# ku_ring_gai/section-b-part-14a-st-ives-local-centre, page 1.
# The code carries a TRAILING letter (14A.1). This single shape is 34 of the 113
# chapters the previous sweep could not read.
KU_RING_GAI = """p 14-39
Ku-ring-gai Development Control Plan
14A St Ives Local Centre
14A.1 St Ives Local Centre Context
14A.2 Public Domain and Pedestrian Access
14A.3 Proposed Community Infrastructure
14A.4 Setbacks
14A.5 Built Form
14A.6 Building Entries, Car Parking and Service Access
14A.7 Precinct S1: St Ives Shopping Village"""

# canterbury_bankstown/chapter-3-3-waste-management, page 3.
# A PREFIX WORD before the code, an en dash, and leaders that run off the line
# with NO page number. 39 of the 113.
CANTERBURY_BANKSTOWN = """CONTENTS
Section 1 - Introduction ...........................................................
Section 2 - Standard services specifications for residential development ..........
Section 3 - Residential development ...............................................
Section 4 - Commercial development ................................................
Section 5 - Industrial development ................................................
Section 6 - Specific uses .........................................................
Page 3 DCP 2023-Chapter 3.3 (Amended August 2025)"""

# leichhardt/part-g-s13-site-specific, page 2 -- G13.1 alongside "4.1." codes
# that carry a trailing dot, and leaders with no page number.
LEICHHARDT_G13 = """Site Specific Controls
Contents
G13.1 Relationship to other plans ..................................................
G13.2 Application ..................................................................
G13.3 Context ......................................................................
4.1. Desired Future Character ......................................................
4.2. Land use ......................................................................
4.3. Lot amalgamation .............................................................."""

# ── reason-coded residue: real documents, not parser defects ─────────────────

# ashfield/chapter-b-public-domain, page 3. A genuine contents page that lists
# titles and page numbers and NO CODES. A code-vs-code comparison cannot run on
# it, and pretending otherwise would report every section as missing.
ASHFIELD_TITLES_ONLY = """Table of Contents
Ref. Section Page
B Public Domain
Active Street Frontages 4
Awnings to Buildings Over Public Land 6
Street Trees 6
Wind Effects of Buildings 7
Reflectivity of Buildings 7
Public Domain Plan 8
External Lighting 9"""

# leichhardt/cover -- one page, no contents page exists. Nothing is wrong here.
COVER = """Leichhardt Development Control Plan 2013
(Amendment No. 18)"""

# marrickville/cover -- a scanned page with no text layer at all.
SCANNED = ""

# ── confusable negatives: must NOT read as a contents page ───────────────────

# Real body prose. "1.1 Name of the Plan and Commencement" is a real contents
# entry AND a real body heading, which is why the density gate exists.
BODY_PROSE = """1.0 Introduction
1.1 Name of the Plan and Commencement
This plan is called the George and Upward Streets, Leichhardt Development Control
It has been prepared pursuant to the provisions of Section 74C of the Environmental
Infrastructure and comes into effect from 11 March 2014.
1.2 Land to Which this Plan Applies
This DCP applies to the land shown in Figure 1 being:
(a) Development must not exceed the height shown on the Height of Buildings Map.
(b) The setback must be a minimum of 3 metres from the front boundary."""

# A page of numbered CONTROLS, one per line. Dense in codes, no contents heading.
# This is the shape the widened regex is most likely to swallow, and the reason
# entry_strength() rejects sentences.
NUMBERED_CONTROLS = """2.1 The design of development must respond to the setting and setbacks.
2.2 Development must maintain significant views to the place of heritage.
2.3 Adequate setbacks from the site must be retained to preserve its setting.
2.4 Original landscape features associated with the place must be retained.
2.5 Materials and finishes must avoid strong contrast with nearby buildings.
2.6 The height of any new building must not exceed the prevailing streetscape."""

# Controls that WRAP, which is what they really do. The continuation lines carry
# no code, so the density gate has to carry this one rather than entry_strength.
WRAPPED_CONTROLS = """Development controls
1.1 The design of development must:
(a) respond to the setting, setbacks, form, scale and style of nearby places
of heritage significance;
(b) maintain significant views to and from the place of heritage significance;
(c) ensure adequate setbacks from the site of the place of heritage significance
to retain its visual setting;
1.2 Materials and finishes must be selected to avoid strong contrast."""


# (label, page_text, expected_status)
CASES = [
    ("waverley             code + page, single space", WAVERLEY, "READ"),
    ("leichhardt           dot leaders + page number", LEICHHARDT, "READ"),
    ("ashfield             no page numbers", ASHFIELD, "READ"),
    ("ku_ring_gai          trailing-letter codes (34 ch)", KU_RING_GAI, "READ"),
    ("canterbury_bankstown prefix word, no page no (39 ch)",
     CANTERBURY_BANKSTOWN, "READ"),
    ("leichhardt G13       G13.1 and '4.1.' mixed", LEICHHARDT_G13, "READ"),
    ("ashfield chapter-b   contents listing NO codes",
     ASHFIELD_TITLES_ONLY, "TITLES_ONLY"),
    ("cover page           no contents page exists", COVER, "NO_CONTENTS"),
    ("scanned page         no text layer", SCANNED, "NO_CONTENTS"),
    ("BODY PROSE           confusable negative", BODY_PROSE, "NO_CONTENTS"),
    ("NUMBERED CONTROLS    confusable negative", NUMBERED_CONTROLS, "NO_CONTENTS"),
    ("WRAPPED CONTROLS     confusable negative", WRAPPED_CONTROLS, "NO_CONTENTS"),
]
