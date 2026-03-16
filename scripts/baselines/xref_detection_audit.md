# Cross-Reference Detection Audit

**Date:** 2026-03-16T15:58:58.055550
**Branch:** feat/xref-detection-audit
**Gate condition:** Detection precision >= 80%
**Gate result:** PASS (precision = 98%)

## Summary

- False positive rate: 0% (sample n=100)
- Estimated precision: 98%
- False negative rate in sample: 17% (provisions with ref-language but no detections)
- UNKNOWN refs: 868 total, 524 reclassifiable (60%)

## False Positive Examples

## Missed Detections (False Negatives)

**ID 98540** (marrickville) — missed patterns: ['bare_refer_to']
> # 4.2 Multi Dwelling Housing and Residential

7
4.2
Multi
Dwelling
Housing
and
Residential
Flat
Buildings
vi. Minimum side and rear setbacks:
a. A minimum setback of 3 metres must be maintained for on

**ID 88463** (marrickville) — missed patterns: ['bare_refer_to']
> # 4.1.21 Design guidelines – two storey terrace,

PART 4: RESIDENTIAL DEVELOPMENT
4.1.21 Design guidelines – two storey terrace,
single and pair
4.1.21.1 Periods
Victorian (c1840 – c1890) and Federati

**ID 85939** (None) — missed patterns: ['bare_refer_to']
> PART 2:  GENERIC PROVISIONS 
4 
Marrickville Development Control Plan 2011 
assessment of how the proposal complies with the requirements in Table 
1 and the anticipated energy consumption certificati

**ID 92345** (marrickville) — missed patterns: ['bare_refer_to']
> # 8.4 Controls for retail streetscapes in Heritage

PART 8: HERITAGE
8.4 Controls for retail streetscapes in Heritage
Conservation Areas
Figure 1. Examples of buildings within Marrickville’s Retail St

**ID 95437** (city_of_sydney) — missed patterns: ['as_per_clause']
> # 3.3.3 Award for design excellence

Section 3
GGEENNEERRAALL PPRROOVVIISSIIOONNSS
(g) the target benchmarks for ecologically sustainable development.
(1A) In addition to clause (1), buildings seeking

**ID 91800** (woollahra) — missed patterns: ['bare_refer_to']
> # E5.1.5 Relationship to other parts of the DCP

E5 | Waste Management  Part E | General Controls for All Development
E5.1.5 Relationship to other parts of the DCP
This chapter is to be read in conju

**ID 98143** (ku_ring_gai) — missed patterns: ['bare_refer_to']
> # 4c_7 Ancillary Facilities

4C
4C.7 ANCILLARY FACILITIES
Further controls that may apply:
SECTION A SECTION B SECTION C
PART 13 – Tree and Vegetation PART 20 – Heritage and PART 21 - General Site Des

**ID 99054** (woollahra) — missed patterns: ['bare_refer_to']
> # C3.4.1 Precinct A: Entrance Character statement

 Part C | Heritage Conservation Areas C3 | Watsons Bay HCA
C3.4.1 Precinct A: Entrance
Character statement
This precinct stretches from the south en

**ID 98589** (marrickville) — missed patterns: ['bare_refer_to']
> # 8.2.7.3 Specific elements

PART 8: HERITAGE
developed since the first release of land for development from the Annandale and
Petersham Estates in the mid-late 19th century and early 20th century.
ii

**ID 97199** (ku_ring_gai) — missed patterns: ['bare_refer_to']
> # 7c_11 Acoustic Privacy

RESIDENTIAL FLAT
BUILDINGS
7C.11 ACOUSTIC PRIVACY
Further controls that may apply
SECTION C
PART 23.7 - G eneral Acoustic
Privacy
Objectives Controls

Objectives
1 To ensure 

## UNKNOWN Reclassification

Total UNKNOWN: 868

| Category | Count | Action |
|---|---|---|
| likely_epa_act | 72 | → EXTERNAL |
| likely_intra_doc | 26 | → INTRA_DOC_PROBABLE |
| leichhardt_c_marker | 17 | → INTRA_DOC (when council=leichhardt) |
| likely_lep_ref | 39 | → CROSS_DOC |
| schedule_ambiguous | 299 | → needs document context |
| bare_part_ambiguous | 71 | → INTRA_DOC_PROBABLE |
| truly_unknown | 344 | → remains UNKNOWN |

## Proposed Improvements

### 1. [MEDIUM] UNKNOWN classification

**Finding:** 60% of UNKNOWN refs are reclassifiable with better heuristics

**Action:** Add to classifier: (1) EPA Act section numbers >= 60 → EXTERNAL, (2) Leichhardt C-markers → INTRA_DOC, (3) 'the LEP' without year → CROSS_DOC, (4) bare Part/Schedule → INTRA_DOC_PROBABLE

### 2. [MEDIUM] Council-specific patterns

**Finding:** Leichhardt C-markers (C1.9, C2.3) detected but not classified as INTRA_DOC

**Action:** Add INTRA_DOC pattern: r'(?:Part\s+)?C\d+(?:\.\d+)+' when source_council='leichhardt'

## Gate Decision

✅ PASS: Precision 98% ≥ 80% threshold.

Proceed to Phase 2 (Tier 1+2 marker resolution): **YES**