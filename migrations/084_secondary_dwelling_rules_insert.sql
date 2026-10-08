-- Secondary dwelling (granny flat) rules, one row per clause, by approval path.
--
-- Why: three rows stated the law wrongly and mixed the two approval paths
-- (verified against the SEPP (Housing) 2021 in force, version 11 September 2026,
-- fetched from legislation.nsw.gov.au on 2026-10-08):
--   id 44 min_lot_size 450 "53(1)(b)"  -> the 450 m2 figure is s 53(2)(a): a
--          NON-DISCRETIONARY site-area standard for DETACHED secondary dwellings
--          on the DA path, not a general minimum lot size.
--   id 34 min_lot_width 12 "Schedule 1, Part 2" -> Sch 1 cl 2(1)(b) sets a road
--          frontage at the building line of 12, 15 or 18 m by lot-area band, on
--          the CDC path.
--   id 35 parking_per_dwelling 0 "Part 3, Division 2" -> no numeric parking
--          standard exists: s 53(2)(b) (DA) keeps existing spaces; Sch 1 cl 2(3)
--          (CDC) requires no additional spaces.
--
-- STEP 2 OF 2 (after 083 and after the reader code that filters
-- approval_pathway IS NULL is deployed): inserts the corrected rules. Rows 34, 35 and 44 stay (flagged stale) until every consumer
-- has moved to the new rows; a later migration retires them. Nothing existing
-- is altered, so no current reader changes behaviour.
--
-- Every regulatory value (thresholds AND the lot-area band limits) is data
-- carried with the exact quote it comes from; services/secondary_dwelling_paths.py
-- refuses a row whose value or band limits do not appear in its own quote.

INSERT INTO housing_sepp_standards
  (development_type, standard_type, approval_pathway, numeric_value, unit,
   lot_area_min_m2, lot_area_min_inclusive, lot_area_max_m2,
   applicable_zones, requires_lmr_area, source_clause, source_document,
   legislation_url, effective_date, source_quote, verified_by, verified_at)
