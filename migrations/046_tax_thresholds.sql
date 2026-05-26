-- Migration 046: Create tax_thresholds table
-- Replaces hardcoded LT_YEAR, LT_THRESHOLD, LT_RATE, LT_BASE in
-- scripts/generate_conveyancing_report.py (lines 199-202).
--
-- Source: revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/land-tax-thresholds
-- Update: add a new row each June when Revenue NSW publishes next year's thresholds.

BEGIN;

CREATE TABLE IF NOT EXISTS tax_thresholds (
    id SERIAL PRIMARY KEY,
    jurisdiction VARCHAR(10) NOT NULL DEFAULT 'NSW',
    tax_type VARCHAR(30) NOT NULL DEFAULT 'land_tax',
    tax_year INTEGER NOT NULL,
    threshold_dollars INTEGER NOT NULL,
    rate DECIMAL(6,4) NOT NULL,
    base_amount_dollars INTEGER NOT NULL DEFAULT 0,
    premium_threshold_dollars INTEGER,      -- premium rate threshold (if applicable)
    premium_rate DECIMAL(6,4),              -- premium rate above premium threshold
    source_url TEXT,
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(jurisdiction, tax_type, tax_year)
);

CREATE INDEX IF NOT EXISTS idx_tax_thresholds_lookup
    ON tax_thresholds(jurisdiction, tax_type, tax_year);

COMMENT ON TABLE tax_thresholds IS
    'Annual tax thresholds and rates. Updated each June when Revenue NSW publishes new year values. Replaces hardcoded constants in Python.';

-- Seed with 2025 values (currently hardcoded in generate_conveyancing_report.py)
INSERT INTO tax_thresholds (
    jurisdiction, tax_type, tax_year,
    threshold_dollars, rate, base_amount_dollars,
    premium_threshold_dollars, premium_rate,
    source_url, effective_date
) VALUES (
    'NSW', 'land_tax', 2025,
    1075000, 0.0160, 100,
    6571000, 0.0200,
    'https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/land-tax-thresholds',
    '2025-01-01'
) ON CONFLICT (jurisdiction, tax_type, tax_year) DO NOTHING;

-- 2024 values for historical reference / 5-year trend
INSERT INTO tax_thresholds (
    jurisdiction, tax_type, tax_year,
    threshold_dollars, rate, base_amount_dollars,
    premium_threshold_dollars, premium_rate,
    source_url, effective_date
) VALUES (
    'NSW', 'land_tax', 2024,
    1075000, 0.0160, 100,
    6571000, 0.0200,
    'https://www.revenue.nsw.gov.au/taxes-duties-levies-royalties/land-tax/land-tax-thresholds',
    '2024-01-01'
) ON CONFLICT (jurisdiction, tax_type, tax_year) DO NOTHING;

COMMIT;
