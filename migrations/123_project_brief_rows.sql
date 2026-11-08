-- 123_project_brief_rows.sql
-- prior-art-checked: no table holds precomputed "best plan clauses" per (council, project type, rule type).
--   dcp_setback_controls holds only PROVEN numeric controls (295 verbatim rows, 19% of the council x project x rule cells);
--   regulatory_provisions holds the clauses. This DERIVED table only points at clauses by id: it never copies text,
--   so the quote, page and citation proof still come from regulatory_provisions at read time.
--
-- NOT APPLIED. Applying it and loading it are production writes and need the owner's go (scripts/load_project_brief.py, dry-run by default).
CREATE TABLE IF NOT EXISTS project_brief_rows (
  id            bigserial PRIMARY KEY,
  council       text      NOT NULL,                       -- regulatory_provisions.source_council
  zone_group    text      NOT NULL CHECK (zone_group IN ('R2','R3','R4','B','ANY')),
  dev_type      text      NOT NULL,                       -- dwelling_house, dual_occupancy, secondary_dwelling, multi_dwelling_housing, residential_flat_building, shop_top_housing
  row_type      text      NOT NULL,                       -- front_setback, side_setback, rear_setback, secondary_street_setback, car_parking, landscaping_min, deep_soil_min, private_open_space, max_site_coverage, max_height
  rank          smallint  NOT NULL CHECK (rank BETWEEN 1 AND 5),
  provision_id  integer   NOT NULL REFERENCES regulatory_provisions(id) ON DELETE CASCADE,   -- CASCADE: several repo scripts hard-delete provisions; a plain FK would block them (and the data-repair session)
  verdict       text      NOT NULL CHECK (verdict IN ('APPLIES','MIGHT')),
  reason        text,
  build_id      text      NOT NULL,                       -- one value per load, so a bad load can be removed by build_id
  built_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (council, zone_group, dev_type, row_type, rank)
);
CREATE INDEX IF NOT EXISTS project_brief_rows_lookup ON project_brief_rows (council, dev_type, zone_group);
-- Same as dcp_setback_controls, dcp_review_queue and regulatory_provisions: RLS on, no policy, so the public (anon) API sees nothing;
-- the app reads through its own database connection.
ALTER TABLE project_brief_rows ENABLE ROW LEVEL SECURITY;
COMMENT ON TABLE project_brief_rows IS 'Derived. Which regulatory_provisions rows to show first for (council, zone group, project type, rule type). Built offline by the applies-when pipeline; nothing here is hand-typed.';
