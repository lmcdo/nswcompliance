-- 065_structure_labels.sql
--
-- Human ground truth for secondary-structure detection.
--
-- WHY THIS EXISTS
-- ---------------
-- Detection recall -- how often the imagery scan misses a structure that is
-- really there -- has never been measured, and cannot be measured from stored
-- data. No source of truth exists: the only record of what stands on a block
-- is the imagery, and reading imagery is a human act.
--
-- The previous attempt failed in a specific, documented way. A "confirmations"
-- figure of 13 of 16 turned out to contain ZERO human input: the frontend
-- defaulted the confirmed count to the machine's own count, so the machine was
-- compared against itself and could not disagree. Any table holding ground
-- truth has to make that failure structurally impossible, not merely
-- discouraged.
--
-- HOW THIS TABLE PREVENTS IT
-- --------------------------
-- 1. There is NO column for detector output. Not the count, not the boxes, not
--    the confidence. A label row cannot be pre-filled from a detection because
--    there is nowhere to put one. The comparison happens later, in a script,
--    joining on tile_sha256.
-- 2. `labels` has no default. The sampling pass inserts status='pending' with
--    labels NULL; only a human write sets labels and labelled_at together, and
--    the CHECK below refuses any other combination.
-- 3. `tile_sha256` pins the exact image the human saw. If the detector ran
--    against a different tile the join finds nothing and the comparison
--    refuses, rather than silently comparing two different pictures.
-- 4. `sample_seed` + `sample_method` make the sample reproducible and, more to
--    the point, auditable: a reader can confirm the blocks were chosen before
--    anyone looked at them rather than cherry-picked afterwards.
--
-- WHAT A ROW MEANS
-- ----------------
-- One row = one lot, one aerial tile, one human reading of it. `labels` holds
-- every structure the human could see, in the SAME bbox_pixel coordinate space
-- the detector uses, so the two are directly comparable. An empty array is a
-- real answer ("I looked, there is nothing"), which is why it must stay
-- distinguishable from "not yet looked at" -- hence `status`.

CREATE TABLE IF NOT EXISTS structure_labels (
    id               BIGSERIAL PRIMARY KEY,

    -- Which sampling run produced this row, and how. Lets a second independent
    -- sample be drawn later without mixing the two.
    sample_id        TEXT        NOT NULL,
    sample_seed      BIGINT      NOT NULL,
    sample_method    TEXT        NOT NULL,

    -- The lot.
    address          TEXT        NOT NULL,
    lat              DOUBLE PRECISION NOT NULL,
    lng              DOUBLE PRECISION NOT NULL,
    lotidstring      TEXT,
    lga_name         TEXT,
    zone_code        TEXT,
    lot_area_m2      DOUBLE PRECISION,

    -- WHAT THE HUMAN SAW.
    -- tile_sha256 hashes the exact stitched image rendered to the labeller,
    -- computed by the UI at display time. It is evidence of what was on screen.
    --
    -- It is NOT the join key, and pretending otherwise would be the defect this
    -- table exists to prevent. Measured 2026-08-08: the detector stores no tile
    -- hash on any row, and a live scan found ZERO stored rows carrying the
    -- aerial_tile block at all. Joining on it would silently match nothing
    -- while looking like it worked. The comparison therefore joins on the
    -- DETERMINISTIC identity below, which both sides derive from lat/lng, and
    -- the recall script reports pixel equality as UNPROVEN until the detector
    -- records a hash too.
    tile_sha256      TEXT,
    tile_width       INTEGER,
    tile_height      INTEGER,
    tile_licence     TEXT,

    -- Deterministic tile identity: the same lat/lng at the same zoom and grid
    -- always resolves to the same centre tile, so this is comparable across
    -- runs without hashing bytes. Mirrors services/nsw_imagery._tile_meta.
    tile_zoom        INTEGER,
    tile_grid        INTEGER,
    tile_centre_x    INTEGER,
    tile_centre_y    INTEGER,

    -- pending  = sampled, nobody has looked yet
    -- labelled = a human recorded an answer (including "nothing here")
    -- skipped  = a human looked and could not judge (cloud, shadow, tile fail)
    status           TEXT        NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'labelled', 'skipped')),

    -- [{bbox_pixel:[x0,y0,x1,y1], structure_type, is_main_dwelling}, ...]
    -- Empty array is a valid, meaningful answer. NULL means not yet answered.
    labels           JSONB,

    -- Required when status='skipped' (see CHECK).
    skip_reason      TEXT,

    labelled_by      TEXT,
    labelled_at      TIMESTAMPTZ,
    -- Wall-clock seconds spent on this tile. A row answered in under a second
    -- is a click-through, not a reading, and should be visible in the analysis.
    seconds_spent    INTEGER,

    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One label per lot per sample. Re-running the sampler is idempotent.
CREATE UNIQUE INDEX IF NOT EXISTS structure_labels_sample_lot_uniq
    ON structure_labels (sample_id, address);

CREATE INDEX IF NOT EXISTS structure_labels_status_idx
    ON structure_labels (sample_id, status);

CREATE INDEX IF NOT EXISTS structure_labels_tile_idx
    ON structure_labels (tile_sha256);

-- A finished row must carry the evidence that a person finished it. This is
-- the database-level version of the guard the confirm flow did not have.
ALTER TABLE structure_labels
    DROP CONSTRAINT IF EXISTS structure_labels_answered_completely;
ALTER TABLE structure_labels
    ADD CONSTRAINT structure_labels_answered_completely CHECK (
        (status = 'pending'  AND labels IS NULL AND labelled_at IS NULL)
     OR (status = 'labelled' AND labels IS NOT NULL AND labelled_at IS NOT NULL
                             AND labelled_by IS NOT NULL)
     OR (status = 'skipped'  AND skip_reason IS NOT NULL AND labelled_at IS NOT NULL
                             AND labelled_by IS NOT NULL)
    );

COMMENT ON TABLE structure_labels IS
 'Human ground truth for secondary-structure detection. Deliberately holds NO detector output: recall is computed by a separate script joining on tile_sha256, so a label can never be pre-filled from the thing it exists to test. Origin: the 13-of-16 "confirmations" that contained zero human input.';

COMMENT ON COLUMN structure_labels.labels IS
 'Every structure the human could see, in the detector''s own bbox_pixel coordinate space. An empty array means "looked, nothing there" and is a real answer; NULL means not yet answered.';

COMMENT ON COLUMN structure_labels.tile_sha256 IS
 'Hash of the exact image shown to the labeller. The recall script joins on this so it cannot compare a human reading of one picture against a machine reading of another.';

COMMENT ON COLUMN structure_labels.seconds_spent IS
 'Wall-clock seconds on the tile. Kept so that implausibly fast answers are visible in the analysis rather than silently weighted the same as considered ones.';
