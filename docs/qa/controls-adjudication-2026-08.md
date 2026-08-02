# Adjudication of the 25 UNEXPLAINED controls — evidence pass

**Date:** 2026-08-03 · **Writes to `dcp_setback_controls`: none.**

`scripts/validate_control_source_values.py` flags 25 of 986 numbered controls as
`UNEXPLAINED`: the stored number cannot be derived from its own `source_text`.
This pass obtained the source for 23 of them and rules on what the clause says.

## Headline: the flag was mostly measuring quote quality, not value quality

| verdict | rows |
|---|---|
| **CORRECT** — value right, quote incomplete | **12** |
| **EXTRACTION_ERROR** — value wrong for the version it claims | **8** |
| **NO_NUMERIC_CONTROL_IN_SOURCE** — source states no number | **3** |
| **UNVERIFIABLE** — source unobtainable | **2** |

**Every one of the 11 rows whose source had to be fetched turned out CORRECT.**
Every error was in a council whose PDF was already sitting on disk. That is not a
coincidence about councils — it is that the older, locally-cached extractions are
the ones with the defects.

## The correction that matters most

DQ-39 originally led with *"Waverley 631/632 store 10% and 635/636 store 15%
against a quote reading 'a minimum 50% of the landscaped area must be deep soil
zone'"* and called those four rows the most serious finding. **They are correct.**

- `C1.9(c)`: *"A minimum of **20%** of the total site area is to be provided as
  landscaped area."* `C1.9(d)`: *"A minimum **50%** of the landscaped area must be
  deep soil zone."* → 50% × 20% = **10% of site**. Rows 631/632 store 10. ✓
- `C2.9(b)`: *"**30%** of the site area is to be provided as landscaped area."*
  `C2.9(c)`: *"**50%** of the landscaped area must be deep soil zone."* →
  **15% of site**. Rows 635/636 store 15. ✓

The control is a **two-clause derivation** and `source_text` stored only the
second clause. The checker saw "50" and a stored "10" and could not do otherwise.
I asserted a defect from a partial quote; the lesson is the same one this whole
workstream keeps relearning — **an incomplete quote is not evidence of a wrong
number.**

## All 25

### CORRECT (12) — value verified against the clause

| id | council / control | stored | source says | where | evidence |
|---|---|---|---|---|---|
| 631, 632 | waverley deep_soil | 10 % | 20% site landscaped × 50% deep soil | C1.9(c)+(d), p.204 | STRONG |
| 635, 636 | waverley deep_soil | 15 % | 30% site landscaped × 50% deep soil | C2.9(b)+(c), p.233 | STRONG |
| 1 | marrickville side_setback | 1.5 m | *"a minimum of 1.5 metres side setback from allotment's side boundaries"* | C11 iii.b, p.14 | MEDIUM |
| 2 | marrickville separation | 4.0 m | *"minimum separation distance of 4 metres … secondary dwelling is located at the rear"* | C11 v.a, p.14 | MEDIUM |
| 6 | marrickville separation | 1.8 m | *"minimum separation distance of 1.8 metres … located at the side"* | C11 v.b, p.14 | MEDIUM |
| 517 | marrickville car_parking | 0 /dwelling | *"1 per principal dwelling and secondary dwelling combined"* → marginal 0 | Table 1, p.9 | STRONG |
| 3 | ku_ring_gai rear_setback | 6.0 m | *"Rear setbacks for secondary dwellings are to be a minimum of 6m from the rear boundary."* | 4.1A.3, p.7 | MEDIUM |
| 13 | woollahra side_setback | 0.9 m | Figure 5A: site width **< 9.0 m → 0.9 m** | B3.2.3 C1, p.16 | MEDIUM |
| 229 | georges_river car_parking | 2 /dwelling | *"1 garage space and 1 driveway space per dwelling"* → 1+1 | Dual Occupancy, p.28 | STRONG |
| 30 | cumberland rear_setback | 8.0 m | *"Rear Setback — Minimum 8m"* | Table 1, p.B8 | STRONG |

Why each was flagged despite being right: **garbled OCR** capturing a heading
instead of the control (ku_ring_gai, marrickville ×3); **a hand-written summary**
rather than the clause (woollahra); **one clause of a two-clause derivation**
(waverley ×4); **a sum of two stated components** (georges_river — deliberately
not given a rule, since summing arbitrary numbers would explain almost anything);
**a 400-character truncation** severing the row (cumberland 30).

### EXTRACTION_ERROR (8) — value wrong for the version it claims

