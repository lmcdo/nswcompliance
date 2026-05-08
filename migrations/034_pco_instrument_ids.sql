BEGIN;

-- Migration 034: Add PCO instrument IDs + AustLII fallback URLs
-- Enables legislation_monitor.py to use PCO XML export as primary source
-- and AustLII as degraded fallback.

ALTER TABLE instrument_registry
  ADD COLUMN IF NOT EXISTS pco_instrument_id TEXT,
  ADD COLUMN IF NOT EXISTS austlii_url TEXT;

-- Seed PCO IDs (from legislation.nsw.gov.au URL paths)
UPDATE instrument_registry SET pco_instrument_id = 'epi-2021-0714'
  WHERE instrument_key = 'sepp_housing_2021';
UPDATE instrument_registry SET pco_instrument_id = 'epi-2008-0572'
  WHERE instrument_key = 'sepp_exempt_complying_2008';
UPDATE instrument_registry SET pco_instrument_id = 'epi-2022-0457'
  WHERE instrument_key = 'inner_west_lep_2022';

-- Move AustLII URLs from hardcoded dict to DB (fallback source)
UPDATE instrument_registry SET austlii_url = 'https://classic.austlii.edu.au/au/legis/nsw/consol_reg/sepp2021448/'
  WHERE instrument_key = 'sepp_housing_2021';
UPDATE instrument_registry SET austlii_url = 'https://classic.austlii.edu.au/au/legis/nsw/consol_reg/seppacdc2008721/'
  WHERE instrument_key = 'sepp_exempt_complying_2008';

COMMIT;
