# Woollahra precinct keying — "C1/C2/C3" is a THREE-WAY collision (2026-07-29)

Written by the precinct-integrity session (CoS/Ashfield/Leichhardt/KG lane) for the
Woollahra deepening session, from a **read-only** live-DB check. Nothing written to
`dcp_precinct_boundaries` or Woollahra provisions by this session.

## Verdict: real trap, NOT yet live

- **Woollahra provisions: 0 have `v2_precinct_id`** (all NULL) → the ~2,100 HCA rows
  (C1 Paddington 554, C2 Woollahra 587, C3 Watsons Bay 964, B2 neighbourhood 165)
  are served **council-wide** today = plain over-inclusion, same class as CoS/Ashfield
  pre-fix. The warning banner (#842 logic) covers it for now.
- **`dcp_precinct_boundaries`: 0 Woollahra rows.** Nothing loaded.
- ∴ No address can be mis-matched by C-number yet — there is neither a key nor a
  polygon to match. The collision is a **landmine in the pending write plan**, not a
  live production bug.

## The token "C1" means THREE different things in this council's data

1. **DCP chapter id** — C1 = Paddington HCA, C2 = Woollahra HCA, C3 = Watsons Bay HCA
   (provision refs literally read `C1 C10`, etc.).
2. **LEP heritage H_ID** C1/C2/C3 — *different geographic areas* (flagged by the
   Woollahra boundary agent). Join heritage geometry by **name**, never by H_ID number.
3. **NSW Standard-Instrument ZONE code** — `spatial_overlays` has `layer_type='zone'`
   `value='C1'` (×4) and `'C2'` (×1) for Woollahra (environmental-conservation zones).
   This is the collision the boundary agent did **not** flag.

## Safe design (applies to BOTH sides of the join)

- Key the boundary's `precinct_id` **and** the provision's `v2_precinct_id` off the HCA
  **NAME** (`Paddington` / `Woollahra` / `Watsons Bay`), not the bare `C1/C2/C3`.
- Never let a bare single-letter+number token from a zone or LEP layer become a
  `precinct_id`. A name-keyed join has no collision; a C-number join silently serves
  the wrong area — the exact bug class fixed for CoS/Ashfield/KG this session.
- `dcp_precinct_boundaries.lga` for Woollahra should read `Woollahra` (match the
  serving code's `LOWER(lga)=LOWER($lga)` — see precinct-service.ts), and the same
  name must appear on the provision key so the two halves meet.

## General lesson worth carrying to Parramatta and beyond

Single-letter/short precinct tokens collide with NSW zone codes (C1/C2/C3/E1/E2/R1…,
RE1/RE2, B1…) and LEP H_IDs. **Precinct keys must be names or name-qualified, never a
bare zone/H_ID-shaped token.**

## Coordination

- This session's in-flight DB writes (KG Part 14 commit, Marrickville re-extraction,
  semantic-sweep fixes) touch NONE of Woollahra/Parramatta — no row collision.
- Woollahra was NOT in this session's semantic fidelity sweep (scoped to
  CoS/Ashfield/Leichhardt). Once its keying lands, run the same page-vs-rows semantic
  sweep before claiming it verified.
- **Woollahra is a completely BLANK precinct slate** (verified read-only 2026-07-29):
  `v2_precinct_id` all NULL, `dcp_precinct_boundaries` 0 rows, `dcp_precinct_requirements`
  0 rows, `dcp_precinct_localities` 0 Woollahra rows, `heritage_precinct_mapping` table
  does not exist. No lurking C-keyed entry anywhere — the write plan is the ONLY place
  the collision can be introduced, so getting the key model right up front fully avoids it.
