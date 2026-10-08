-- Secondary dwelling (granny flat) rules by approval path — STEP 1 OF 2: columns only.
--
-- Adds the columns that per-clause, per-path rules need. No rows change, so every
-- current reader is unaffected. Step 2 (084) inserts the rules; it must only be
-- applied after the code that makes the generic readers skip path-specific rows
-- (scripts/conveyancing_db.py fetch_sepp_housing_standards and
-- services/housing_sepp_eligibility.py _fetch_standards_grouped: approval_pathway IS NULL)
-- is deployed. Applied in the other order, the conveyancing loader crashes on
-- float(None) and the brief shows bare band thresholds as "additional standards".

ALTER TABLE housing_sepp_standards
  ADD COLUMN IF NOT EXISTS approval_pathway text,
  ADD COLUMN IF NOT EXISTS source_quote text,
  ADD COLUMN IF NOT EXISTS lot_area_min_m2 numeric,
  ADD COLUMN IF NOT EXISTS lot_area_min_inclusive boolean,
  ADD COLUMN IF NOT EXISTS lot_area_max_m2 numeric;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'housing_sepp_standards_approval_pathway_check') THEN
    ALTER TABLE housing_sepp_standards
      ADD CONSTRAINT housing_sepp_standards_approval_pathway_check
      CHECK (approval_pathway IS NULL OR approval_pathway IN ('cdc', 'da'));
  END IF;
END $$;
