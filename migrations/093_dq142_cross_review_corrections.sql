-- 093: corrections to rows added by 091/092, from cross-review (gpt-5.6-sol) on
-- feat/dq142-building-area-controls, 2026-10-10. Every change is by row id.
--
-- 1. CHAPTER LABEL (30 rows). The 092 generator took source_chapter_key and
--    dcp_version from the council's most common chapter, not from the chapter of
--    the provision each row quotes -- Woollahra setbacks were labelled with the
--    parking chapter. Each row is relabelled with the source_chapter_key of the
--    regulatory_provisions row its quote was found in, and the most common
--    dcp_version among that council's existing rows in that chapter.
--    applicability is NOT changed (it decides who the row is served to).
--
-- 2. "WHICHEVER IS GREATER" (4 rows). The buildable-area sum uses value_min and
--    cannot compute "x% of the site length" or a neighbour average, so storing
--    the floor of a greater-of rule OVERSTATES the footprint on any lot where the
--    other limb is larger -- the permissive direction DQ-139 exists to stop.
--    These become value NULL + 'NO FIGURE: formula ...' so the footprint is
--    withheld (constraint_arithmetic three-state) rather than overstated.
--      1295 parramatta multi_dwelling_housing rear (091): 15% of site length or 6 m
--      1364 parramatta dual_occupancy rear: 30% of site length or 10 m
--      1363 parramatta dual_occupancy front: 6 m AND consistent with prevailing
--      1371 penrith dual_occupancy front: 5.5 m or neighbours' average
--
-- 3. ASYMMETRIC SIDE (1 row). 1428 northern_beaches dual_occupancy side is
--    "1m on one side and 2.5m on the other"; the sum deducts 2 x side, so 1 m
--    overstates width by 1.5 m. Stored as NO FIGURE until the sum can take two
--    sides.
--
-- 4. ASHFIELD DH REAR (1 row). 1401 recorded 'no rear setback' but its quote
--    points to "minimum rear boundary setbacks in this DCP"; no figure is in the
--    stored text, so the decision was wrong. Retired (is_current FALSE); the gap
--    reappears in DQ-142 until the PDF is read.
--
-- VERIFY: python scripts/dq_probe_live.py --id DQ-142  (69 -> 70)
--         python scripts/dq_probe_live.py --id DQ-139

BEGIN;

UPDATE dcp_setback_controls s
   SET source_chapter_key = v.k, dcp_version = v.ver
  FROM (VALUES
    (1380, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1381, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1382, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1383, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1384, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1385, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1386, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1387, 'chapter-b3-general-development', 'v2015-amended-dec2024'),
    (1391, 'cumberland-dcp-part-b-residential', 'v1.0-baseline'),
    (1394, 'grdcp-part-6-1-low-density', 'Georges River DCP 2021 Amendment 6 (June 2024)'),
    (1397, 'hornsby-dcp-2024-part3-residential', 'v2024-jun2025'),
    (1398, 'hornsby-dcp-2024-part3-residential', 'v2024-jun2025'),
    (1399, 'hornsby-dcp-2024-part3-residential', 'v2024-jun2025'),
    (1400, 'hornsby-dcp-2024-part3-residential', 'v2024-jun2025'),
    (1404, 'blacktown-dcp-2015-part-c', 'Blacktown DCP 2015'),
    (1406, 'blacktown-dcp-2015-part-c', 'Blacktown DCP 2015'),
    (1407, 'blacktown-dcp-2015-part-c', 'Blacktown DCP 2015'),
    (1408, 'blacktown-dcp-2015-part-c', 'Blacktown DCP 2015'),
    (1412, 'section-a-part-5-dual-occupancy', 'Ku-ring-gai Development Control Plan'),
    (1413, 'section-a-part-5-dual-occupancy', 'Ku-ring-gai Development Control Plan'),
    (1414, 'section-a-part-5-dual-occupancy', 'Ku-ring-gai Development Control Plan'),
    (1415, 'section-a-part-5-dual-occupancy', 'Ku-ring-gai Development Control Plan'),
    (1416, 'section-a-part-4-dwelling-houses', 'Ku-ring-gai Development Control Plan'),
    (1417, 'section-a-part-4-dwelling-houses', 'Ku-ring-gai Development Control Plan'),
    (1418, 'part-c-s3-residential', 'v1.0-2026-03-01'),
    (1419, 'part-c-s3-residential', 'v1.0-2026-03-01'),
    (1420, 'part-c-s3-residential', 'v1.0-2026-03-01'),
    (1424, 'part4-s1-low-density', 'v1.1-2026-04-06'),
    (1425, 'part4-s1-low-density', 'v1.1-2026-04-06'),
    (1426, 'part4-s1-low-density', 'v1.1-2026-04-06')
  ) AS v(id, k, ver)
 WHERE s.id = v.id AND s.is_current AND s.extraction_method = 'manual_curation';

UPDATE dcp_setback_controls SET value_min = NULL, condition = CASE id
    WHEN 1295 THEN 'NO FIGURE: formula - 15% of the site length or 6 m, whichever is greater'
    WHEN 1364 THEN 'NO FIGURE: formula - 30% of the site length or 10 m, whichever is greater; corner sites minimum 6 m'
    WHEN 1363 THEN 'NO FIGURE: minimum 6 m and consistent with the prevailing setback along the street'
    WHEN 1371 THEN 'NO FIGURE: 5.5 m or the average of the immediate neighbours'' setbacks, whichever is greater'
    WHEN 1428 THEN 'NO FIGURE: two different side setbacks - 1 m on one side and 2.5 m on the other'
  END
 WHERE id IN (1295, 1364, 1363, 1371, 1428) AND is_current AND extraction_method = 'manual_curation';

UPDATE dcp_setback_controls SET is_current = FALSE
 WHERE id = 1401 AND lga = 'ashfield' AND condition LIKE 'NO FIGURE:%' AND extraction_method = 'manual_curation';

DO $$
DECLARE a integer; b integer; c integer;
BEGIN
    SELECT count(*) INTO a FROM dcp_setback_controls
     WHERE id IN (1380, 1381, 1382, 1383, 1384, 1385, 1386, 1387, 1391, 1394, 1397, 1398, 1399, 1400,
                  1404, 1406, 1407, 1408, 1412, 1413, 1414, 1415, 1416, 1417, 1418, 1419, 1420, 1424, 1425, 1426)
       AND is_current
       AND source_chapter_key IN ('chapter-e1-parking-access', '_external_adg', 'part-3-general-planning-considerations',
                                  'part-1-general', 'part-a-car-parking', 'section-c-part-22-parking',
                                  'part-c-s1-general', 'part2-s18-landscaping');
    SELECT count(*) INTO b FROM dcp_setback_controls
     WHERE id IN (1295, 1364, 1363, 1371, 1428) AND is_current AND value_min IS NULL AND condition LIKE 'NO FIGURE:%';
    SELECT count(*) INTO c FROM dcp_setback_controls WHERE id = 1401 AND is_current;
    IF a <> 0 OR b <> 5 OR c <> 0 THEN
        RAISE EXCEPTION '093: expected 0 mislabelled / 5 formula / 0 Ashfield current, got % / % / %', a, b, c;
    END IF;
END $$;

COMMIT;
