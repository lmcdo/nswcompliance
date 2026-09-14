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
-- figure, e.g. "Average of neighbours' setbacks". The controls tab printed "assessed on merit" for every
-- such row, which is wrong for a rule that is calculated from neighbouring buildings.
--
-- Additive and nullable with no default: existing rows, the running backend and the insert scripts are
-- unaffected until they read or write the columns.

ALTER TABLE dcp_setback_controls
    ADD COLUMN IF NOT EXISTS zones_include text[],
    ADD COLUMN IF NOT EXISTS zones_exclude text[],
    ADD COLUMN IF NOT EXISTS plain_summary text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'dcp_setback_controls_zone_scope_one_side'
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
