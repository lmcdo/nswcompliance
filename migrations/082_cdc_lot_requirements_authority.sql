-- CDC Housing Code lot-requirements screen (services/cdc_lot_requirements*.py):
-- the two data changes its authority boundary needs. Nothing else is touched.
--
-- 1. The cited Codes SEPP document has no source URL, so every standard citing it
--    fails the "authoritative source URL" requirement and the screen returns
--    UNAVAILABLE. Set it to the instrument's legislation.nsw.gov.au address, the
--    same URL instrument_registry holds for sepp_exempt_complying_2008. Only a
--    NULL is filled; an existing value is never overwritten.
--
-- 2. Codes SEPP cl 3.1(3)(c) (lot width at the building line) has no standards
--    row. It lands with manual_verified = FALSE: the screen reads only verified
--    rows, so it stays UNAVAILABLE until the row is reviewed against its quote:
--
--      UPDATE cdc_eligibility_standards
--      SET manual_verified = TRUE, verified_by = '<name>', verified_at = now()
--      WHERE code_name = 'housing_code' AND standard_type = 'min_lot_width' AND is_active;
--
--    The quote below was matched against provision 36997 (PDF page 113) and the
--    law in force fetched from legislation.nsw.gov.au on 2026-10-07.
--    The legacy screen (services/cdc_screen.py) ignores this standard type.

UPDATE documents
SET source_url = 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572'
WHERE id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
  AND source_url IS NULL;

INSERT INTO cdc_eligibility_standards
  (code_name, standard_type, numeric_value, applicable_zones, conditionality,
   ref_number, source_provision_ids, source_quote, manual_verified)
VALUES
  (
    'housing_code', 'min_lot_width', 6,
    NULL, NULL,
    'cl 3.1(3)(c)',
    ARRAY[36996, 36997],
    '(3) Lot requirements — Complying development specified for this code may only be carried out on a lot that meets the following requirements — ... (c) the width of the lot must be at least 6m measured at the building line',
    FALSE
  )
ON CONFLICT DO NOTHING;

-- Replay guard: fail loudly if either change did not land as written.
DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM documents
  WHERE id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
    AND source_url = 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572';
  IF n <> 1 THEN
    RAISE EXCEPTION 'migration 082: Codes SEPP document source_url not set as expected (found %)', n;
  END IF;
  SELECT count(*) INTO n FROM cdc_eligibility_standards
  WHERE code_name = 'housing_code' AND standard_type = 'min_lot_width' AND is_active
    AND numeric_value = 6 AND ref_number = 'cl 3.1(3)(c)';
  IF n <> 1 THEN
    RAISE EXCEPTION 'migration 082: expected one active housing_code min_lot_width row of 6 at cl 3.1(3)(c), found %', n;
  END IF;
END $$;
