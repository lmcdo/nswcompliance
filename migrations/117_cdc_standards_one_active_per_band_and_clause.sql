-- 117: one active CDC standard per (code, type, band, clause) — not per (code, type).
--
-- Migration 058 allowed one active row per (code_name, standard_type). The Housing Code
-- (SEPP (Exempt and Complying Development Codes) 2008, Part 3) sets most standards in
-- bands by lot area or lot width, and the same type can come from several clauses — e.g.
-- the rear setback for a detached garage (3.23(7)), a deck (3.24(2)) and a shed (3.21(8)).
-- Under 058 those 75 verified standards could not be stored.
--
-- The band is stored in `conditionality` and the clause in `ref_number`. COALESCE keeps
-- the 4 existing unbanded rows unique exactly as before.
--
-- Rollback: DROP INDEX cdc_standards_one_active;
--           CREATE UNIQUE INDEX cdc_standards_one_active
--             ON cdc_eligibility_standards (code_name, standard_type) WHERE is_active;
--           (only possible while no banded rows are active)

BEGIN;

DROP INDEX IF EXISTS cdc_standards_one_active;

CREATE UNIQUE INDEX cdc_standards_one_active
  ON cdc_eligibility_standards (code_name, standard_type,
                                COALESCE(conditionality, ''), COALESCE(ref_number, ''))
  WHERE is_active;

COMMIT;
