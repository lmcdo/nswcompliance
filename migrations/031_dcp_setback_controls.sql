-- Migration 031: DCP secondary dwelling setback controls
-- Stores extracted setback/height/area controls from council DCPs.
-- Populated by enrichment/extractors/extract_secondary_setbacks_*.py scripts.

CREATE TABLE IF NOT EXISTS dcp_setback_controls (
  id            serial PRIMARY KEY,
  provision_id  integer REFERENCES regulatory_provisions(id),
  lga           text NOT NULL,
  dev_type      text NOT NULL DEFAULT 'secondary_dwelling',
  -- control_type enum:
  --   rear_setback | side_setback | front_setback | height_max | height_storeys_max
  --   separation_from_dwelling | floor_area_max | site_coverage_max
  --   landscaping_min | private_open_space | car_parking
  control_type  text NOT NULL,
  value_min     numeric,
  value_max     numeric,
  unit          text,           -- 'm' | 'storeys' | 'm2' | '%'
  condition     text,           -- qualifier e.g. "detached only", "wall height > 3.8m"
  -- applicability:
  --   'secondary_dwelling_specific'  — chapter/section is dedicated to secondary dwellings
  --   'universal_residential'        — universal residential controls that apply to secondary dwellings too
  applicability text NOT NULL CHECK (applicability IN ('secondary_dwelling_specific', 'universal_residential')),
  source_text   text,           -- ≤250 char snippet from provision_text for citation
  section_ref   text,           -- ref_number value for display citation
  created_at    timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS dcp_setback_controls_lga_devtype
  ON dcp_setback_controls(lga, dev_type);

COMMENT ON TABLE dcp_setback_controls IS
  'Extracted DCP setback, height, and area controls for secondary dwellings. '
  'Populated by enrichment/extractors/extract_secondary_setbacks_*.py. '
  'NULL value_min/value_max = extraction uncertain — surface "check with council" in UI.';

COMMENT ON COLUMN dcp_setback_controls.applicability IS
  'secondary_dwelling_specific: provision is from a chapter dedicated to secondary dwellings. '
  'universal_residential: universal residential controls that also apply to secondary dwellings.';
