-- 106: per-control DCP coverage findings (DQ-142's last gaps).
-- dcp_dev_type_coverage gains control_type: NULL = the whole housing type (migration 105), otherwise
-- one control ('front_setback', 'side_setback', 'rear_setback', or 'cap' = site coverage / landscaped
-- area / deep soil). Each row was checked by two readings of the chapter (a reader, then a focused
-- re-read with the nearest related sentence quoted); every quote below was checked to occur in the
-- stored chapter text before this file was written. A floor-area limit is not recorded as a cap.
-- Not recorded (still open): Ashfield dwelling-house rear setback -- Chapter F points to a minimum
-- "in this DCP" that has not yet been located.
-- VERIFY: python scripts/dq_probe_live.py --id DQ-142

BEGIN;

ALTER TABLE dcp_dev_type_coverage ADD COLUMN IF NOT EXISTS control_type text
    CHECK (control_type IS NULL OR control_type IN ('front_setback', 'side_setback', 'rear_setback', 'cap'));
ALTER TABLE dcp_dev_type_coverage DROP CONSTRAINT IF EXISTS dcp_dev_type_coverage_council_dev_type_key;
CREATE UNIQUE INDEX IF NOT EXISTS dcp_dev_type_coverage_key
    ON dcp_dev_type_coverage (council, dev_type, COALESCE(control_type, ''));

INSERT INTO dcp_dev_type_coverage
  (council, dev_type, control_type, coverage, statement, evidence_quote, evidence_url, evidence_page, reviewed_at)
VALUES
  ('sutherland_shire', 'dwelling_house', 'cap', 'none', 'Sutherland Shire DCP 2015 Chapter 2 (Dwelling Houses), reviewed on 10 October 2026, sets no site coverage, landscaped area or deep soil percentage for the whole lot; its 50% deep soil control applies to the front setback area only.', NULL, 'https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0016/119230/Chapter-2-Dwelling-Houses-May-2026.pdf', NULL, DATE '2026-10-10'),
  ('sutherland_shire', 'dual_occupancy', 'cap', 'none', 'Sutherland Shire DCP 2015 Chapter 4 (Dual Occupancy), reviewed on 10 October 2026, sets no site coverage, landscaped area or deep soil percentage for the whole lot; its 50% deep soil control applies to the front setback area only.', NULL, 'https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0018/119232/Chapter-4-Dual-Occupancy-May-2026.pdf', NULL, DATE '2026-10-10'),
  ('blacktown', 'dwelling_house', 'cap', 'none', 'Blacktown DCP 2015 Part C, reviewed on 10 October 2026, sets no site coverage, landscaped area or deep soil percentage for dwelling houses.', NULL, 'https://www.blacktown.nsw.gov.au/files/assets/public/v/1/part-c-development-in-the-residential-areas_01-02-2026.pdf', NULL, DATE '2026-10-10'),
  ('burwood', 'secondary_dwelling', 'cap', 'none', 'Burwood DCP Part 4 Section 4.4, reviewed on 10 October 2026, sets no site coverage, landscaped area or deep soil percentage for secondary dwellings; its 67% Built Area counts the floor area of every storey, so it is not a footprint cap.', 'The maximum Built Area is 67%.', 'https://www.burwood.nsw.gov.au/Planning-and-Development/Planning-Controls/Development-Control-Plans', 204, DATE '2026-10-10'),
  ('burwood', 'dual_occupancy', 'cap', 'none', 'Burwood DCP Part 4 Section 4.4, reviewed on 10 October 2026, sets no site-wide site coverage, landscaped area or deep soil percentage for dual occupancy; its landscaping controls are shares of the front setback.', 'A minimum 30% of the front setback (i.e. front yard) is to consist of soft landscaping.', 'https://www.burwood.nsw.gov.au/Planning-and-Development/Planning-Controls/Development-Control-Plans', 205, DATE '2026-10-10'),
  ('campbelltown', 'secondary_dwelling', 'cap', 'none', 'Campbelltown DCP 2015 Part 3, reviewed on 10 October 2026, sets no site coverage, landscaped area or deep soil percentage for secondary dwellings.', 'Ensure that secondary dwelling development is of a small scale.', 'https://www.campbelltown.nsw.gov.au/files/sharedassets/public/v/2/build-and-develop/documents/dcp/volume-1/part-3-low-and-medium-desnity-residential-development.pdf', 22, DATE '2026-10-10'),
  ('canterbury_bankstown', 'secondary_dwelling', 'cap', 'none', 'Canterbury-Bankstown DCP 2023, reviewed on 10 October 2026: in the former Canterbury area (Chapter 5.2) secondary dwellings are assessed against Schedule 1 of the Housing SEPP; in the former Bankstown area (Chapter 5.1) the control limits floor area (60 m2), which is not a footprint cap.', 'All applications for secondary dwellings will be assessed against Schedule 1 of the State Environmental Planning Policy (Housing) 2021.', 'http://webdocs.bankstown.nsw.gov.au/api/publish?documentPath=aHR0cDovL2lzaGFyZS9zaXRlcy9QbGFubmluZy9TUC9EQ1AgQW1lbmRtZW50cy9EQ1AgLSBXZWJzaXRlIERvY3VtZW50cyAtIEN1cnJlbnQgdmVyc2lvbnMgb24gQ291bmNpbCdzIHdlYnNpdGUvMjAyNi4wMy4xMiAtIERDUCAyMDIzIC0gQU1FTkRNRU5UIDExIC0gQ2hhcHRlciA1LjIgLSBGb3JtZXIgQ2FudGVyYnVyeSBMR0EucGRm&title=2026.03.12%20-%20DCP%202023%20-%20AMENDMENT%2011%20-%20Chapter%205.2%20-%20Former%20Canterbury%20LGA.pdf', 122, DATE '2026-10-10'),
  ('fairfield', 'secondary_dwelling', 'front_setback', 'none', 'Fairfield DCP Chapter 5B (urban areas), reviewed on 10 October 2026, sets no front setback figure for secondary dwellings; Chapter 4B (rural zones RU2 and RU4 only) requires them in line with or behind the front elevation.', 'A secondary dwelling located alongside the existing dwelling within the front building line must be:', 'https://www.fairfieldcity.nsw.gov.au/Development/Development-Controls/Development-Control-Plan', 179, DATE '2026-10-10'),
  ('city_of_sydney', 'secondary_dwelling', 'front_setback', 'none', 'Sydney DCP 2012 Section 4.1, reviewed on 10 October 2026, sets no setback figures for secondary dwellings; its general setback provisions refer to the Building setbacks map and the established pattern of the street.', 'Front setbacks are to be consistent with the Building setbacks map.', 'https://www.cityofsydney.nsw.gov.au/-/media/corporate/files/publications/development-control-plans/section4_dcp2012_091222.pdf?download=true', 6, DATE '2026-10-10'),
  ('city_of_sydney', 'secondary_dwelling', 'side_setback', 'none', 'Sydney DCP 2012 Section 4.1, reviewed on 10 October 2026, sets no setback figures for secondary dwellings; its general setback provisions refer to the Building setbacks map and the established pattern of the street.', 'new development is to relate to the established development pattern including the subdivision pattern, front, side and rear setbacks.', 'https://www.cityofsydney.nsw.gov.au/-/media/corporate/files/publications/development-control-plans/section4_dcp2012_091222.pdf?download=true', 6, DATE '2026-10-10'),
  ('city_of_sydney', 'secondary_dwelling', 'rear_setback', 'none', 'Sydney DCP 2012 Section 4.1, reviewed on 10 October 2026, sets no setback figures for secondary dwellings; its general setback provisions refer to the Building setbacks map and the established pattern of the street.', 'New development and alterations and additions must respect and be sympathetic to the predominant rear building line.', 'https://www.cityofsydney.nsw.gov.au/-/media/corporate/files/publications/development-control-plans/section4_dcp2012_091222.pdf?download=true', 7, DATE '2026-10-10');

DO $$
BEGIN
    IF (SELECT count(*) FROM dcp_dev_type_coverage WHERE control_type IS NOT NULL AND is_current) <> 11 THEN
        RAISE EXCEPTION '106: expected 11 per-control findings';
    END IF;
END $$;

COMMIT;
