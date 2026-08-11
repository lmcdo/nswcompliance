-- 054 — add `secondary_street_setback` to the control_type vocabulary.
--
-- WHY
-- ---
-- DQ-40 found 31 controls whose control_type contradicts their own source_text,
-- 28 of them served. Sixteen are one cause, not sixteen mistakes: the enforced
-- vocabulary (constraint `control_type_canonical`) has no type for a
-- SECONDARY-STREET setback — the corner-lot control that nearly every NSW
-- residential DCP prescribes alongside the primary street setback.
--
-- With nowhere to file it, extractors used `front_setback` and qualified it in
-- `condition`. The values are correct and the conditions are candid; the label is
-- wrong. So a corner-lot 2-4 m setback sits in the same bucket as the primary
-- 4.5-6 m one, and any consumer reading control_type without reading condition
-- sees them as the same kind of control.
--
-- The fix is a vocabulary addition. Re-filing the 16 rows is a separate scripted
-- step, so the schema change and the data move can be reviewed and rolled back
-- independently of each other.
--
-- WHAT THIS DOES NOT DO
-- ---------------------
-- Nothing is re-typed here. Adding a permitted value cannot invalidate an
-- existing row, so this is safe to apply on its own and leaves every row exactly
-- as it found it. All 21 existing values are carried forward verbatim — 15 are
-- in use, and dropping any would orphan live rows.
--
-- Verify after applying:
--   SELECT pg_get_constraintdef(oid) FROM pg_constraint
--    WHERE conname = 'control_type_canonical';
--   -- expect 'secondary_street_setback' present AND every prior value retained.

BEGIN;

-- Currency scope: a CHECK constraint governs every row, current and superseded
-- alike, so no is_current filter applies here — DDL has no WHERE clause, and
-- scoping a vocabulary to served rows would let retired rows hold invalid types.
ALTER TABLE dcp_setback_controls
  DROP CONSTRAINT IF EXISTS control_type_canonical;

ALTER TABLE dcp_setback_controls
  ADD CONSTRAINT control_type_canonical CHECK (
    control_type = ANY (ARRAY[
      'front_setback',
      -- NEW: the setback to a secondary street on a corner lot. Distinct from
      -- front_setback because it is a different requirement with a different
      -- value, and from side_setback because the boundary faces a road.
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
      'solar_access_hours'
    ])
  );

COMMIT;
