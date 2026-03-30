BEGIN;

-- Migration 011: instrument_currency
-- Single source of truth for data currency disclosure.
-- One row per (council, instrument_key). Updated by monitors after every run.
-- Read by /api/instrument-currency and rendered in the UI.

CREATE TABLE IF NOT EXISTS instrument_currency (
    id                  SERIAL PRIMARY KEY,
    council             TEXT,               -- NULL for state instruments; council slug for DCP
    instrument_key      TEXT NOT NULL,      -- 'dcp', 'sepp_housing_2021', 'inner_west_lep_2022'
    instrument_label    TEXT NOT NULL,
    instrument_type     TEXT NOT NULL,      -- 'dcp' | 'sepp' | 'lep'
    verified_at         TIMESTAMPTZ,        -- NULL = never verified (shows red in UI)
    version_label       TEXT,               -- 'Version 15 (commenced 15 Mar 2026)'
    source_url          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (council, instrument_key)
);

CREATE INDEX IF NOT EXISTS idx_ic_council ON instrument_currency (council);

CREATE OR REPLACE FUNCTION _update_instrument_currency_ts()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ic_updated_at ON instrument_currency;
CREATE TRIGGER trg_ic_updated_at
    BEFORE UPDATE ON instrument_currency
    FOR EACH ROW EXECUTE FUNCTION _update_instrument_currency_ts();

-- Seed: one row per council DCP + state instruments
-- verified_at starts NULL — turns red in UI until first monitor run confirms currency
INSERT INTO instrument_currency
    (council, instrument_key, instrument_label, instrument_type, source_url)
VALUES
    ('marrickville', 'dcp', 'Marrickville DCP 2011', 'dcp',
     'https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/marrickville-dcp'),
    ('leichhardt', 'dcp', 'Leichhardt DCP 2013', 'dcp',
     'https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/leichhardt-dcp'),
    ('ashfield', 'dcp', 'Ashfield DCP 2016', 'dcp',
     'https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/ashfield-dcp'),
    (NULL, 'sepp_housing_2021',
     'State Environmental Planning Policy (Housing) 2021', 'sepp',
     'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714'),
    (NULL, 'sepp_exempt_complying_2008',
     'State Environmental Planning Policy (Exempt and Complying Development Codes) 2008', 'sepp',
     'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572'),
    (NULL, 'inner_west_lep_2022',
     'Inner West Local Environmental Plan 2022', 'lep',
     'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0191')
ON CONFLICT (council, instrument_key) DO NOTHING;

COMMIT;
