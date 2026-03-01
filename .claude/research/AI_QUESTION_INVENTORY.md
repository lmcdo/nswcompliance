# AI Assistant Question Inventory

**Last Updated:** 2026-01-19

This document lists ALL questions the AI assistant can answer, organized by category with data source status.

---

## CATEGORY 1: FACTUAL LOOKUPS ✅
*Direct answers from database - no AI interpretation needed*

| # | Question | Data Source | Status |
|---|----------|-------------|--------|
| 1.1 | What is the height limit? | LEP 4.3 + SEPP TOD | ✅ Ready |
| 1.2 | What is the FSR? | LEP 4.4 + SEPP TOD | ✅ Ready |
| 1.3 | What are the front setback requirements? | DCP Part 4 | ✅ Ready |
| 1.4 | What are the side setback requirements? | DCP Part 4 | ✅ Ready |
| 1.5 | What are the rear setback requirements? | DCP Part 4 | ✅ Ready |
| 1.6 | How much parking is required? | SEPP Housing > DCP | ✅ Ready |
| 1.7 | What are the heritage requirements? | DCP Part 8 | ✅ Ready |
| 1.8 | What is the minimum lot size? | LEP 4.1 | ✅ Ready |
| 1.9 | What are the landscaping requirements? | DCP provisions | ✅ Ready |
| 1.10 | What are the privacy requirements? | DCP provisions | ✅ Ready |
| 1.11 | What are the solar access requirements? | ADG / DCP | ✅ Ready |
| 1.12 | What is the building separation requirement? | ADG standards | ✅ Ready |

---

## CATEGORY 2: PERMISSIBILITY ✅
*Is development type X permitted in this zone?*

| # | Question | Data Source | Status |
|---|----------|-------------|--------|
| 2.1 | Is dual occupancy permitted here? | LEP land use table | ✅ Ready |
| 2.2 | Can I build a granny flat / secondary dwelling? | LEP + SEPP Housing | ✅ Ready |
| 2.3 | Is a manor house permitted? | LEP + SEPP Housing | ✅ Ready |
| 2.4 | Can I build boarding houses? | LEP land use table | ✅ Ready |
| 2.5 | Are shop top dwellings allowed? | LEP land use table | ✅ Ready |
| 2.6 | Can I build a multi dwelling housing? | LEP land use table | ✅ Ready |
| 2.7 | Is residential flat building permitted? | LEP land use table | ✅ Ready |
| 2.8 | Can I build a home business? | LEP land use table | ✅ Ready |

---

## CATEGORY 3: HOUSING SEPP ELIGIBILITY ✅
*Do I qualify for Housing SEPP benefits?*

| # | Question | Data Source | Status |
|---|----------|-------------|--------|
| 3.1 | Do I qualify for SEPP Housing? | Zone + lot size + frontage | ✅ Ready |
| 3.2 | Can I use the SEPP parking rates? | Zone + dev type | ✅ Ready |
| 3.3 | What TOD bonuses apply to my site? | Station proximity | ✅ Ready |
| 3.4 | Is my lot big enough for a manor house? | housing_sepp_standards | ✅ Ready |
| 3.5 | Do I meet the frontage requirement? | housing_sepp_standards | ✅ Ready |
| 3.6 | What SEPP height bonus do I get? | TOD precinct lookup | ✅ Ready |
| 3.7 | What SEPP FSR bonus do I get? | TOD precinct lookup | ✅ Ready |

---

## CATEGORY 4: CONSTRAINT CHECKS ✅
*What constraints affect my site?*

| # | Question | Data Source | Status |
|---|----------|-------------|--------|
| 4.1 | Is my property heritage listed? | Heritage flag + provisions | ✅ Ready |
| 4.2 | Am I in a heritage conservation area? | Heritage HCA flag | ✅ Ready |
| 4.3 | Am I in a flood zone? | Flood constraints API | ✅ Ready |
| 4.4 | Is there bushfire risk? | Bushfire API | ✅ Ready |
| 4.5 | What's the acid sulfate soil class? | ASS layer | ✅ Ready |
| 4.6 | Is there mine subsidence risk? | Mine subsidence API | ✅ Ready |
| 4.7 | What environmental constraints apply? | Multiple APIs | ✅ Ready |

---

## CATEGORY 5: DEFINITIONS ✅
*What does term X mean?*

| # | Question | Data Source | Status |
|---|----------|-------------|--------|
| 5.1 | What is a habitable room? | regulatory_definitions | ✅ 465 terms |
| 5.2 | What does articulation mean? | regulatory_definitions | ✅ Extracted |
| 5.3 | Define setback | regulatory_definitions | ✅ Extracted |
| 5.4 | What is a dual occupancy? | regulatory_definitions | ✅ Extracted |
| 5.5 | What is gross floor area? | regulatory_definitions | ✅ Extracted |
| 5.6 | What is site coverage? | regulatory_definitions | ✅ Extracted |
| 5.7 | What is a secondary dwelling? | regulatory_definitions | ✅ Extracted |
| 5.8 | What does "prevailing" mean in setbacks? | regulatory_definitions | ✅ Extracted |

**Note:** 465 terms extracted from:
- Marrickville DCP 2011 (19 terms)
- Leichhardt DCP 2013 (103 terms)
- Ashfield DCP 2016 (28 terms)
- SEPP Housing 2021 (58 terms)
- Inner West LEP 2022 SI (257 terms)

