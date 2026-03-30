BEGIN;

-- Migration 010: instrument_registry
-- Unified registry for state planning instruments (SEPP, LEP).
-- DCP chapters stay in dcp_chapter_registry (migration to unified table is v2).

CREATE TABLE IF NOT EXISTS instrument_registry (
    id                  SERIAL PRIMARY KEY,
    instrument_type     TEXT NOT NULL,      -- 'sepp' | 'lep' | 'adg'
    instrument_key      TEXT NOT NULL,      -- stable slug: 'sepp_housing_2021'
    instrument_label    TEXT NOT NULL,      -- human: 'SEPP Housing 2021'
    council             TEXT,               -- NULL for state instruments
    legislation_url     TEXT NOT NULL,      -- https://legislation.nsw.gov.au/view/...
    current_version     TEXT,               -- 'Version 15'
    version_date        TEXT,               -- '15 March 2026'
    content_hash        TEXT,               -- SHA-256 of legislation page HTML
    last_checked        TIMESTAMPTZ,
    last_changed        TIMESTAMPTZ,
    needs_review        BOOLEAN NOT NULL DEFAULT FALSE,
    check_failures      INTEGER NOT NULL DEFAULT 0,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (instrument_key)
);

CREATE INDEX IF NOT EXISTS idx_ir_type     ON instrument_registry (instrument_type);
CREATE INDEX IF NOT EXISTS idx_ir_active   ON instrument_registry (is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_ir_review   ON instrument_registry (needs_review) WHERE needs_review = TRUE;

CREATE OR REPLACE FUNCTION _update_instrument_registry_ts()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_ir_updated_at ON instrument_registry;
CREATE TRIGGER trg_ir_updated_at
    BEFORE UPDATE ON instrument_registry
    FOR EACH ROW EXECUTE FUNCTION _update_instrument_registry_ts();

-- Seed: state instruments relevant to Inner West DAs
INSERT INTO instrument_registry
    (instrument_type, instrument_key, instrument_label, legislation_url, notes)
VALUES
    ('sepp', 'sepp_housing_2021',
     'State Environmental Planning Policy (Housing) 2021',
     'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
     '241 provisions in regulatory_provisions; housing pathways, CDC eligibility, ADG'),

    ('sepp', 'sepp_exempt_complying_2008',
     'State Environmental Planning Policy (Exempt and Complying Development Codes) 2008',
     'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572',
     'CDC and exempt development codes'),

    ('lep', 'inner_west_lep_2022',
     'Inner West Local Environmental Plan 2022',
     'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0457',
     'Zone objectives, local provisions, heritage; zone/height/FSR from Planning Portal spatial API')
ON CONFLICT (instrument_key) DO NOTHING;

COMMIT;
