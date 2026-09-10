# DCP Scope Config Reference

**Last updated:** 2026-09-10
**Source:** Research across 13 NSW councils (Inner West × 3, Inner East × 4, future pipeline × 6+)

This document defines the `universalPartKeys` and `devTypeGatedPartKeys` values for each council's
`lib/council-configs/{council}.json`. These are the only two fields that drive DA mode scope behaviour.

---

## Default scope for a NEW council — extract ~6 chapters, not the whole DCP

**Added 2026-09-10.** Everything above describes councils already onboarded, where the
whole DCP was registered and extracted. That is the wrong default for the next one, and
the measurement says so plainly.

### What the product actually consumes

Every numeric control the app renders is **residential**, measured across all 1,071
current rows of `dcp_setback_controls`:

| dev_type | rows |
|---|---|
| dwelling_house | 308 |
| residential_flat_building | 253 |
| multi_dwelling_housing | 166 |
| dual_occupancy | 103 |
| secondary_dwelling | 52 |
| shop_top_housing | 37 |

No industrial, no childcare, no sex services, no places of worship. The chapters that
produced them are equally narrow: parking chapters, landscaping chapters, low/medium
density residential chapters, transport chapters.

### What a full DCP extraction actually yields

Measured across the 11,952 served council provisions on 2026-09-10:

| topic | share |
|---|---|
| heritage | **19.9%** |
| building_form | 8.0% |
| parking | 7.8% |
| **signage** | **7.5%** |
| residential | 6.5% |
| site_analysis | 5.6% |
| height | 3.9% |
| landscaping | 3.8% |
| setbacks | 3.6% |
| waste / roofing / fencing / safety | ~9% combined |

So the four control topics the product renders are about a fifth of the text, while
heritage alone is a fifth and signage is another 7.5%. Registering and extracting a whole
DCP spends most of the effort on content no common use case reaches.

### The default scope

For a new council, register and extract these and nothing else:

1. **General / introductory part** — how the DCP applies, definitions, site analysis.
2. **Low and medium density residential** — the source of setbacks, height, site coverage,
   private open space.
3. **Residential flat buildings**, where the council separates it.
4. **Parking and transport.**
5. **Landscaping and trees.**
6. **Heritage — second priority, not skipped.** It is the largest single topic and the
   spatial layer already answers *whether* a property sits in a conservation area. What
   the DCP adds is what that means for a design, which is a real question. Do it after
   the first five, not instead of them.

**Explicitly out of scope on a first pass:** signage, industrial, waste management,
childcare, educational establishments, places of worship, licensed premises,
telecommunications, sex services, outdoor dining — and any registry entry that is a
**map sheet**. City of Sydney alone carries 234 registered map sheets that can never
produce a provision; they inflate every backlog count that reads the registry.

That is roughly six chapters instead of forty: five to six times less registration,
extraction and review for the part people actually use.

### ⚠ Narrowing the scope creates a claim problem — handle it in the same change

