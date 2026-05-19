-- Migration 043: Create lga_registry table
-- Single source of truth for valid LGA slugs.
-- Enforces referential integrity on dcp_setback_controls.lga via FK.
-- Also used by /api/dcp/coverage endpoint for display names.

CREATE TABLE IF NOT EXISTS lga_registry (
  slug TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  parent_lga TEXT REFERENCES lga_registry(slug),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Populate with all LGAs currently in dcp_setback_controls
-- Parent LGAs first (no parent_lga reference)
INSERT INTO lga_registry (slug, display_name) VALUES
  ('inner_west',            'Inner West'),
  ('bayside',               'Bayside'),
  ('blacktown',             'Blacktown'),
  ('burwood',               'Burwood'),
  ('camden',                'Camden'),
  ('campbelltown',          'Campbelltown'),
  ('canada_bay',            'Canada Bay'),
  ('canterbury_bankstown',  'Canterbury-Bankstown'),
  ('city_of_sydney',        'City of Sydney'),
  ('cumberland',            'Cumberland'),
  ('fairfield',             'Fairfield'),
  ('georges_river',         'Georges River'),
  ('hornsby',               'Hornsby'),
  ('ku_ring_gai',           'Ku-ring-gai'),
  ('liverpool',             'Liverpool'),
  ('northern_beaches',      'Northern Beaches'),
  ('parramatta',            'Parramatta'),
  ('penrith',               'Penrith'),
  ('randwick',              'Randwick'),
  ('ryde',                  'Ryde'),
  ('strathfield',           'Strathfield'),
  ('sutherland_shire',      'Sutherland Shire'),
  ('the_hills',             'The Hills Shire'),
  ('waverley',              'Waverley'),
  ('woollahra',             'Woollahra'),
  ('nsw_statewide',         'NSW Statewide')
ON CONFLICT (slug) DO NOTHING;

-- Inner West sub-councils (have parent_lga)
INSERT INTO lga_registry (slug, display_name, parent_lga) VALUES
  ('ashfield',    'Ashfield',    'inner_west'),
  ('leichhardt',  'Leichhardt',  'inner_west'),
  ('marrickville','Marrickville','inner_west')
ON CONFLICT (slug) DO NOTHING;

-- Add FK constraint on dcp_setback_controls.lga
ALTER TABLE dcp_setback_controls
  ADD CONSTRAINT fk_dcp_setback_lga FOREIGN KEY (lga) REFERENCES lga_registry(slug);

-- Index for coverage queries
CREATE INDEX IF NOT EXISTS idx_lga_registry_active ON lga_registry (is_active) WHERE is_active = TRUE;
