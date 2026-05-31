-- Migration 047: Add comprehensive secondary dwelling standards to housing_sepp_standards
--
-- Prerequisite: Migration 045 adds 2 headline standards (min_lot_size 450m², max_floor_area 60m²).
-- This migration adds the remaining CDC-pathway standards for secondary dwellings.
--
-- Sources (cross-referenced 2026-05-31):
--   SEPP (Housing) 2021, Part 3 Division 2 + Schedule 1
--   SEPP (Exempt and Complying Development Codes) 2008, Part 3 (Housing Code)
--   Verified against: NSW Planning Portal, Granny Flat Approvals, BuildCert, AustLII clause text
--
-- Lot-size-banded standards use suffixed standard_type names (e.g. max_site_coverage_lot_under_900)
-- because housing_sepp_standards schema is flat (one numeric_value per row).
-- The eligibility API returns all standards; frontend groups by band for display.

BEGIN;

-- 1. Minimum lot width 12m at building line
INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'min_lot_width', 12, 'm',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

-- 2. No additional parking required
INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'parking_per_dwelling', 0, 'spaces',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Part 3, Division 2',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#pt.3-div.2',
    '2021-11-29'
);

-- 3. Maximum building height 3.8m for detached secondary dwelling
-- Source: Codes SEPP Clause 3.22 (detached development)
INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_height', 3.8, 'm',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, '3.22',
    'State Environmental Planning Policy (Exempt and Complying Development Codes) 2008',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572#sec.3.22',
    '2021-11-29'
);

-- 4. Minimum private open space 24m² (min 3m dimension)
INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'min_private_open_space', 24, 'm²',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Clause 17',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

-- 5-7. Site coverage limits by lot size band (principal + secondary + ancillary)
-- Source: Housing SEPP Schedule 1, Part 2

INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_site_coverage_lot_under_900', 50, '%',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2, Clause 3',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_site_coverage_lot_900_to_1500', 40, '%',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2, Clause 3',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_site_coverage_lot_over_1500', 30, '%',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2, Clause 3',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

-- 8-10. Total floor area limits by lot size band (principal + secondary + ancillary)
-- Source: Housing SEPP Schedule 1, Part 2

INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_total_floor_area_lot_under_600', 330, 'm²',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2, Clause 4(2)',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_total_floor_area_lot_600_to_900', 380, 'm²',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2, Clause 4(2)',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

INSERT INTO housing_sepp_standards (
    development_type, standard_type, numeric_value, unit,
    applicable_zones, requires_lmr_area, source_clause,
    source_document, legislation_url, effective_date
) VALUES (
    'secondary_dwelling', 'max_total_floor_area_lot_over_900', 430, 'm²',
    ARRAY['R1', 'R2', 'R3', 'R4'], FALSE, 'Schedule 1, Part 2, Clause 4(2)',
    'State Environmental Planning Policy (Housing) 2021',
    'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714#sch.1',
    '2021-11-29'
);

COMMIT;
