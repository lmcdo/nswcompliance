# Extracted-data integrity — the standard

Any table populated by **extracting values from source text** (council PDFs, LEP
tables, SEPP documents) can carry three bug classes:

1. **Fabricated value** — a number invented to fill a gap and stored as fact
   (e.g. "assumed standard NSW POS = 24 m²").
2. **Mislabelled value** — a number scraped from the wrong clause (e.g. a fence
   height stored as a front setback).
3. **Conflicting value** — two contradictory values for the same thing with
   nothing to choose between them.

These are *data* defects. Validating the consuming code (types, ranges, routing)
does not catch them. The reusable engine that does is
[`services/extracted_data_integrity.py`](../services/extracted_data_integrity.py).
It is deterministic (no LLM — per the project's "deterministic only, no AI
interpretation of regulations" rule).

## The three rules every extracted-data table follows

### 1. Never store a guess (write-time gate)
If extraction can't find the real value, store **NULL** (the rule exists, value
unknown → "check with council"), never a default. Call the gate before every
insert:

```python
from services.extracted_data_integrity import assert_clean_row

value = None if unverified else extracted_value          # NULL, not a guess
assert_clean_row(
    {"value": value, "note": condition, "source_text": source_text},
    value_field="value", marker_fields=["note", "source_text"],
)  # raises if a value is stored while a marker admits it is assumed
cur.execute("INSERT ...", ...)
```

### 2. Sweep the table (offline + live)
- **Offline (runs every commit):** a test over the script's own row data — see
  `tests/test_insert_scripts_integrity.py`. Catches a guess added to the source
  list, or a broken NULL-for-unverified path, before it reaches the DB.
- **Live (maintenance cron):** a `@pytest.mark.database` ratchet — see
  `tests/test_dcp_setback_validation.py` — asserting the live high-severity count
  never grows.

```python
from services.extracted_data_integrity import conflicting_values, fabricated_values
conflicting_values(rows, key_fields=[...], value_field="...", condition_field="...")
fabricated_values(rows, value_field="...", marker_fields=[...])
```

### 3. Silent guesses → human review (advisory)
`value_absent_from_source(rows, value_field=..., source_field=...)` flags a value
whose digits don't appear in its own source text. It has false positives (unit
conversions, "3m x 3m" = 9 m²), so it routes a row to **review**, never a hard
block.

### 4. Named derivations → a value the source does NOT support (gating)
A flag is not an answer. Re-measured on `dcp_setback_controls` (2026-08-02),
`value_absent_from_source` returns **142 rows**, and most are legitimate
derivations. A list where most entries are fine is a list people stop reading —
which is how a real mismatch survives inside it.

`explain_value` / `explain_row` name the transformation instead, and every rule
must return the substring it matched:

```python
from services.extracted_data_integrity import explain_row, RULE_NAMES, UNEXPLAINED
explain_row(row, value_fields=["value_min", "value_max"],
            source_field="source_text", unit_field="unit")
# -> {"state": "unit_conversion", "fields": {...evidence per field...}}
```

Rules, ordered most-direct to most-derived: `exact_digit_match`,
`percentage_phrasing`, `unit_conversion`, `fraction_literal`, `ratio_or_rate`,
`implied_single_unit_rate`, `area_from_dimensions`, `written_numeral`,
`explicit_nil_requirement`, `built_to_boundary_zero`. Anything left is
`UNEXPLAINED`; a row with no number at all is `no_value_stored`, which is counted
separately and is **not** a pass.

A row's state is the most-derived rule any of its values needed, and one
unexplained end of a range makes the whole row unexplained.

**The rules under-claim on purpose.** A false explanation hides a real defect
permanently, so no rule fires on a bare number: percentages need a literal `%`,
conversions need a literal unit token, rates need an explicit "per"/"for every".
Numbers inside clause references (`s4.3.6`) and numbered-list ordinals (`2. ...`)
are excluded from quantity matching — both were live false-pass channels.

Gate: `scripts/validate_control_source_values.py`, wired into pre-push `[1f/5]`
and CI. Shrink-only baseline in `scripts/control_source_values_baseline.json`.
Covers all 1,069 controls, versus the 42 reachable through the provisions corpus.

## Adding a new extracted table — checklist
- [ ] Insert path calls `assert_clean_row` and writes NULL for unverified rows.
- [ ] An offline test sweeps the source rows with `fabricated_values` /
      `conflicting_values` (config: value column, key columns, marker/condition).
- [ ] A live `@pytest.mark.database` ratchet test (baseline 0 for new tables).

## Coverage to date (2026-06-24 sweep)
| Table | Rows | Conflicts | Fabricated |
|---|---|---|---|
| dcp_setback_controls (setbacks) | — | 0 (was 10) | 0 (was 27) |
| dcp_setback_controls (other) | 708 | 1 (Marrickville separation) | 0 |
| lep_land_use_table | 17,353 | 0 | 0 |
| housing_sepp_standards | 45 | 0 | 0 |

The PDF-prose DCP setbacks carried the bug; the structured LEP/SEPP tables were
clean.
