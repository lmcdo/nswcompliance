-- 101: the last 5 rows of the second Ashfield load (DQ-141) are not rules: three are worked
-- examples from the DCP's parking and sustainability illustrations ("1 space per 40 m2 = 3 spaces",
-- "assuming a 6 business day week"), two are OCR-garbled fragments. Served on their own they read
-- as controls with figures. Retired (is_current FALSE, kept).
-- VERIFY: python scripts/dq_probe_live.py --id DQ-141   (5 -> 0)

BEGIN;

UPDATE regulatory_provisions SET is_current = FALSE
 WHERE source_council IS NULL AND is_current AND id IN (81022, 81024, 81108, 81249, 87246);

DO $$
BEGIN
    IF (SELECT count(*) FROM regulatory_provisions WHERE id IN (81022, 81024, 81108, 81249, 87246) AND is_current) <> 0 THEN
        RAISE EXCEPTION '101: rows still current';
    END IF;
END $$;

COMMIT;
