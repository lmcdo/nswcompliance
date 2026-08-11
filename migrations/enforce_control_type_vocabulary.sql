-- Enforce the canonical control_type vocabulary on dcp_setback_controls.
--
-- Source of truth: enrichment/config/control_type_vocabulary.py
-- (CANONICAL_CONTROL_TYPES). This constraint is the writer-agnostic guarantee:
-- any INSERT/UPDATE with a non-canonical control_type fails loudly instead of
-- drifting silently (which previously hid controls from the capacity engine and
-- mis-grouped them in the UI).
--
-- Applied to production 2026-07-15. All existing rows conform (verified: the 15
-- distinct control_type values in the table are all in this list).
--
-- To ADD a new control_type: add it to CANONICAL_CONTROL_TYPES in the Python
-- vocabulary (and MAXIMUM_CONTROL_TYPES if it is a ceiling), then extend the IN
-- list below via a new migration. test_control_type_vocabulary.py asserts this
-- list and the Python set stay in sync.
--
-- Reversal: ALTER TABLE dcp_setback_controls DROP CONSTRAINT control_type_canonical;

ALTER TABLE dcp_setback_controls
    DROP CONSTRAINT IF EXISTS control_type_canonical;

ALTER TABLE dcp_setback_controls
    ADD CONSTRAINT control_type_canonical CHECK (
        control_type IN (
            'front_setback',
            -- Corner-lot setback to the secondary street; added by migration
            -- 054 (applied 2026-08-02) after DQ-40 found the vocabulary had
            -- nowhere to file it, so extractors used front_setback.
            'secondary_street_setback',
            'side_setback',
            'rear_setback',
            'separation_from_dwelling',
            'car_parking',
            'bicycle_parking',
            'driveway_width',
            'driveway_gradient',
            'max_site_coverage',
            'max_height',
            'max_floor_area',
            'landscaping_min',
            'front_setback_landscaping',
            'deep_soil_min',
            'tree_canopy_min',
            'communal_open_space_min',
            'private_open_space',
            'solar_access_hours',
            'privacy_separation',
            'fencing_height_max',
            'dwelling_size_min'
        )
    );