---

## CATEGORY 6: SYNTHESIS (COMPLEX) ✅
*Questions requiring multiple data sources*

| # | Question | Data Sources Combined | Status |
|---|----------|----------------------|--------|
| 6.1 | What's the maximum I can build here? | Height + FSR + setbacks | ✅ Ready |
| 6.2 | Can I build a dual occ on this site? | LEP + lot size + SEPP + constraints | ✅ Ready |
| 6.3 | What applies to my R2 heritage site? | Zone + heritage provisions | ✅ Ready |
| 6.4 | What are ALL the requirements for my property? | SEPP + LEP + DCP combined | ✅ Ready |
| 6.5 | Does SEPP override my DCP parking rate? | SEPP vs DCP hierarchy | ✅ Ready |

---

## CATEGORY 7: PROCEDURAL WORKFLOW ✅
*How do I do X? What's the process?*

| # | Question | Data Source | Status |
|---|----------|-------------|--------|
| 7.1 | Should I use CDC or DA? | procedural_guidance | ✅ Ready |
| 7.2 | What's the CDC process? | procedural_guidance | ✅ Ready |
| 7.3 | What's the DA process? | procedural_guidance | ✅ Ready |
| 7.4 | What documents do I need for CDC? | application_checklists | ✅ 61 items |
| 7.5 | What documents do I need for DA? | application_checklists | ✅ 61 items |
| 7.6 | Do I need a BASIX certificate? | procedural_guidance | ✅ Ready |
| 7.7 | What does a certifier need from me? | procedural_guidance | ✅ Ready |
| 7.8 | How long will CDC approval take? | procedural_guidance | ✅ Ready |
| 7.9 | How long will DA approval take? | procedural_guidance | ✅ Ready |
| 7.10 | What happens after I get CDC approval? | procedural_guidance | ✅ Ready |
| 7.11 | What happens after I get DA approval? | procedural_guidance | ✅ Ready |
| 7.12 | Do I need an architect? | procedural_guidance | ✅ Ready |
| 7.13 | When do I need a structural engineer? | procedural_guidance | ✅ Ready |
| 7.14 | What fees apply for CDC? | procedural_guidance | ✅ Ready |
| 7.15 | What fees apply for DA? | procedural_guidance | ✅ Ready |
| 7.16 | What is a compliance schedule? | procedural_guidance | ✅ Ready |
| 7.17 | What inspections are required during construction? | procedural_guidance | ✅ Ready |
| 7.18 | How do I get an occupation certificate? | procedural_guidance | ✅ Ready |

**Note:** 18 Q&A pairs + 61 checklist items imported from NSW Planning Portal

---

## CATEGORY 8: INTERPRETATION ❌
*Questions requiring professional judgment - REFUSED*

| # | Question | Why Refused |
|---|----------|-------------|
| 8.1 | Will my proposal get approved? | Merit-based assessment |
| 8.2 | Is my design compliant? | Professional judgment required |
| 8.3 | Should I apply for a variation? | Strategy advice |
| 8.4 | How do I negotiate with council? | Professional advice |
| 8.5 | What should my setback be? | Design decision |
| 8.6 | Is this a good investment? | Financial advice |

**Response for refused questions:** "This question requires assessment by a qualified planning professional. The AI assistant provides factual information about requirements but cannot offer compliance opinions or strategy advice."

---

## SUMMARY

| Category | Question Count | Status |
|----------|----------------|--------|
| 1. Factual Lookups | 12 | ✅ All ready |
| 2. Permissibility | 8 | ✅ All ready |
| 3. Housing SEPP | 7 | ✅ All ready |
| 4. Constraint Checks | 7 | ✅ All ready |
| 5. Definitions | 465+ | ✅ All ready |
| 6. Synthesis | 5 | ✅ All ready |
| 7. Procedural | 18 | ✅ All ready |
| 8. Interpretation | 6 | ❌ Refused by design |

**Total Supported Questions:** ~504
**All Categories Available:** Categories 1-7 complete
**Refused by Design:** 6 interpretation questions (require professional judgment)

---

## DATA SOURCES

### Database Tables (Ready)
- `regulatory_provisions` - 47,818 provisions
- `regulatory_definitions` - 465 definitions
- `housing_sepp_standards` - 33 standards
- `sepp_adg_requirements` - 23 requirements
- `procedural_guidance` - 18 Q&A pairs for workflow questions
- `application_checklists` - 61 CDC/DA document requirements

### APIs (Ready)
- `/api/provisions/for-property` - DCP provisions
- `/api/capacity/calculate` - LEP height/FSR
- `/api/sepp/structured-requirements` - SEPP data
- `/api/property` - Property constraints
- `/api/definitions` - Term lookups (465 definitions)
- `/api/procedural` - Workflow guidance (18 Q&A + 61 checklist items)

---

## PROCEDURAL DATA SOURCES

**Extracted from:**
1. NSW Planning Portal - Apply for CDC
2. NSW Planning Portal - Apply for DA
3. NSW Planning Portal - Post Approval
4. BASIX website
5. SEPP Housing 2021 (Codes SEPP reference)

**Files:**
- `scripts/procedural/extracted/pathway_guidance.json` - 18 Q&A pairs
- `scripts/procedural/extracted/application_checklists.json` - 61 checklist items
- `scripts/procedural/import_procedural.py` - Import script
