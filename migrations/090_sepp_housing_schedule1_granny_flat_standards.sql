-- 090: SEPP (Housing) 2021 Schedule 1 granny-flat standards, cl 5-11, with quotes.
--
-- WHY: the public granny-flat tool showed a typed table (8.5 m height, 3 m rear,
-- 0.9-1.5 m side ...) citing clauses not in force; #1245 removed it because no
-- row backed it. These are the rules it was trying to state, from the law in
-- force (version from 11 Sep 2026), one row per figure, each with its exact
-- words and an anchored link, so the tool and every reader show them from the
-- database and scripts/provenance_check.py re-proves them weekly.
-- Schedule 1 states the complying development standards for a secondary
-- dwelling. approval_pathway is NULL to match ids 36-45 (the existing Sch 1
-- rows); the path engine's rules (ids 53-61) are unaffected.
-- Every quote was checked with provenance_check.trace_row() against the law in
-- force, and its number found inside it, before this file was written.
--
-- VERIFY: SELECT count(*) FROM housing_sepp_standards WHERE standard_type IN ('max_height', 'max_balcony_total_floor_area', 'setback_primary_road_lot_450_to_900', 'setback_primary_road_lot_900_to_1500', 'setback_primary_road_lot_over_1500', 'setback_secondary_road_lot_450_to_600', 'setback_secondary_road_lot_600_to_1500', 'setback_secondary_road_lot_over_1500', 'setback_classified_road', 'setback_side_lot_450_to_900', 'setback_side_lot_900_to_1500', 'setback_side_lot_over_1500', 'setback_rear_lot_450_to_900', 'setback_rear_lot_900_to_1500', 'setback_rear_lot_over_1500', 'setback_public_reserve')
--          AND development_type = 'secondary_dwelling';   -- 16
-- RESTORE: DELETE FROM housing_sepp_standards WHERE development_type='secondary_dwelling'
--          AND verified_by = 'claude-session (user instructed 2026-10-10)';

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM housing_sepp_standards
     WHERE development_type = 'secondary_dwelling' AND standard_type IN ('max_height', 'max_balcony_total_floor_area', 'setback_primary_road_lot_450_to_900', 'setback_primary_road_lot_900_to_1500', 'setback_primary_road_lot_over_1500', 'setback_secondary_road_lot_450_to_600', 'setback_secondary_road_lot_600_to_1500', 'setback_secondary_road_lot_over_1500', 'setback_classified_road', 'setback_side_lot_450_to_900', 'setback_side_lot_900_to_1500', 'setback_side_lot_over_1500', 'setback_rear_lot_450_to_900', 'setback_rear_lot_900_to_1500', 'setback_rear_lot_over_1500', 'setback_public_reserve');
    IF n <> 0 THEN
        RAISE EXCEPTION '090: % of these standard types already exist; not re-inserting', n;
    END IF;
END $$;

INSERT INTO housing_sepp_standards
  (development_type, standard_type, numeric_value, unit, applicable_zones, requires_lmr_area,
   source_clause, source_document, legislation_url, effective_date, source_quote, verified_by, verified_at)
