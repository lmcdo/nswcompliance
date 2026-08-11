-- Seed cdc_eligibility_standards for the Housing Code (#820, PR-1 follow-up).
--
-- Every value below is quoted from the ingested SEPP (Exempt and Complying
-- Development Codes) 2008 corpus in regulatory_provisions, cited by row id.
-- Rows land with manual_verified = FALSE: the engine (services/cdc_screen.py)
-- reads only verified rows, so NOTHING renders from this seed until the
-- founder reviews each row against its quote and flips the flag:
--
--   UPDATE cdc_eligibility_standards
--   SET manual_verified = TRUE, verified_by = '<name>', verified_at = now()
--   WHERE id IN (...);
--
-- Grounding corrections vs the workbench route's TS hardcodes, found during
-- extraction:
--   * acid-sulfate exclusion is Class 1 OR 2 (cl 1.19(1)(c)) — the route's
--     "Class <= 3" over-excluded Class 3 land;
--   * B1/B2 have no grounding in the Housing Code lot requirements and are
--     not seeded;
--   * the conditional "200 m2 if no minimum specified" wording (cl
--     6.4(1)(d)(ii)) belongs to a different code — the Housing Code minimum
--     in cl 3.1(3)(b) is flat, so conditionality is NULL here.

INSERT INTO cdc_eligibility_standards
  (code_name, standard_type, numeric_value, applicable_zones, conditionality,
   ref_number, source_provision_ids, source_quote, manual_verified)
VALUES
  (
    'housing_code', 'eligible_zones', NULL,
    ARRAY['R1', 'R2', 'R3', 'R4', 'RU5'], NULL,
    'cl 3.1(3)(a)',
    ARRAY[36996, 36997],
    '(3) Lot requirements — Complying development specified for this code may only be carried out on a lot that meets the following requirements — (a) the lot must be in Zone R1, R2, R3, R4 or RU5',
    FALSE
  ),
  (
    'housing_code', 'min_lot_size', 200,
    NULL, NULL,
    'cl 3.1(3)(b)',
    ARRAY[36996, 36997],
    '(3) Lot requirements — ... (b) the area of the lot must not be less than 200 m2',
    FALSE
  ),
  (
    'housing_code', 'acid_sulfate_max_class', 2,
    NULL, NULL,
    'cl 1.19(1)(c)',
    ARRAY[36184, 36185],
    'To be complying development specified for the Housing Code ... the development must not be carried out on ... (c) land identified on an Acid Sulfate Soils Map as being Class 1 or Class 2',
    FALSE
  )
ON CONFLICT DO NOTHING;

-- Replay guard (Sol review of PR #827): ON CONFLICT DO NOTHING makes re-runs
-- safe, but a conflicting row carrying DIFFERENT values would be skipped
-- silently. Assert the three seeded standards exist with exactly the seeded
-- values, so drift fails the migration loudly instead of shipping quietly.
DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM cdc_eligibility_standards
  WHERE code_name = 'housing_code' AND is_active
    AND (   (standard_type = 'eligible_zones'
             AND applicable_zones = ARRAY['R1','R2','R3','R4','RU5'])
         OR (standard_type = 'min_lot_size' AND numeric_value = 200)
         OR (standard_type = 'acid_sulfate_max_class' AND numeric_value = 2));
  IF n <> 3 THEN
    RAISE EXCEPTION
      'cdc_eligibility_standards seed mismatch: expected the 3 housing_code rows with seeded values, found %', n;
  END IF;
END $$;
