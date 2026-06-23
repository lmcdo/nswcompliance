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