VALUES
  ('secondary_dwelling', 'max_height', 8.5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 6(1)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.6-ssec.1', '2026-09-11',
   '(1) Development for the purposes of a secondary dwelling or an ancillary structure must not result in a new building or a new part of an existing building having a building height above ground level (existing) of more than 8.5m.',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'max_balcony_total_floor_area', 12, 'm²', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 5(1)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.5-ssec.1', '2026-09-11',
   '(1) The total floor area of all balconies, decks, patios, terraces and verandahs on a lot must be no more than 12m 2 if— (a) a part of the structure is within 6m from a side or rear boundary, and (b) the structure has a point of its finished floor level at more than 2m above ground level (existing).',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_primary_road_lot_450_to_900', 4.5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 7(1)(b)(i)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.7-ssec.1-para1.b-para2.i', '2026-09-11',
   '(i) for a lot with an area of at least 450m 2 but not more than 900m 2 —4.5m, or',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_primary_road_lot_900_to_1500', 6.5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 7(1)(b)(ii)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.7-ssec.1-para1.b-para2.ii', '2026-09-11',
   '(ii) for a lot with an area of more than 900m 2 but not more than 1,500m 2 —6.5m, or',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_primary_road_lot_over_1500', 10, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 7(1)(b)(iii)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.7-ssec.1-para1.b-para2.iii', '2026-09-11',
   '(iii) for a lot with an area of more than 1,500m 2 —10m.',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_secondary_road_lot_450_to_600', 2, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 7(3)(a)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.7-ssec.3-para1.a', '2026-09-11',
   '(a) for a lot with an area of at least 450m 2 but not more than 600m 2 —2m, or',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_secondary_road_lot_600_to_1500', 3, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 7(3)(b)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.7-ssec.3-para1.b', '2026-09-11',
   '(b) for a lot with an area of more than 600m 2 but not more than 1,500m 2 —3m, or',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_secondary_road_lot_over_1500', 5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 7(3)(c)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.7-ssec.3-para1.c', '2026-09-11',
   '(c) for a lot with an area of more than 1,500m 2 —5m.',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_classified_road', 9, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 8(b)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.8-para1.b', '2026-09-11',
   '(b) otherwise—9m.',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_side_lot_450_to_900', 0.9, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 9(1)(a)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.9-ssec.1-para1.a', '2026-09-11',
   '(a) for a lot with an area of at least 450m 2 but not more than 900m 2 —0.9m,',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_side_lot_900_to_1500', 1.5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 9(1)(b)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.9-ssec.1-para1.b', '2026-09-11',
   '(b) for a lot with an area of more than 900m 2 but not more than 1,500m 2 —1.5m,',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_side_lot_over_1500', 2.5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 9(1)(c)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.9-ssec.1-para1.c', '2026-09-11',
   '(c) for a lot with an area of more than 1,500m 2 —2.5m.',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_rear_lot_450_to_900', 3, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 10(1)(a)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.10-ssec.1-para1.a', '2026-09-11',
   '(a) for a lot with an area of at least 450m 2 but not more than 900m 2 — (i) 3m, and (ii) if the development results in a new or existing building with a height of more than 3.8m—an additional amount equal to 3 times the height above 3.8m, up to a maximum setback of 8m,',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_rear_lot_900_to_1500', 5, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 10(1)(b)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.10-ssec.1-para1.b', '2026-09-11',
   '(b) for a lot with an area of more than 900m 2 but not more than 1,500m 2 — (i) 5m, and (ii) if the development results in a new or existing building with a height of more than 3.8m—an additional amount equal to 3 times the height above 3.8m, up to a maximum setback of 12m,',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_rear_lot_over_1500', 10, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 10(1)(c)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.10-ssec.1-para1.c', '2026-09-11',
   '(c) for a lot with an area of more than 1,500m 2 — (i) 10m, and (ii) if the development results in a new or existing building with a height of more than 3.8m—an additional amount equal to 3 times the height above 3.8m, up to a maximum setback of 15m.',
   'claude-session (user instructed 2026-10-10)', now()),
  ('secondary_dwelling', 'setback_public_reserve', 3, 'm', ARRAY['R1','R2','R3','R4'], FALSE, 'Schedule 1, cl 11(1)',
   'State Environmental Planning Policy (Housing) 2021', 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.11-ssec.1', '2026-09-11',
   '(1) Development for the purposes of a secondary dwelling must not result in a new building or a new part of an existing building having a setback of less than 3m from a boundary with a public reserve.',
   'claude-session (user instructed 2026-10-10)', now());

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM housing_sepp_standards
     WHERE development_type = 'secondary_dwelling' AND standard_type IN ('max_height', 'max_balcony_total_floor_area', 'setback_primary_road_lot_450_to_900', 'setback_primary_road_lot_900_to_1500', 'setback_primary_road_lot_over_1500', 'setback_secondary_road_lot_450_to_600', 'setback_secondary_road_lot_600_to_1500', 'setback_secondary_road_lot_over_1500', 'setback_classified_road', 'setback_side_lot_450_to_900', 'setback_side_lot_900_to_1500', 'setback_side_lot_over_1500', 'setback_rear_lot_450_to_900', 'setback_rear_lot_900_to_1500', 'setback_rear_lot_over_1500', 'setback_public_reserve')
       AND source_quote IS NOT NULL AND legislation_url LIKE 'https://legislation.nsw.gov.au/%#%';
    IF n <> 16 THEN
        RAISE EXCEPTION '090: expected 16 quoted Schedule 1 rows, found %', n;
    END IF;
END $$;

COMMIT;
