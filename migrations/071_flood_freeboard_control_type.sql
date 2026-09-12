-- 071: add `flood_freeboard_min` to the control_type vocabulary.
--
-- NOT YET APPLIED. Extending a CHECK constraint on a live table is a deliberate
-- act, not a side effect of an extraction run, so this file exists and the
-- constraint does not yet name the type. Until it is applied,
-- scripts/dcp_verify_extracted_controls.py rejects every flood_freeboard_min
-- proposal with "not in the vocabulary" -- which is the gate working, not a bug.
--
-- WHAT THE CONTROL IS
-- -------------------
-- The FREEBOARD: the height a floor level (normally of habitable rooms) must sit
-- above a mapped flood level. Stated LGA-wide, unlike the flood planning level
-- itself, which is a per-property datum read off a flood map.
--
-- WHY NOT `flood_planning_level`
-- ------------------------------
-- That was the original plan and reading the documents refuted it. Across 24
-- candidate passages, DCP mentions of an FPL are overwhelmingly (a)
-- cross-references to a separate floodplain policy with no number, (b) absolute
-- site datums -- parramatta states "this freeboard of RL 17.0" for one creek --
-- or (c) event labels such as "1% AEP" and "1 in 100 year", which name the event
-- a control is measured against and are not controls. The freeboard is the part
-- that is both numeric and general.
--
-- THE EVIDENCE FOR SPENDING A MIGRATION ON IT (measured 2026-09-12)
-- -----------------------------------------------------------------
-- 35 candidate passages across 8 of the 17 councils whose DCP text is extracted.
-- A model proposed 15 rows; all 15 passed the verbatim-quote and
-- number-in-quote checks; reading them cleared 5 rows across 4 councils:
--
--   ashfield              0.5m  above the 1% AEP flood level          C3.1 DS2.1
--   canterbury_bankstown  0.5m  above the 1-in-100-year flood level   9.8
--   ku_ring_gai           300mm above the design flood standard       24D.3(3)
--   ku_ring_gai           500mm above the design flood standard       24D.3(4)
--   marrickville          500mm above the 1% AEP flood level          C5
--
-- The other 10 stopped: 2 duplicates of an already-captured figure, 8 rejected
-- for scope (named lots, one precinct, a city centre), for advisory "should"
-- wording, or -- georges_river -- for being measured above the PROBABLE MAXIMUM
-- FLOOD rather than the 1% AEP, which is not the same control in the same column.
--
-- 4 LGAs is in band with tree_canopy_min (3) and communal_open_space_min (3) and
-- below max_height (5). It is a real capability, not a broad new layer, and
-- parramatta and northern_beaches end with nothing -- correctly: neither states
-- an LGA-wide freeboard figure anywhere in its extracted text.
--
-- TWO THINGS TO SETTLE BEFORE APPLYING
-- ------------------------------------
-- 1. UNIT. These rows are stored in the document's own unit, so the set mixes
--    `m` (0.5) and `mm` (500). `mm` is NOT currently a value of
--    dcp_setback_controls.unit. Sorting or comparing value_min across councils
--    without respecting unit would rank 500mm above 0.5m. Either whatever renders
--    these handles `mm`, or the rows are stored in metres with the document's own
--    figure kept in the condition -- but note that converting 500mm to 0.5 takes
--    value_min out of its own quote, which is precisely what the pre-insert
--    verifier refuses. Storing the document's unit is the option consistent with
--    the rest of the table (which already carries %, m2 and hours).
-- 2. DATUM. A freeboard is meaningless without what it is measured above. Every
--    cleared row records that in `condition` (1% AEP, 1-in-100-year, design flood
--    standard). A consumer that shows the number without the datum shows a number
--    nobody can act on.
--
-- APPLYING THIS IS THREE EDITS, NOT ONE
-- -------------------------------------
--   (a) this constraint;
--   (b) enrichment/config/control_type_vocabulary.py CANONICAL_CONTROL_TYPES --
--       the declared single source of truth, which the verifier imports;
--   (c) frontend-nextjs/app/api/dcp/structured-controls/route.ts, both the
--       category map (~line 86) and the label map (~line 113).
-- tests/test_control_vocabulary_matches_db.py fails until (a) and (b) agree, so
-- doing one without the other is caught rather than discovered.

BEGIN;

ALTER TABLE dcp_setback_controls
    DROP CONSTRAINT IF EXISTS control_type_canonical;

ALTER TABLE dcp_setback_controls
    ADD CONSTRAINT control_type_canonical CHECK (control_type = ANY (ARRAY[
        'front_setback',
        'secondary_street_setback',
        'side_setback',
        'rear_setback',
        'separation_from_dwelling',
        'privacy_separation',
        'car_parking',
        'bicycle_parking',
        'driveway_width',
        'driveway_gradient',
        'max_site_coverage',
        'max_height',
        'max_floor_area',
        'dwelling_size_min',
        'fencing_height_max',
        'landscaping_min',
        'front_setback_landscaping',
        'deep_soil_min',
        'tree_canopy_min',
        'communal_open_space_min',
        'private_open_space',
        'solar_access_hours',
        'flood_freeboard_min'
    ]));

-- Verify before committing: this must return the 23 slugs above, and every
-- existing row must still satisfy the constraint (ADD CONSTRAINT validates
-- existing rows, so a failure here means an out-of-vocabulary row already exists
-- and must be reconciled first rather than the constraint widened to admit it).
-- SELECT pg_get_constraintdef(oid) FROM pg_constraint
--  WHERE conname = 'control_type_canonical';

COMMIT;
