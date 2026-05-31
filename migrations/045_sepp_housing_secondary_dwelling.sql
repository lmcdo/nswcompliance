-- Migration 045: Add secondary_dwelling rows to housing_sepp_standards
-- Source: SEPP (Housing) 2021, Division 2 — Secondary dwellings in residential zones
-- https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#pt.3-div.2
--
-- These values were previously hardcoded in:
--   - services/granny_flat.py (SEPP_MIN_LOT_M2, SEPP_MAX_GF_AREA_M2)
--   - scripts/generate_conveyancing_report.py (_SD_MIN_LOT, _SD_ZONES)
-- Now standardised in the housing_sepp_standards table alongside LMR reform types.

BEGIN;

-- Min lot area 450m² — Clause 53(1)(b)
INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'min_lot_size', 450, 'm²',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, '53(1)(b)',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sec.53',
    '2021-11-29'
);

-- Max floor area 60m² — Clause 22(1) of SEPP (Exempt and Complying Development Codes) 2008
-- Note: this standard originates from the Codes SEPP, not Housing SEPP, but is the
-- operative limit for CDC-pathway secondary dwellings. Stored here for single source of truth.
INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_floor_area', 60, 'm²',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, '22(1)',
    'State Environmental Planning Policy (Exempt and Complying Development Codes) 2008',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572#sec.22',
    '2021-11-29'
);

COMMIT;
