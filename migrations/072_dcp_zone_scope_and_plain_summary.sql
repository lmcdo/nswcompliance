-- 072: explicit zone scope and a plain-English summary on dcp_setback_controls.
--
-- WHY
-- ---
-- The served zone filter (scripts/conveyancing_db.zone_row_applies) can only read zone scope from a
-- control's free-text condition. It reads a named zone as "this zone only", and since PR #1105 it no
-- longer guesses exclusions: a row written "zones other than R2" is served to every zone. So a Strathfield
-- R2 site was shown its R2 setbacks and also the ones the plan sets for every other zone. Explicit columns
-- end the guessing:
--   zones_include  the control applies only to these zone codes, e.g. {R2}
--   zones_exclude  the control applies to every zone except these, e.g. {R2}
-- At most one of the two is set. When both are NULL the text rule applies exactly as before.
--
-- plain_summary: short plain-English wording shown in place of a number where the plan sets no fixed
-- figure, e.g. "Worked out from neighbours' setbacks". The controls tab printed "assessed on merit" for every
-- such row, which is wrong for a rule that is calculated from neighbouring buildings.
--
-- Additive and nullable with no default: existing rows, the running backend and the insert scripts are
-- unaffected until they read or write the columns. Re-running this file changes nothing.

ALTER TABLE dcp_setback_controls
    ADD COLUMN IF NOT EXISTS zones_include text[],
    ADD COLUMN IF NOT EXISTS zones_exclude text[],
    ADD COLUMN IF NOT EXISTS plain_summary text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'dcp_setback_controls_zone_scope_one_side'
           AND conrelid = 'dcp_setback_controls'::regclass
    ) THEN
        ALTER TABLE dcp_setback_controls
            ADD CONSTRAINT dcp_setback_controls_zone_scope_one_side
            CHECK (zones_include IS NULL OR zones_exclude IS NULL);
    END IF;
END $$;

COMMENT ON COLUMN dcp_setback_controls.zones_include IS
    'Zone codes this control applies to (e.g. {R2}); NULL = scope read from the condition text.';
COMMENT ON COLUMN dcp_setback_controls.zones_exclude IS
    'Zone codes this control does not apply to; it applies to every other zone. NULL = none.';
COMMENT ON COLUMN dcp_setback_controls.plain_summary IS
    'Plain-English wording shown where the control sets no fixed number.';

-- BACKFILL
-- --------
-- The rows whose scope and wording are known: Strathfield General Residential DCP 2026, inserted by
-- scripts/insert_strathfield_general_residential.py (clauses C3.6.1/C3.6.2 rear and C3.4.2 side setbacks name
-- the R2 zone and "any other zone"; C3.1.1 front setback is an average of the neighbouring dwellings). A
-- database that gains the columns from this file alone - a restore or staging copy holding those rows - must
-- not serve both the R2 and the other-zones figures to an R2 site. Each UPDATE touches only rows with nothing
-- stored yet. tests/test_insert_strathfield_general_residential.py checks these rows equal the script's ROWS.

UPDATE dcp_setback_controls SET zones_include = ARRAY['R2']::text[]
 WHERE lga = 'strathfield' AND source_chapter_key = 'general-residential-dcp-2026'
   AND zones_include IS NULL AND zones_exclude IS NULL
   AND control_type IN ('rear_setback', 'side_setback')
   AND (section_ref, value_min) IN (('general-residential-dcp-2026#C3.6.1', 6),
                                    ('general-residential-dcp-2026#C3.4.2', 5),
                                    ('general-residential-dcp-2026#C3.4.2', 3));

UPDATE dcp_setback_controls SET zones_exclude = ARRAY['R2']::text[]
 WHERE lga = 'strathfield' AND source_chapter_key = 'general-residential-dcp-2026'
   AND zones_include IS NULL AND zones_exclude IS NULL
   AND control_type IN ('rear_setback', 'side_setback')
   AND (section_ref, value_min) IN (('general-residential-dcp-2026#C3.6.2', 6),
                                    ('general-residential-dcp-2026#C3.4.2', 4),
                                    ('general-residential-dcp-2026#C3.4.2', 2));

UPDATE dcp_setback_controls SET plain_summary = 'Worked out from neighbours'' setbacks'
 WHERE lga = 'strathfield' AND source_chapter_key = 'general-residential-dcp-2026'
   AND plain_summary IS NULL
   AND control_type = 'front_setback' AND section_ref = 'general-residential-dcp-2026#C3.1.1'
   AND value_min IS NULL AND value_max IS NULL;
