# Proposed numeric DCP controls — NOT INSERTED, NOT SERVED

Nothing in this directory is in `dcp_setback_controls` and nothing here is served
to a user. These are proposals and the record of the reading that judged them.
They are committed so the reading is checkable later by someone other than its
author, which a chat message is not.

## The three files per control type

| file | what it is |
|---|---|
| `<control>.accepted.json` | rows that passed the MECHANICAL gate — `scripts/dcp_verify_extracted_controls.py`: quote verbatim on the cited page, and the number inside that quote |
| `<control>.verdicts.json` | the reading — one verdict and a written reason per row, keyed by `council\|control_type\|dev_type\|section_ref\|page\|value_min` |
| `<control>.reviewed.json` | the rows cleared to the human review surface, with corrections applied and re-checked |

Re-run the reading with:

```
python scripts/dcp_review_proposals.py <control>.accepted.json \
    --verdicts <control>.verdicts.json --pages <candidates>.json \
    --out <control>.reviewed.json
```

It exits non-zero if any row is unreviewed, carries an unexplained verdict, or
if a correction moved a value out of its own quote.

## Why a reading exists at all

The mechanical gate proves a number is in the document and inside its own quote.
It cannot read. On the first run all 11 proposals passed every mechanical check
and four still had to be changed. Three failure modes recur, none of them visible
to a string comparison:

- **DIRECTION** — the concession stored as the requirement. "Must be 6 metres …
  may be reduced to 4.5 metres at Council's discretion" stored as 4.5.
- **SCOPE** — a precinct or single-address figure served LGA-wide, overriding the
  council's real general answer.
- **GRAIN** — a correct number answering a different question: an upper-level
  massing setback, a deck depth from a figure legend, a freeboard above the
  Probable Maximum Flood rather than the 1% AEP.

## This run — 2026-09-12

| control | proposed | mechanically accepted | cleared by the reading | councils |
|---|---|---|---|---|
| `secondary_street_setback` | 12 | 12 | **4** | parramatta |
| `private_open_space` | 36 | 33 | **16** | parramatta, city_of_sydney |
| `flood_freeboard_min` | 15 | 15 (dry run) | **5** | ashfield, canterbury_bankstown, ku_ring_gai, marrickville |
| `corner_setback_11` | 11 | 10 | **3** | hornsby |

`corner_setback_11` is the earlier corner-setback run (ashfield, hornsby,
marrickville), reviewed once in a scratch file nobody else could run and put
through this pipeline on 2026-09-12. Two verdicts changed on re-reading, both
because evidence was checked this time that was not checked then:

- **ashfield DS5.5** was accepted narrowly with an `applicability` qualifier. It
  is now rejected: nothing filters on `applicability` (see DQ-99), so marking
  scope in that column does not contain the scope.
- **marrickville C11(i)** was corrected 4.5 → 6 and accepted. Our own table
  already holds that 6m as `multi_dwelling_housing front_setback` at
  `s4.2.4.3-C11(i)` — the same clause. The clause states a discretionary
  reduction of the secondary building line to 4.5m without ever stating the
  requirement it reduces from, so neither number can be stored, and storing 6
  would re-serve the primary figure as the secondary one — the exact defect
  DQ-40 created `secondary_street_setback` to fix.

One row never reached the reading: **marrickville C29(iii)**, a clean, LGA-wide,
boundary-relative 1.5m secondary setback for industrial development. `dev_type`
has no industrial value — all 16 in use are residential or mixed_use — so the
vocabulary gate stopped it. A vocabulary gap is a reason to hold a row, never a
reason to reshape it until it fits.

`flood_freeboard_min` is not yet in the `control_type` vocabulary, so the
mechanical gate rejects all 15 until `migrations/071_flood_freeboard_control_type.sql`
is applied. The numbers above come from a dry run that allow-lists the type
in-process; the live CHECK constraint is untouched.

Two results worth stating plainly because they look like gaps and are not:

- **city_of_sydney has no secondary street setback.** Its clause 4.2.3.x says in
  terms that the setback provisions "apply to the primary frontage only". The
  absence is the correct answer, not missing data.
- **parramatta and northern_beaches have no LGA-wide flood freeboard.** Every
  numeric freeboard in their text is precinct- or site-bound. Parramatta's only
  general mentions are "above the 100 year flood level plus freeboard" (no
  number) and "this freeboard of RL 17.0" (a site datum).
