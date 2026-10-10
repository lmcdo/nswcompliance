-- 103: register Sutherland Shire DCP 2015 Chapter 2 (Dwelling Houses) and Chapter 4 (Dual Occupancy) (DQ-142).
-- Sutherland had no residential chapter registered, so its dwelling-house and dual-occupancy building
-- controls could not be read or traced. URLs are the council's own (found from its DCP hub page,
-- 2026-10-10); content_hash / url_content_length are of the PDFs downloaded that day.
-- needs_extraction FALSE on purpose: only the building-area controls are taken (migration 104,
-- each quote checked on its page); a whole-chapter provisions load is a separate, reviewed step.

BEGIN;

INSERT INTO dcp_chapter_registry
  (council, dcp_name, doc_type, chapter_key, chapter_label, council_url, council_page_url,
   r2_version_label, content_hash, url_content_length, is_active, needs_extraction, registration_status, notes)
VALUES
  ('sutherland_shire', 'Sutherland Shire DCP 2015', 'dcp', 'sutherland-dcp-2015-ch2-dwelling-houses',
   'Chapter 2 - Dwelling Houses',
   'https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0016/119230/Chapter-2-Dwelling-Houses-May-2026.pdf',
   'https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp', 'May 2026', '5aabb8ad7a0dac158a496aea81400911ecf50eb9a66eb06d13d5b39025c94e30', 1800484, TRUE, FALSE, 'confirmed',
   '2026-10-10: registered for DQ-142; building controls only (migration 104).'),
  ('sutherland_shire', 'Sutherland Shire DCP 2015', 'dcp', 'sutherland-dcp-2015-ch4-dual-occupancy',
   'Chapter 4 - Dual Occupancy',
   'https://www.sutherlandshire.nsw.gov.au/__data/assets/pdf_file/0018/119232/Chapter-4-Dual-Occupancy-May-2026.pdf',
   'https://www.sutherlandshire.nsw.gov.au/plan-and-build/Planning-considerations/development-control-plan-dcp', 'May 2026', '0e4555bbf70ea8a0bf26829deefaa276eaa343a7a1d2a27412035d23d98d8740', 3411306, TRUE, FALSE, 'confirmed',
   '2026-10-10: registered for DQ-142; building controls only (migration 104).')
ON CONFLICT (council, chapter_key) DO NOTHING;

DO $$
BEGIN
    IF (SELECT count(*) FROM dcp_chapter_registry WHERE council = 'sutherland_shire'
          AND chapter_key IN ('sutherland-dcp-2015-ch2-dwelling-houses', 'sutherland-dcp-2015-ch4-dual-occupancy')) <> 2 THEN
        RAISE EXCEPTION '103: chapters not registered';
    END IF;
END $$;

COMMIT;
