# DCP Structured Controls — Data Provenance Chain

**Date:** 2026-05-23
**Table:** `dcp_setback_controls`
**Total rows:** ~999 across 29 LGAs, 16 control types

---

## What this data is

Structured numeric development controls extracted from NSW council Development Control Plans (DCPs). Each row represents a specific quantitative standard — for example, "minimum rear setback of 6 metres for dwelling houses in R2 zones."

These controls are used in the compliance assessment UI to show users the numeric requirements that apply to their property. They complement the full DCP provision text, which is stored separately in `regulatory_provisions`.

---

## Data extraction methodology

### Source documents

All numeric values are extracted from publicly available council DCP documents. Each row's `source_ref` field identifies the specific DCP section and clause number. Each row's `source_text` field contains the original text from which the value was extracted.

### Extraction process

1. **Identify the control type** — setback, parking rate, landscaping percentage, etc.
2. **Locate the relevant DCP section** — using the council's published DCP (via `regulatory_provisions` or direct PDF access)
3. **Extract the numeric value** — directly from the text, not interpolated or estimated
4. **Record the condition** — zone, development type, lot size threshold, or other qualifier
5. **Set review status** — `needs_review = FALSE` if extracted from verified provision text; `needs_review = TRUE` if based on ADG defaults or assumed standard values

### Quality controls

- **Dedup check:** Every insert script checks for existing rows matching `(lga, control_type, dev_type, condition)` before inserting. Duplicates are skipped.
- **Constraint compliance:** The `applicability` field must match a CHECK constraint (`universal_residential`, `development_specific`, `zone_specific`, `site_specific`).
- **Automated tests:** `tests/test_insert_scripts.py` (17 tests) validates required fields, value ranges, LGA validity, and duplicate prevention for all insert scripts.
- **needs_review flag:** Rows where the value could not be confirmed from direct DCP text are flagged `needs_review = TRUE` with a `review_reason` explaining why.

---

## Control types and coverage

| Control Type | LGAs Covered | Unit | Source |
|---|---|---|---|
| setback_front | 18 | m | Council DCPs |
| setback_rear | 18 | m | Council DCPs |
| setback_side | 18 | m | Council DCPs |
| parking_rate | 27 | spaces/dwelling | Council DCPs |
| landscaping_min | 22 | % or m2 | Council DCPs |
| deep_soil_min | 15 | % or m2 | Council DCPs |
| site_coverage_max | 15 | % | Council DCPs |
| tree_canopy_min | 8 | % | Council DCPs |
| building_height_max | 12 | m | Council DCPs + LEPs |
| building_separation | 10 | m | Council DCPs |
| solar_access_hours | 27 | hours | Council DCPs (PR #354) |
| bicycle_parking | 27 | spaces/dwelling | Council DCPs (PR #357) |
| private_open_space | 29 | m2 | Council DCPs (PR #365) |
| communal_open_space_min | 10 | m2 or % | Council DCPs |
| driveway_width | 5 | m | Council DCPs |
| fencing_height_max | 3 | m | Council DCPs |

---

## Three-state display model

Controls are displayed in the UI using a three-state model (PR #358):

| State | Meaning | How determined |
|---|---|---|
| **Numeric value** | Specific standard extracted from DCP | `value_min` or `value_max` populated, `needs_review = FALSE` |
| **Under review** | Value exists but not yet verified against source | `needs_review = TRUE`, shown with amber indicator |
| **Not applicable** | Council does not have this control type | No row exists for this (lga, control_type) combination |

This model ensures users see clearly whether a number is verified, pending verification, or absent — rather than confusing "no data" with "no requirement."

---

## LGA coverage (29 councils)

All 29 councils with structured controls are listed in `lga_registry` with their canonical slugs and council names. The registry serves as the single source of truth for LGA identification across the system.

---

## Remaining review items

15 rows have `needs_review = TRUE` as of 2026-05-23. These are primarily:
- Councils where DCP text was not available in `regulatory_provisions` (no PDF extract)
- Controls using assumed ADG default values pending council-specific verification
- Controls where the source text was ambiguous about the exact numeric threshold

Each `review_reason` field documents why the row is flagged. Resolution requires locating the council's published DCP document and confirming or correcting the value.
