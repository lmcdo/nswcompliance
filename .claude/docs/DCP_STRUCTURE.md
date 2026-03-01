# DCP Structure Documentation

This documents the ACTUAL structure of the 3 DCPs in the database.

---

## LEICHHARDT DCP 2013

### Source Documents

| Document | Provisions | Pages | Description |
|----------|------------|-------|-------------|
| Part A Introduction | 128 | p2-9 | Admin/intro (not controls) |
| Part C Section 1 | 1,554 | p1-109 | **General Development Controls** |
| Part C Section 2 | 173 | p19-226 | Neighbourhood-specific controls |
| Part D Energy | 270 | p2-15 | BASIX/energy requirements |
| Part E Water | 357 | p2-20 | Stormwater/water management |
| Part F Food | 21 | p3-6 | Food premises |
| Part G Site-Specific | 486 | p9-149 | Site-specific controls |

### Part C Section 1 - Control Markers (C1-C55)

**48 unique markers found.** Each marker = specific topic.

| Marker | Topic | Provisions | Marker | Topic | Provisions |
|--------|-------|------------|--------|-------|------------|
| C1 | site_analysis | 256 | C29 | privacy | 6 |
| C2 | heritage | 85 | C30 | solar | 3 |
| C3 | parking | 57 | C31 | views | 6 |
| C4 | building_form | 34 | C32 | setbacks | 6 |
| C5 | roofing | 58 | C33 | height | 3 |
| C6 | landscaping | 50 | C34 | building_form | 6 |
| C7 | fencing | 29 | C35 | building_form | 3 |
| C8 | setbacks | 26 | C36 | safety | 6 |
| C9 | trees | 23 | C37 | heritage | 6 |
| C10 | trees | 23 | C38 | signage | 3 |
| C11 | trees | 11 | C43-C55 | vehicle_access | 3 each |
| C12 | flooding | 20 | | | |
| C13 | contamination | 17 | | | |
| C14-C17 | parking | 14-22 each | | | |
| C18-C21 | bicycle_parking | 4-9 each | | | |
| C22 | access | 9 | | | |
| C23 | landscaping | 9 | | | |
| C24-C28 | building_design | 3-9 each | | | |

### Part C Section 2 - Neighbourhood Controls

22 distinct neighbourhoods, each with own document:

- C2.2.1.1 Young Street
- C2.2.1.2 Annandale Street
- C2.2.1.3 Johnston Street
- C2.2.1.5 Trafalgar Street
- C2.2.1.6 Nelson Street
- C2.2.1.8 Camperdown
- C2.2.2.1 Darling Street
- C2.2.2.3 Gladstone Park
- C2.2.3.1 Excelsior Estate
- C2.2.3.2 West Leichhardt
- C2.2.3.3 Piperston
- C2.2.3.4 Helsarmel
- C2.2.3.5 Leichhardt Commercial
- C2.2.4.1 Catherine Street
- C2.2.4.2 Nanny Goat Hill
- C2.2.4.3 Leichhardt Park
- C2.2.4.4 Iron Cove Parklands
- C2.2.5.1 The Valley (Rozelle)
- C2.2.5.2 Easton Park
- C2.2.5.3 Callan Park
- C2.2.5.4 Iron Cove
- C2.2.5.5 Rozelle Commercial
- C2.2.5.6 Robert Street Industrial

---

## ASHFIELD DCP 2016

### Source Documents

| Document | Provisions | Pages | Description |
|----------|------------|-------|-------------|
| Chapter A Miscellaneous | 151 | p5-125 | General provisions |
| Chapter B Public Domain | 4 | p4-8 | Public domain |
| Chapter C Sustainability | 174 | p4-86 | Environmental sustainability |
| Chapter D Precinct Guidelines | 134 | p4-197 | Precinct-specific |
| Chapter E1 Heritage | 905 | p6-387 | **Heritage controls (bulk of DCP)** |
| Chapter F Development Category | 50 | p5-85 | Use-specific controls |

### Markers (36 unique)

Ashfield uses different marker systems:
- **C1-C10**: General controls (22+2+3+4+4+4+1+1+1+2 = 44 provisions)
- **DS#.#**: Design standards (DS1.2, DS12.4, etc.)
- **O1**: Objectives (16 provisions)
- **PC#**: Precinct controls

### Chapter E1 Heritage - The Big Problem

**905 provisions** in heritage chapter, but only **51 have markers** (5.6%).

The heritage chapter contains:
- Historical context paragraphs
- HCA descriptions
- Contributory item lists
- Actual controls mixed in

---

## MARRICKVILLE DCP 2011

### Source Documents