| id | council / control | stored | source actually says | where |
|---|---|---|---|---|
| 31 | cumberland front_setback | 4.0 m | *"Secondary Frontage … Minimum 4m"* — a **secondary** street setback | Table 1, p.B8 |
| 32 | cumberland front_setback | 5.5 m | *"garage to be setback a minimum 5.5m"* — a **garage** setback | Table 1, p.B8 |
| 690 | camden front_setback | 3.5 m | For the case its own condition describes the table gives **4.5 m**; 3.5 m is only the exception *"where the development is fronting open space"* | Table 4-2, p.P4-8 |
| 692 | camden front_setback | 4.0 m | *"driveway crossover (minimum 4m for double garage)"* — a **driveway width** | p.P4-20 |
| 693 | camden front_setback | 2.0 m | *"Secondary Setback — 2m"* | Table 4-2, p.P4-8 |
| 255 | campbelltown car_parking | 2 spaces | *"restricted to a maximum of 18 m² … and 36 m²"* — an **area cap**, no count of spaces anywhere | s3.6.1.4, p.21 |
| 1119 | cumberland POS | 24 m² | *"minimum area of **50m²** … lots greater than 451m²; **30m²** … 450m² or smaller"* | s2.8, p.B15 |
| 1120 | campbelltown POS | 24 m² | *"has a minimum area of **75sqm**"* | s3.6.1.5, p.21 |

Six of these eight are already `is_current = FALSE`. The two that are still
served are **camden 690 and 692**.

**Cumberland and Camden share one failure mode**: secondary-frontage and
garage/driveway figures stored as `front_setback`, and the *primary* front setback
missed — entirely in Camden's case (no row holds 4.5 / 6.5 / 10 m), while
Cumberland captured it separately as id=28.

### NO_NUMERIC_CONTROL_IN_SOURCE (3) — provisional

City of Sydney 883 / 884 / 885 quote clause 4.1.2 **verbatim**, and 4.1.2 contains
no numbers at all: *"consistent with the Building setbacks map"*, *"relate to the
established development pattern"*, *"respect and be sympathetic to the predominant
rear building line"*. The stored 0 m / 0–0.9 m / 3–8 m come entirely from each
row's `condition`, which is candid — *"prevailing rear yard depth (varies by
block, typically 3-8m)"*. An observed terrace pattern was encoded as a prescribed
control. The honest state is NULL with the qualitative text, which is what
`assert_clean_row` already enforces at write time.

**Provisional**: the PDF read is headed *"Sydney DCP 2012 — December 2012"*; the
rows claim *"Sydney DCP 2012 (amended Jan 2026)"*, effective 2026-01-28. If that
amendment introduced numbers into 4.1.2, this reading is stale.

### UNVERIFIABLE (2)

- **ryde 778** (car_parking 1–2) — chapter `part-9.3-parking` has no `council_url`,
  no R2 path, `url_last_checked` NULL. The local Ryde PDF is a different chapter.
- **sutherland_shire 606** (front_setback 5.5 m) — cites *"LEP 2015 Schedule 3"*,
  an LEP rather than a DCP; registry entry is a stub with no URL.

## Two counts that change how the 97.5% should be read

### (a) Truncation — 23 rows cut at exactly 400 characters

Every one ends mid-word. Councils: cumberland 6, camden 5, canada_bay 4,
marrickville 3, ryde 3, ku_ring_gai 1, burwood 1. Two more sit at 200 and four at
250. Separately, **246 of 986 quotes (25%) end mid-word with no terminal
punctuation.**

This cuts both ways, which is the point: cumberland 30 was **falsely flagged**
because its evidence was severed, and cumberland 28 (front 6.0 m, served,
unflagged) sits on the **same 400-char truncation** and passed only because "6m"
happened to fall inside the surviving window. A truncated quote produces false
flags and false passes from the same defect, so the "97.5% explained" figure is
softer than it looks.

### (b) Control-type mismatch — 28 rows, 26 of them served

Rows whose `control_type` and `source_text` disagree: 23 `front_setback`,
4 `side_setback`, 1 `rear_setback`. Councils: georges_river 4, the_hills 3,
campbelltown 2, penrith 2, camden 2, cumberland 2, parramatta 2,
canterbury_bankstown 2, and others.

**24 of the 28 PASS the value checker** — the number matches its quote exactly
while describing the wrong control. Samples:

- `id=581 georges_river front_setback 3 m` ← *"The minimum setback (ground and first floor) to a **secondary** street is 3m"*
- `id=568 parramatta front_setback 4 m` ← *"On corner lots, the **secondary street** setback must be a minimum of 4 metres"*
- `id=96 liverpool front_setback 2.0 m` ← *"Table 3: **Secondary street** setback minimum 2.0m"*
- `id=607 sutherland front_setback 3 m` ← *"A setback from any **secondary frontage** of at least 3m"*

This is a class the value checker **structurally cannot see**, and it is the more
serious of the two: a secondary-street setback (typically 2–4 m) served as the
primary front setback (typically 4.5–6 m) understates the requirement, in the
direction that matters. It is systematic across at least ten councils.

## Gate added