VALUES
  ('secondary_dwelling', 'cdc_min_road_frontage_lot_450_to_900', 'cdc', 12, 'm',
   450, TRUE, 900,
   ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 2(1)(b)(i)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.1-para1.b-para2.i',
   '2026-09-11',
   '(b) for a lot other than a battle-axe lot—has a boundary with a primary road, measured at the building line, of at least the following— ... (i) if the lot has an area of at least 450m2 but not more than 900m2—12m,',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'cdc_min_road_frontage_lot_900_to_1500', 'cdc', 15, 'm',
   900, FALSE, 1500,
   ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 2(1)(b)(ii)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.1-para1.b-para2.ii',
   '2026-09-11',
   '(b) for a lot other than a battle-axe lot—has a boundary with a primary road, measured at the building line, of at least the following— ... (ii) if the lot has an area of more than 900m2 but not more than 1500m2—15m,',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'cdc_min_road_frontage_lot_over_1500', 'cdc', 18, 'm',
   1500, FALSE, NULL,
   ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 2(1)(b)(iii)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.1-para1.b-para2.iii',
   '2026-09-11',
   '(b) for a lot other than a battle-axe lot—has a boundary with a primary road, measured at the building line, of at least the following— ... (iii) if the lot has an area of more than 1500m2—18m,',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'cdc_parking_rule', 'cdc', NULL, NULL,
   NULL, NULL, NULL,
   ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 2(3)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.3',
   '2026-09-11',
   '(3) Nothing in this Schedule requires the provision of additional parking spaces for development for the purposes of a secondary dwelling.',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'da_detached_min_site_area', 'da', 450, 'm²',
   NULL, NULL, NULL,
   ARRAY['R1','R2','R3','R4','R5'], FALSE, 's 53(2)(a)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.53-ssec.2-para1.a',
   '2026-09-11',
   '(2) The following are non-discretionary development standards in relation to the carrying out of development to which this Part applies— ... (a) for a detached secondary dwelling—a minimum site area of 450m2,',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'da_non_discretionary_note', 'da', NULL, NULL,
   NULL, NULL, NULL,
   ARRAY['R1','R2','R3','R4','R5'], FALSE, 's 53(1), Note',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.53',
   '2026-09-11',
   'See the Act, section 4.15(3), which does not prevent development consent being granted if a non-discretionary development standard is not complied with.',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'da_parking_rule', 'da', NULL, NULL,
   NULL, NULL, NULL,
   ARRAY['R1','R2','R3','R4','R5'], FALSE, 's 53(2)(b)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.53-ssec.2-para1.b',
   '2026-09-11',
   '(b) the number of parking spaces provided on the site is the same as the number of parking spaces provided on the site immediately before the development is carried out.',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'cdc_zone_scope', 'cdc', NULL, NULL,
   NULL, NULL, NULL,
   ARRAY['R1','R2','R3','R4'], FALSE, 's 49 (residential zone); s 54(1)(a)',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.54-ssec.1-para1.a',
   '2026-09-11',
   'residential zone means the following land use zones or an equivalent land use zone— (a) Zone R1 General Residential, (b) Zone R2 Low Density Residential, (c) Zone R3 Medium Density Residential, (d) Zone R4 High Density Residential, (e) Zone R5 Large Lot Residential. ... (a) is on land in a residential zone other than Zone R5 Large Lot Residential, and',
   'claude-session (user instructed fix 2026-10-08)', now()),
  ('secondary_dwelling', 'da_zone_scope', 'da', NULL, NULL,
   NULL, NULL, NULL,
   ARRAY['R1','R2','R3','R4','R5'], FALSE, 's 49 (residential zone); s 50',
   'State Environmental Planning Policy (Housing) 2021',
   'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.50',
   '2026-09-11',
   'residential zone means the following land use zones or an equivalent land use zone— (a) Zone R1 General Residential, (b) Zone R2 Low Density Residential, (c) Zone R3 Medium Density Residential, (d) Zone R4 High Density Residential, (e) Zone R5 Large Lot Residential. ... This Part applies to development for the purposes of a secondary dwelling on land in a residential zone if development for the purposes of a dwelling house is permissible on the land under another environmental planning instrument.',
   'claude-session (user instructed fix 2026-10-08)', now())
ON CONFLICT (development_type, standard_type) DO NOTHING;

-- Replay guard: fail loudly if the seven rows did not land exactly as written.
DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM housing_sepp_standards
  WHERE development_type = 'secondary_dwelling'
    AND (   (standard_type = 'cdc_min_road_frontage_lot_450_to_900' AND numeric_value = 12 AND lot_area_min_m2 = 450 AND lot_area_min_inclusive AND lot_area_max_m2 = 900)
         OR (standard_type = 'cdc_min_road_frontage_lot_900_to_1500' AND numeric_value = 15 AND lot_area_min_m2 = 900 AND NOT lot_area_min_inclusive AND lot_area_max_m2 = 1500)
         OR (standard_type = 'cdc_min_road_frontage_lot_over_1500' AND numeric_value = 18 AND lot_area_min_m2 = 1500 AND NOT lot_area_min_inclusive AND lot_area_max_m2 IS NULL)
         OR (standard_type = 'cdc_parking_rule' AND numeric_value IS NULL AND approval_pathway = 'cdc')
         OR (standard_type = 'da_detached_min_site_area' AND numeric_value = 450 AND approval_pathway = 'da')
         OR (standard_type = 'da_non_discretionary_note' AND numeric_value IS NULL AND approval_pathway = 'da')
         OR (standard_type = 'da_parking_rule' AND numeric_value IS NULL AND approval_pathway = 'da')
         OR (standard_type = 'cdc_zone_scope' AND approval_pathway = 'cdc' AND applicable_zones = ARRAY['R1','R2','R3','R4'])
         OR (standard_type = 'da_zone_scope' AND approval_pathway = 'da' AND applicable_zones = ARRAY['R1','R2','R3','R4','R5']));
  IF n <> 9 THEN
    RAISE EXCEPTION 'migration 084: expected 9 secondary_dwelling pathway rows as written, found %', n;
  END IF;
END $$;