| Part | Provisions | Pages | Description |
|------|------------|-------|-------------|
| Part 1 Statutory | 14 | p5-10 | Admin |
| Part 2 General | 146 | p1-16 | **General provisions** |
| Part 3 Subdivision | 9 | p1-12 | Subdivision controls |
| Part 4.1 Low Density | 28 | p1-48 | Low density residential |
| Part 4.2 Multi-Dwelling | 5 | p1-13 | Multi-dwelling |
| Part 5 Commercial | 45 | p1-42 | Commercial/mixed use |
| Part 6 Industrial | 36 | p1-29 | Industrial |
| Part 7 Specific Uses | varies | varies | Childcare, sex industry |
| Part 8 Heritage | 210 | p2-295 | Heritage |
| Part 9 Precincts | 283 | p1-44 | **47 precincts** |

### Part 2 Section Structure

Document IDs contain section numbers:

| Section | Topic | Document Pattern |
|---------|-------|------------------|
| 2.1 | urban_design | `2__1__Urban__Design` |
| 2.3 | site_analysis | `2__3__Site__Context` |
| 2.5 | access | `2__5__Equity__of__Access` |
| 2.6 | privacy | `2__6__Acoustic__and__Visual` |
| 2.7 | solar | `2__7__Solar__Access` |
| 2.8 | social_impact | `2__8__Social__Impact` |
| 2.9 | safety | `2__9__Community__Safety` |
| 2.10 | parking | `2__10__Parking` |
| 2.11 | fencing | `2__11__Fencing` |
| 2.12 | signage | `2__12__Signs` |
| 2.13 | biodiversity | `2__13__Biodiversity` |
| 2.14 | environmental | `2__14__Unique__Environmental` |
| 2.16 | energy | `2__16__Energy__Efficiency` |
| 2.17 | wsud | `2__17__Water__Sensitive` |
| 2.18 | landscaping | `2__18__Landscaping` |
| 2.25 | stormwater | `2__25__Stormwater` |

### Part 9 Precincts (47 total)

Each precinct has own document:
- 9.1 Lewisham North
- 9.2 Petersham North
- 9.3 Stanmore North
- 9.4 Newtown North & Camperdown
- 9.5 Lewisham South
- 9.6 Petersham South
- 9.7 Stanmore South
- 9.8 Enmore North & Newtown Central
- 9.9 Newington
- 9.10 Dulwich Hill North
- 9.11 Hoskins Park
- 9.12 Marrickville Park & Morton Park
- 9.13 Henson Park
- 9.14 Camdenville
- 9.15 Enmore Park
- 9.16 Abergeldie Estate
- 9.17 New Canterbury Road West
- 9.18 Dulwich Hill Station North
- 9.19 Marrickville Road Central
- 9.20 Marrickville Town Centre North
- 9.21 Ness Park
- 9.22 Dulwich Hill Station South
- 9.23 Marrickville Station West
- 9.24 Marrickville Town Centre South
- 9.25 St Peters Triangle
- 9.26 Barwon Park
- 9.27 Barwon Park South
- 9.28 Cooks River West
- 9.29 South Western Marrickville
- 9.30 The Warren
- 9.31 Unwins Bridge Road
- 9.32 Cooks River East
- 9.33 Princes Highway
- 9.34 Tempe Reserve
- 9.35 Parramatta Road
- 9.36 Petersham Commercial
- 9.37 King Street & Enmore Road Commercial
- 9.38 Dulwich Hill Commercial
- 9.39 Marrickville Metro
- 9.40 Marrickville Town Centre Commercial
- 9.41 Bridge Road
- 9.42 Camperdown North
- 9.43 Sydney Steel
- 9.44 Carrington Road
- 9.45 McGill Street
- 9.46 Tempe Lands
- 9.47 Victoria Road
- 9.48 Mary Robert & Edith Street North

### NO MARKERS IN MARRICKVILLE

Marrickville has **0 markers** in the v2_marker field. Topic must be derived from:
1. Section number in document_id (e.g., `2__10__` = parking)
2. Part number (Part 8 = heritage, Part 9 = precinct)

---

## Topic Derivation Rules

### Leichhardt
1. If v2_marker starts with C#, use marker→topic mapping
2. Part D = energy
3. Part E = water
4. Part F = food_premises
5. Part G = site_specific

### Ashfield
1. Chapter E1 = heritage
2. Chapter F Part # = development type specific
3. Chapter D = precinct

### Marrickville
1. Extract section from document_id (regex: `__2__(\d+)__`)
2. Part 8 = heritage
3. Part 9 = precinct (topic = precinct name)
4. Part 4.1 = low_density_residential
5. Part 4.2 = multi_dwelling
6. Part 5 = commercial
7. Part 6 = industrial
