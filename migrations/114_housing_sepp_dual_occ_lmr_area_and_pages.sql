-- 114: housing_sepp_standards -- dual occupancy rows apply only in a low and mid rise housing area, and every
-- cited PDF page moved to the page the clause is on in the PDF the rows link to.
--
-- WHY (1): ids 1-7 (dual_occupancy, ss 168(2) and 169(3)) carried requires_lmr_area = false. The SEPP limits both:
--   s 168(1) "This section applies to development for the purposes of dual occupancies in a low and mid rise
--   housing area in the following zones"; s 169(1) "... on land in a low and mid rise housing area ...".
-- Both readers (frontend-nextjs/app/api/housing-sepp/eligibility/route.ts and services/housing_sepp_eligibility.py)
-- gate on this flag, so 6 Berrigan St Winston Hills (R2, 685 m2, outside any such area by the 766/752/759 map
-- layers) read duplex "Eligible" and was told the SEPP's 0.65:1 and 9.5 m beat the council's 0.5:1 and 9 m.
-- The R1-R2 apartment, multi dwelling and terrace rows already carried true; this brings duplex into line.
--
-- WHY (2): r2_pdf_url .../sepps/v1.0-baseline/sepp-housing-2021.pdf is the 131-page "in force" print of
-- 30 Mar 2026. Every pdf_page in this table pointed 5-9 pages early (s 168 cited p72; p72 is s 147, design review).
-- Pages below were found by locating each clause and its value in that PDF (PyMuPDF text, 2026-10-19):
--   s 108(2) p49 | s 168(2) p80 | s 169(3) p81 | s 172(2),(3) p82 | s 173 p82 | ss 175, 176 p83 | ss 179, 180 p84
--
-- BACKUP + RESTORE: data/db_rollback_backups/housing_sepp_standards_pre_114_2026-10-19.json
-- No trigger on the table and no foreign key references it (pg_trigger, pg_constraint, 2026-10-19).
--
-- VERIFY
--   SELECT id, requires_lmr_area, pdf_page FROM housing_sepp_standards WHERE id BETWEEN 1 AND 33 ORDER BY id;

BEGIN;

DO $$
DECLARE
    n integer;
BEGIN
    UPDATE housing_sepp_standards SET requires_lmr_area = true
     WHERE id BETWEEN 1 AND 7 AND development_type = 'dual_occupancy' AND approval_pathway IS NULL
       AND requires_lmr_area = false AND (source_clause LIKE '168(2)%' OR source_clause LIKE '169(3)%');
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 7 THEN
        RAISE EXCEPTION '114: expected 7 dual occupancy rows (ids 1-7) to flag, matched %', n;
    END IF;

    -- Each update must hit exactly the rows named, by id AND clause AND the old page, or nothing commits.
    UPDATE housing_sepp_standards SET pdf_page = 49 WHERE id IN (8, 9, 10, 11)   AND source_clause LIKE '108(2)%' AND pdf_page = 44;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION '114: s 108 rows, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 80 WHERE id IN (1, 2, 3, 4, 5)  AND source_clause LIKE '168(2)%' AND pdf_page = 72;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 5 THEN RAISE EXCEPTION '114: s 168 rows, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 81 WHERE id IN (6, 7)           AND source_clause LIKE '169(3)%' AND pdf_page = 72;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION '114: s 169 rows, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 82 WHERE id BETWEEN 12 AND 21   AND source_clause LIKE '172(%'   AND pdf_page = 73;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 10 THEN RAISE EXCEPTION '114: s 172 rows, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 82 WHERE id = 22                AND source_clause = '173'        AND pdf_page = 74;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 1 THEN RAISE EXCEPTION '114: s 173 row, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 84 WHERE id BETWEEN 23 AND 27   AND source_clause LIKE '179(2)%' AND pdf_page = 75;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 5 THEN RAISE EXCEPTION '114: s 179 rows, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 84 WHERE id IN (28, 31)         AND source_clause LIKE '180(%'   AND pdf_page = 75;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 2 THEN RAISE EXCEPTION '114: s 180 rows, matched %', n; END IF;
    UPDATE housing_sepp_standards SET pdf_page = 83 WHERE id IN (29, 30, 32, 33) AND source_clause IN ('175', '176') AND pdf_page = 75;
    GET DIAGNOSTICS n = ROW_COUNT; IF n <> 4 THEN RAISE EXCEPTION '114: ss 175/176 rows, matched %', n; END IF;
END $$;

COMMIT;
