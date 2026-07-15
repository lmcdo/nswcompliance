-- Normalize variant DCP control_type slugs to canonical.
-- Applied to production 2026-07-15 (38 rows, backed up, zero collisions verified);
-- recorded here for audit + reproducibility. Label-only change — no values altered.
--
-- Root cause: there is no shared control_type vocabulary, so one-off per-council
-- insert scripts drifted:
--   * landscaped_area_min  (7 councils, 36 rows)  === landscaping_min
--   * communal_open_space  (penrith, 2 rows)      === communal_open_space_min
-- The variant slugs were invisible to the capacity route (frontend-nextjs
-- .../api/capacity/calculate #719), to constraint_arithmetic.py (line ~490,
-- reads 'landscaping_min'), and were grouped under "Other" with a raw-slug
-- label in the DCP structured-controls display. Normalizing fixes every
-- consumer at once.
--
-- Canonical landscaping / open-space vocabulary (writers must use these):
--   landscaping_min            minimum landscaped area (%)
--   deep_soil_min              minimum deep soil zone
--   tree_canopy_min            tree canopy coverage
--   communal_open_space_min    minimum communal open space
--   private_open_space         minimum private open space
--   front_setback_landscaping  DISTINCT concept (landscaping within the front
--                              setback) — intentionally NOT merged.
--
-- Idempotent: re-running is a no-op once the variants are gone.

UPDATE dcp_setback_controls
   SET control_type = 'landscaping_min'
 WHERE control_type = 'landscaped_area_min';

UPDATE dcp_setback_controls
   SET control_type = 'communal_open_space_min'
 WHERE control_type = 'communal_open_space';
