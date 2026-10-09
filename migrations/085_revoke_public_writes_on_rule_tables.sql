-- 085: take INSERT/UPDATE/DELETE/TRUNCATE on the rule tables away from the
-- public browser roles. Clears DQ-138.
--
-- WHY
-- `anon` is the role behind NEXT_PUBLIC_SUPABASE_ANON_KEY, which ships to every
-- browser. Measured 2026-10-08: it holds INSERT, UPDATE, DELETE and TRUNCATE on
-- every rule table, as does `authenticated`. All 149 public base tables are in
-- that state (1,192 grant rows).
--
-- Nothing is exploitable today. RLS is enabled on these tables with no policies
-- and `anon` has rolbypassrls = false, so every statement is denied. That is ONE
-- mechanism with the grant sitting underneath it: a single permissive policy
-- added for an unrelated feature, or one DISABLE ROW LEVEL SECURITY, turns a
-- published key into a write path to regulatory data -- and the grant would make
-- it legal. This migration makes two independent things have to fail instead of
-- one.
--
-- WHERE THE GRANTS CAME FROM
-- Not a decision. migrations/009_lep_land_use_table_full_v2.sql:24-26 is the
-- pattern: `ENABLE ROW LEVEL SECURITY` immediately followed by
-- `GRANT ALL ON TABLE ... TO anon, authenticated, service_role`. That is the
-- Supabase boilerplate idiom -- grant broadly, rely on RLS -- applied table by
-- table. This migration keeps the RLS half and drops the write half.
--
-- WHY THIS CANNOT REGRESS A FEATURE
--  * Serving connects as `postgres`, the table OWNER, which bypasses RLS and
--    keeps its privileges regardless of this file.
--  * `service_role` is deliberately NOT touched. 19 frontend files use its
--    key env var and the role has rolbypassrls = true.
--  * SELECT is deliberately NOT revoked. This migration is about writes only;
--    narrowing reads is the separate read-privilege gate described in
--    ~/.claude/plans/ce-authority-status-and-offer-2026-10-08.md, which needs a
--    new non-owner serving role first and must not be switched on while DQ-136
--    reads 45.
--  * The writes being removed are already denied by RLS, so no statement that
--    succeeds today starts failing.
--
-- VERIFY (not by checking the app still works -- the app is unaffected either
-- way, so a green app proves nothing about this):
--   python scripts/dq_probe_live.py --id DQ-138     -- must print 0 (was 34)
--
-- RESTORE, if this ever needs undoing:
--   GRANT INSERT, UPDATE, DELETE, TRUNCATE ON
--     public.housing_sepp_standards, public.cdc_eligibility_standards,
--     public.regulatory_provisions, public.instrument_registry,
--     public.sepp_structured_requirements, public.sepp_adg_requirements,
--     public.dcp_setback_controls, public.lep_land_use_table,
--     public.lep_clauses, public.lep_development_type_clauses,
--     public.development_controls, public.control_codes,
--     public.quantitative_standards, public.dcp_base_requirements,
--     public.dcp_precinct_requirements, public.dcp_table_of_contents,
--     public.provision_versions
--   TO anon, authenticated;
--
-- SCOPE LIMIT, recorded: these 17 tables are a hand-named list. A catalogue
-- sweep on 2026-10-08 found 72 further rule-shaped tables outside it, including
-- 17 BACKUP tables holding copies of regulatory data (11 dcp_setback_controls_*,
-- 6 regulatory_provisions_citation_backup_*). Those are not covered here and are
-- not counted by DQ-138. `lep_zone_coverage` -- the table migration 009 granted,
-- and the source of the "data may be stale" line on the LEP tab -- is also not
-- in this list. Replace the list with the derived rule-table inventory (A1 of
-- ce-rule-provenance-lockdown-PLAN-2026-10-08.md) when it exists.

BEGIN;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON
    public.housing_sepp_standards,
    public.cdc_eligibility_standards,
    public.regulatory_provisions,
    public.instrument_registry,
    public.sepp_structured_requirements,
    public.sepp_adg_requirements,
    public.dcp_setback_controls,
    public.lep_land_use_table,
    public.lep_clauses,
    public.lep_development_type_clauses,
    public.development_controls,
    public.control_codes,
    public.quantitative_standards,
    public.dcp_base_requirements,
    public.dcp_precinct_requirements,
    public.dcp_table_of_contents,
    public.provision_versions
FROM anon, authenticated;

-- Fail the migration rather than commit a partial revoke: this must be 0.
DO $$
DECLARE
    remaining integer;
BEGIN
    SELECT count(*) INTO remaining
      FROM (
        SELECT DISTINCT table_name, grantee
          FROM information_schema.role_table_grants
         WHERE table_schema = 'public'
           AND grantee IN ('anon', 'authenticated')
           AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')
           AND table_name IN ('housing_sepp_standards', 'cdc_eligibility_standards',
                              'regulatory_provisions', 'instrument_registry',
                              'sepp_structured_requirements', 'sepp_adg_requirements',
                              'dcp_setback_controls', 'lep_land_use_table',
                              'lep_clauses', 'lep_development_type_clauses',
                              'development_controls', 'control_codes',
                              'quantitative_standards', 'dcp_base_requirements',
                              'dcp_precinct_requirements', 'dcp_table_of_contents',
                              'provision_versions')) s;
    IF remaining <> 0 THEN
        RAISE EXCEPTION
            'DQ-138 would still read % after this migration; refusing to commit',
            remaining;
    END IF;
    RAISE NOTICE 'DQ-138 now reads 0 (was 34)';
END $$;

COMMIT;