A council with six extracted chapters does **not** have "DCP controls". Labelling it that
way is the same overclaim removed on 2026-09-10, when eight councils were found asserting
`hasDcpData: true` with zero rows behind them (PR #1075). Partial scope must surface as
partial: "residential development controls", not "DCP".

`scripts/verify_lga_capability_flags.py` runs daily and fails when a per-council flag
claims something the database does not support. Setting a council's flag before its
provisions land will turn that job red the next morning.

### Per-council status, measured 2026-09-10

A pass over every registered chapter title in `dcp_chapter_registry`. The finding
that matters: **for most councils the scope was already chosen correctly, and the
blocker is not scope at all.**

Burwood has `part-4-residential`, `s4-landscaping`, `s4-table-4-parking`. Fairfield
has `chapter-5-dwelling-houses`, `landscaping-controls`, `parking-controls`.
Strathfield, Canada Bay, Liverpool, Ryde, Randwick, Camden — all the same shape.
Somebody already picked residential + parking + landscaping for these councils.
**None of them has a mirrored PDF**, so nothing can be extracted.

**50 chapters across 22 councils have no mirrored PDF. Only 15 of those even carry a
`council_url` to fetch from** — the other 35 need the source document located first.
That, not chapter selection, is the work.

| Council | Registered | Core areas covered | Blocker |
|---|---|---|---|
| Ku-ring-gai | 38 | all six | none — see the yield note below |
| Woollahra | 27 | five (no RFB part) | none |
| City of Sydney | 8 + 234 map sheets | all six, inside sections 3 and 4 | none. Its DCP is structured by section, not topic — a topic-keyword scan reports it as empty, wrongly |
| Canterbury-Bankstown | 68 | five (no RFB part) | 29 chapters awaiting extraction; **6 duplicate registrations** of the same waste chapter |
| Penrith | 2 | parking, residential | needs general, landscaping, heritage |
| Hornsby | 2 | residential, general | needs parking, landscaping, heritage |
| Blacktown | 2 | residential, parking | needs general, landscaping, heritage |
| Campbelltown | 2 | residential, RFB | needs general, parking, landscaping |
| Georges River | 2 | general, residential | needs parking, landscaping, heritage |
| Cumberland | 2 | residential, parking | parking chapter has no PDF |
| Waverley | 4 | general, parking, landscaping | landscaping and transport have no PDF |
| Northern Beaches | 4 | one consolidated DCP extracted | the three part-level entries have no PDF |
| Parramatta | 2 | one consolidated DCP extracted | transport part has no PDF |
| Bayside, Burwood, Camden, Canada Bay, Fairfield, Liverpool, Randwick, Ryde, Strathfield, Sutherland Shire, The Hills, Wingecarribee | 1–3 each | **already the right ones** | **no PDF mirrored, on any of them** |

### Two things this pass corrected

**Ku-ring-gai's low yield is mostly chapter mix, not an extraction defect.** It produces
358 provisions from 38 chapters where Woollahra produces 739 from 27. But **15 of its 38
chapters are site-specific** `section-b-part-14a` … `14o` local-centre and single-site
parts (Pymble Golf Club, 45–47 Tennyson Avenue), and they account for 115 of the 358.
The remaining 23 general chapters yield about 10 provisions each against Woollahra's 27,
so a gap remains — but it is much smaller than the headline suggests, and calling it a
defect on the raw ratio would have been wrong.

**A keyword scan cannot classify these chapters reliably.** Applied to City of Sydney it
reported no residential, no parking and no landscaping, because their sections are named
structurally. All three are present inside `section-3-general-provisions` and
`section-4-development-types`. Any future automated scope audit must read chapter
CONTENT or a human must read the titles — matching on the title text alone produces
confident wrong answers on exactly the councils whose structure differs most.

### What this does NOT change

Precinct and heritage parts still self-gate through the for-property API layer system
(`v2_dcp_layer` = condition / precinct) and still do not belong in either array. Zone-tier
parts are still handled by the API `use_specific` layer. The two fields below drive DA
mode scope behaviour exactly as before — this section narrows what gets *registered and
extracted*, not how scope is expressed once it is in.

---

## How to read this table

- **universalPartKeys** — parts that must always be shown to the planner regardless of dev type.
  Match these exactly to `v2_dcp_part` values in the DB for that council.
- **devTypeGatedPartKeys** — parts where dev type is a structural gate (DCP document itself partitions
  by dev category). Auto-dismiss of non-matching parts is defensible.
- **Precinct / heritage parts** — handled by the for-property API layer system (v2_dcp_layer =
  condition / precinct). Do not put them in either array — they self-gate via property attributes.
- **Zone-tier parts** (Residential / Commercial / Industrial) — already handled by the API
  `use_specific` layer. Do not put these in devTypeGatedPartKeys unless the DCP document explicitly
  labels them by dev category (not just zone).

---

## Inner West (currently onboarded)

### Ashfield — Inner West DCP (Ashfield) 2016
```json
"universalPartKeys": ["Chapter A", "Chapter B", "Chapter C"],
"devTypeGatedPartKeys": ["Chapter F"],
"daDevTypeRole": "chapter_selector"
```
Chapter F sub-parts: F1 Dwelling Houses, F2 Dual Occupancy, F3 Multi Dwelling, F4 RFBs,
F5 Boarding Houses, F6 Commercial, F7 Industrial, F8 Childcare, F9 Sex Services, F10 Other.
Chapter D (precincts) and E1/E2 (heritage) = API-gated, not in arrays.

### Marrickville — Inner West DCP (Marrickville) 2011
```json
"universalPartKeys": ["Part 1", "Part 2"],
"devTypeGatedPartKeys": ["Part 3", "Part 7"],
"daDevTypeRole": "subpart_selector"
```
Part 2 has 16 sub-sections — all must reach the planner (parking, solar, privacy, landscaping etc).
Parts 4/5/6 (Residential/Commercial/Industrial) = zone-gated by API, not dev-type-gated by app.
Part 3 = subdivision only. Part 7 = childcare + sex services.
Part 8 (heritage) and Part 9 (precincts) = API-gated.

### Leichhardt — Inner West DCP (Leichhardt) 2013
```json
"universalPartKeys": ["Part A", "Part B", "Part C", "Part D", "Part E"],
"devTypeGatedPartKeys": ["Part F"],
"daDevTypeRole": "sort_only"
```
Part F = food premises only (23 provisions). Almost everything else is universal.
Parts C Section 2 and G (distinctive neighbourhoods) = API precinct-gated.

---

## Inner East (to be onboarded)

### Woollahra — Woollahra DCP 2015
```json
"universalPartKeys": ["Part A", "Part E"],
"devTypeGatedPartKeys": ["Part F"],
"daDevTypeRole": "subpart_selector"
```
Part E = parking/access, stormwater, trees, contamination, waste, sustainability, signage, adaptable housing.
Part F = childcare, educational establishments, licensed premises, telecommunications.
Part B (residential zones), Part C (heritage HCAs), Part D (commercial centres) = API-gated.
Part G (specific sites) = API precinct-gated.

### Waverley — Waverley DCP 2022
```json
"universalPartKeys": ["Part A", "Part B"],
"devTypeGatedPartKeys": ["Part C", "Part D", "Part F"],
"daDevTypeRole": "chapter_selector"
```
Part B = waste, ESD, landscaping, coastal risk, water, accessibility, transport, heritage, safety, public art.
Part C = residential (C1 low density, C2 other). Part D = commercial (D1, D2 outdoor dining).
Part F = specific dev types: shared accommodation, tourist/visitor, childcare, places of worship.
Part E (site specific) = API precinct-gated.

### Randwick — Randwick Comprehensive DCP 2013
```json
"universalPartKeys": ["Part A", "Part B"],
"devTypeGatedPartKeys": ["Part C", "Part D"],
"daDevTypeRole": "chapter_selector"
```
Part B = design, heritage, ESD, landscaping, trees, waste, transport/parking, water, management plan, foreshore, laneways.
Part C = residential (C1 low density, C2 medium density, C3 adaptable, C4 boarding houses).
Part D = commercial sub-types + specific uses (childcare, backpackers, amusement, sex services, late night).
Part E (specific sites), Part F (miscellaneous) = API precinct/condition-gated.

### City of Sydney — Sydney DCP 2012
```json
"universalPartKeys": ["Section 1", "Section 3"],
"devTypeGatedPartKeys": ["Section 4"],
"daDevTypeRole": "chapter_selector"
```
Section 3 = 17 topic sub-sections (public domain, design excellence, ESD, heritage, transport/parking,
  accessible design, waste, signage, contamination, water/flood, urban ecology, social/environmental,
  late night trading, significant architectural building types).
Section 4 = single dwellings/terraces/dual occ, RFBs/mixed use, industrial, other dev types.
Section 2 (13 locality statements) = informative context, not a scope gate. Do not put in either array.
Sections 5–6 (specific areas + sites) = API precinct-gated.
NOTE: Section 3 is very large (hundreds of pages). Expect high provision count in universalPartKeys.

---

## Future pipeline

### Ku-ring-gai — Ku-ring-gai DCP 2022 (Amendment 1)
```json
"universalPartKeys": ["Part 1", "Part 2", "Part 13", "Section B", "Section C"],
"devTypeGatedPartKeys": ["Part 4", "Part 5", "Part 6", "Part 7", "Part 8", "Part 9", "Part 10", "Part 11", "Part 12"],
"daDevTypeRole": "chapter_selector"
```
Section A dominates — 8+ dev-type-specific parts (dwelling houses, dual occ, MDH, RFBs, mixed use,
non-residential, childcare, secondary dwellings, seniors housing etc).
Section B = environmental/special controls (heritage, biodiversity, contamination) = API condition-gated.
Section C = universal technical standards (site design, access/parking, building design, water, notification).
NOTE: devTypeGatedPartKeys will be the longest of any council. Dev type dropdown must map precisely
to the correct Section A part. This is the most Ashfield-like structure of the future pipeline.

### Bayside — Bayside DCP 2022
```json
"universalPartKeys": ["Part 1", "Part 3", "Part 8"],
"devTypeGatedPartKeys": ["Part 2", "Part 4"],
"daDevTypeRole": "chapter_selector"
```
Part 3 = general development provisions (design excellence, energy/water efficiency, biodiversity,
  tree management, late-night premises, flood management, contamination, ESD).
Part 8 = managing risk and environmental conditions.
Part 2 = residential and mixed-use. Part 4 = commercial and employment.
Parts 6–7 (specific places) = API precinct-gated.

### North Sydney — North Sydney DCP 2025
```json
"universalPartKeys": ["Part A", "Part B", "Part C", "Part D"],
"devTypeGatedPartKeys": ["Part E"],
"daDevTypeRole": "chapter_selector"
```
Part B = 11 environmental factor sections (topography, visual impact, biodiversity, water, solar,
  privacy, noise, light, wind, sustainability, contamination).
Part C = heritage conservation (items and areas).
Part D = premises and signage.
Part E = dev types: residential, employment zones, boarding houses, telecommunications.
Part F (planning areas) = API precinct-gated.
NOTE: Explicitly designed for AI-assisted assessment. Clean factor/type/area separation.

### Canterbury-Bankstown — Canterbury-Bankstown DCP 2023
```json
"universalPartKeys": ["Chapter 1", "Chapter 2", "Chapter 3"],
"devTypeGatedPartKeys": ["Chapter 4", "Chapter 5"],
"daDevTypeRole": "chapter_selector"
```
Chapter 3 = general development provisions (trees, engineering, parking, sustainable development,
  landscape design, signage, subdivision).
Chapter 4 = residential accommodation (split by former LGA area within chapter).
Chapter 5 = employment development.
Chapters 6–7 (strategic/local centres) + Chapter 11 (key sites) = API precinct-gated.

### Lane Cove — Lane Cove DCP 2009 (as amended)
```json
"universalPartKeys": ["Part A", "Part B", "Part F", "Part J", "Part O", "Part Q", "Part R", "Part S"],
"devTypeGatedPartKeys": ["Part C", "Part D", "Part E"],
"daDevTypeRole": "chapter_selector"
```
Universal topics are fragmented across many alphabetical parts (legacy patch structure):
  Part B = general controls (incl. heritage). Part F = access/mobility. Part J = landscaping/trees.
  Part O = stormwater. Part Q = waste. Part R = traffic/parking. Part S = sustainability.
Part C = residential. Part D = commercial/mixed use. Part E = industrial.
NOTE: universalPartKeys is the longest of any council (~8 entries). This is a structural artefact of
the 2009 base document being patch-amended rather than comprehensively restructured.

### Northern Beaches — THREE SEPARATE DCPs (not consolidated)
**Do not create one `northern_beaches` config. Create three separate councils:**

**`warringah` — Warringah DCP 2011**
```json
"universalPartKeys": ["Part A", "Part B", "Part C", "Part D", "Part E"],
"devTypeGatedPartKeys": [],
"daDevTypeRole": "sort_only"
```
Parts B–E are all topic/factor-based. No dev-type chapters at top level.
Zone differentiation in Part F. Area controls in Part G = API precinct-gated.
Most topic-universal structure after Leichhardt.

**`pittwater` — Pittwater 21 DCP**
```json
"universalPartKeys": ["Section A", "Section B"],
"devTypeGatedPartKeys": ["Section C"],
"daDevTypeRole": "chapter_selector"
```
Section D (12 named localities: Avalon, Bayview, Bilgola, Church Point, Elanora, Ingleside,
Mona Vale, Newport, North Narrabeen, Palm Beach etc) = API precinct-gated.

**`manly` — Manly DCP 2013**
```json
"universalPartKeys": ["Part 1", "Part 2", "Part 3"],
"devTypeGatedPartKeys": ["Part 4"],
"daDevTypeRole": "chapter_selector"
```
Part 5 (special character precincts) = API precinct-gated.

For-property API routing must identify which of the three legacy DCPs applies for a given
Northern Beaches address based on the former-council / document_id.

---

## Key onboarding rules

1. **Match part key strings exactly to `v2_dcp_part` values in the DB.** Run:
   ```sql
   SELECT DISTINCT v2_dcp_part FROM regulatory_provisions
   WHERE source_council = '<council>' AND is_current = true
   ORDER BY v2_dcp_part;
   ```
   before populating the JSON config.

2. **Heritage and precinct parts are never in either array.** They are API-gated via
   `v2_dcp_layer = condition` or `precinct` on the provision. The for-property API already
   handles these. Putting them in universalPartKeys would force them to load for all properties.

3. **Zone-tier parts (residential/commercial/industrial) go in devTypeGatedPartKeys only if
   the DCP document explicitly labels them by development category** (like Ashfield Chapter F).
   If they're labelled by zone (R2/B4/IN1), the API layer system handles them — don't double-gate.

4. **For councils with fragmented universal topics (Lane Cove):** universalPartKeys will have
   many entries. This is expected. The arrays can be long.

5. **For multi-DCP councils (Northern Beaches):** one config per legacy DCP, not per merged LGA.
   The routing key must match what the for-property API uses to identify the council.

6. **Verify after populating:** run a test DA through the API and check that displayProvisions
   contains the right sections. Compare against the DCP table of contents manually.
