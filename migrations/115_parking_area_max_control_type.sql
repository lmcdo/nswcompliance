-- 115: add `parking_area_max` to the control_type vocabulary.
--
-- WHAT THE CONTROL IS
-- -------------------
-- A ceiling on the FLOOR AREA of parking (garage / carport / undercover area), in m2.
-- It is not a number of spaces. Area beyond the cap counts as gross floor area.
--
-- WHY A NEW TYPE, NOT car_parking
-- -------------------------------
-- Every car_parking reader treats value_min as SPACES:
--   frontend-nextjs/app/api/tod/parking-rates/route.ts   (semantic_type === 'car_parking')
--   frontend-nextjs/app/api/capacity/calculate/route.ts  (PARKING_TYPES allowlist)
--   services/constraint_arithmetic.py                    (_get_dcp_value(..., "car_parking", ...))
-- Campbelltown 3.6.1.4 (rows 254/255) was stored as car_parking 1 and 2 spaces/dwelling,
-- numbers the clause never states; the clause caps the AREA at 18 m2 / 36 m2. The rows
-- were held (needs_review) rather than served wrong. All three readers use explicit
-- allowlists, so a separate type is ignored by every spaces calculation.
--
-- THE EVIDENCE (measured 2026-10-19, current council words in regulatory_provisions)
-- --------------------------------------------------------------------------------
-- Clauses that cap a parking AREA with a figure:
--   campbelltown  3.6.1.4 a) i)/ii)  18 m2 (1-2 bedrooms) / 36 m2 (3+ bedrooms), p21
--   ku_ring_gai   L315 dwelling houses  "required car parking area is to be no greater than 31sqm"
--   ku_ring_gai   L451 dual occupancy   "... no greater than 31sqm per dwelling"
-- Read and excluded as not area caps: spaces-per-GFA rates (parramatta, wollongong,
-- woollahra), basement area (georges_river 6.1.2), all outbuildings 55sqm (campbelltown
-- 3.5.2.2), SEPP exempt-development carport sizes (state law, not a DCP control).
--
-- enrichment/config/control_type_vocabulary.py is edited in the same change;
-- tests/test_control_vocabulary_matches_db.py fails if the two disagree.
-- 071 flood_freeboard_min is still NOT applied and is deliberately not included here.

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
        'parking_area_max'
    ]));

COMMIT;