`fabricated_values` is now wired into `scripts/validate_control_source_values.py`
and blocks when a row whose own note admits the value was assumed is **served**.
28 rows across ~14 councils carry such a note (a 24 m² POS default and a 3-hour
solar default); **all 28 are already `is_current = FALSE`**, so the gate passes
today and stops the next one reaching production. `validate_dcp_setbacks.py`
already called the same function, but only over ~280 setback rows and only as an
advisory signal that never affected its exit code.

---

# Close-out pass, 2026-08-03 — DQ-40 MISSING_PRIMARY rulings

Writes: `scripts/repair_canada_bay_rear_setback.py` (1 row) and
`scripts/repair_missing_primary_controls.py` (8 updates + 2 inserts). Backups:
`dcp_setback_controls_cb701_repair_20260803`,
`dcp_setback_controls_missing_primary_20260803`. Every ruling read from the
source PDF in `data/dcps/`; nothing inferred from another clause.

## canada_bay 701 — the live 4× understatement

Served rear 1.5 m; its own 400-char-truncated quote was the **C6 side-boundary
table** ("second storey … 1500mm from side boun…"). No true rear value existed
anywhere. Corrected to **6.0 m** per C9, printed p.E-15 ("All development (not
including an outbuilding or secondary dwelling) is to have a minimum rear
setback of 6.0 metres…"), quote replaced in the same UPDATE (rule 2b). C10
(9.0 m upper-floor living room), C11 (3.0 m secondary dwelling) and C12
(corner-lot 1.5 m) recorded in `condition` as not stored.

## The 8 MISSING_PRIMARY rows

| row | ruling | action |
|---|---|---|
| ryde 680 (front 8.0) | quote IS s2.9.3(a), the general REAR control; 8 m is the floor of "25% of site length or 8 m, whichever greater". Ryde's real front control (6 m, s2.9.1(a) p.25) was stored NOWHERE | re-filed → rear_setback with the full clause; **front 6.0 m INSERTED (id 1175)**; 681 re-quoted to the s2.9.3(b) exception it stores and conditioned |
| burwood 707 (side 0.9) | P10 is the garage-WALL side rule; general side (Table 3 p.221: 900mm single storey / 1.5m second-storey component) stored NOWHERE | 707 conditioned as garage-wall; **side 0.9–1.5 m INSERTED (id 1176)**, range-row shape per row 1080 |
| camden 691 (side 0.9) | value matches the general Table 4-2 side setback; quote was the zero-lot-line rear-yard ACCESS rule | quote replaced with Table 4-2 side row (rule 2b); the general control now carries its own evidence |
| fairfield 714 (front sd 6.0) | the 6 m is 5C.2.3.1(b) — a garage setback from Chapter **5C Dwelling Houses on Narrow Lots**; 5B.2.3.1 (p.176) prescribes NO numeric front setback for secondary dwellings | **RETIRED** (camden-692 model: no correct value to substitute) |
| fairfield 715 (side sd 0.9) | value matches 5B.2.3.1(a) "minimum side and rear setbacks of 900mm"; quote was Chapter 5C's | quote replaced with 5B.2.3.1(a) (rule 2b) |
| georges_river 229, campbelltown 256/257 (parking) | their quotes ARE the general rule stated in garage terms | no DB change; detector now exempts inherent wording (car_parking↔garage) |
| cumberland 34 (secondary street sd 3.0) | corner scope is inherent in the control type | no DB change; detector exemption (secondary_street_setback↔corner) |
| city_of_sydney 884 (side 0) | clause 4.1.2 holds no numbers (see NO_NUMERIC ruling above) | nothing to add without inventing; fix awaits authorisation |

## Adjacent defects found while ruling — flagged fail-closed, not repaired

- **fairfield 716** (rear sd 6.0, served): 5B.2.3.1(a) prescribes **900mm**;
  the stored 6.0 is 5C.2.3.3 (first-floor walls, narrow lots). needs_review=TRUE;
  the 0.9 repair is a one-line authorisation away.
- **ryde 682** (side 4.0, served): quote says "a minimum side setback of 4 m is
  **preferred**" — a design preference for northerly aspects. True general side:
  s2.9.2(a)/(b) 900mm / 1.5 m, stored nowhere. needs_review=TRUE.

## Detection-side changes

- v1 blind spot closed: FOREIGN patterns match "side/rear **boundaries**"
  wording, not just "…setback" (canada_bay 701's lesson).
- Sol's truncation escape closed in `evidence_is_truncated`: length == 400 is a
  cut regardless of terminal punctuation (all 21 at-limit rows end mid-word, so
  no verdict changed today; the hole mattered for the next extraction).
- KNOWN_FALSE_POSITIVES: + blacktown 105 (s3.2.5 verified against the local PDF
  — one clause governs side AND rear), + 707/714/715 with their rulings above.

**End state:** category A 28 → **3** (884 / 570 / 895, each with a stated
blocker), category B 6 → **0**, truncated 21 → 19, value-checker baseline
41 → 38 (shrink-only), checker exit 0.
