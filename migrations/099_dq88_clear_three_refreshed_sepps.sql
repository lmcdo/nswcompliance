-- 099: clear the DQ-88 review flag on the three SEPPs whose stored text was brought up to date
-- 2026-10-10 by scripts/dq88_sepp_bulk_refresh.py (plans data/dq88_sepp_refresh_plan*_2026-10-10.json).
--
-- The Biodiversity and Conservation, Planning Systems, and Transport and Infrastructure SEPPs were
-- loaded from PDFs dated 7 Mar / 11 Jul / 15 Aug 2025 and never monitored until 2026-10-05 (DQ-130).
-- Each stored row was compared with the version it was taken from and with today's text:
--   plan  (paragraph alignment)                 260 rows
--   plan2 (reader paragraph numbers + check)     70
--   plan3 (reader exact spans + check)           40
--   plan4 (two independent readers agree)        47
--   plan5 (two readers + main-session check)      6
--   plan6 (fresh re-sweep: 34 rows the first sweep missed; two readers agree, or <=20% of the
--          row's wording remains in today's law)                                         32
-- Every retirement keeps the row (is_current FALSE) with provision_versions history; every
-- replacement is today's text, verbatim, with v1/v2 history.
--
-- LEFT, recorded in DQ-88: 3 rows whose wording is current law but whose original item is
-- uncertain (42548, 42566, 35213; none served) and 1 served row (45832, Transport Sch 7 cl 4(2)(a))
-- with 22% of its wording still present -- for the next review. A separate 126 rows of these SEPPs
-- are not the law's verbatim words at all (OCR damage, tables, page headers): not a law-change
-- defect; logged for the citation-proof work.
-- RUN FIRST: python scripts/dq88_sepp_bulk_refresh.py data/dq88_sepp_refresh_plan6_2026-10-10.json --apply
-- VERIFY: python scripts/dq_probe_live.py --id DQ-88   (3 -> 0)

BEGIN;

DO $$
BEGIN
    IF (SELECT count(*) FROM regulatory_provisions WHERE id IN (18888, 42651, 45827) AND is_current) <> 0 THEN
        RAISE EXCEPTION '099: plan6 has not been applied -- run scripts/dq88_sepp_bulk_refresh.py data/dq88_sepp_refresh_plan6_2026-10-10.json --apply first';
    END IF;
END $$;

UPDATE instrument_registry
   SET needs_review = FALSE,
       notes = COALESCE(notes || ' ', '') || 'Reviewed 2026-10-10 (DQ-88, migration 099): stored text refreshed row by row against the law in force; see the migration header.'
 WHERE is_active AND needs_review AND version_date::date <= DATE '2026-10-10'
   AND instrument_key IN ('sepp_biodiversity_conservation_2021', 'sepp_planning_systems_2021',
                          'sepp_transport_infrastructure_2021');

DO $$
BEGIN
    IF (SELECT count(*) FROM instrument_registry WHERE is_active AND needs_review) <> 0 THEN
        RAISE EXCEPTION '099: an instrument is still flagged (a new change since this review?) -- review it first';
    END IF;
END $$;

COMMIT;
