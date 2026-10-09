-- 086: finish what 085 started. Revoke public writes on the rule-bearing tables
-- 085's hand-named list left out.
--
-- WHY A SECOND MIGRATION
-- 085 is already applied to production. Editing an applied migration would make
-- the file disagree with what actually ran, so the remaining tables go in their
-- own file.
--
-- WHAT 085 MISSED, AND HOW IT WAS FOUND
-- 085 revoked on 17 hand-named tables and recorded that the list was incomplete.
-- Cross-review (gpt-5.6-sol, MEDIUM) made the right objection: recording a known
-- gap is not the same as closing it, and declaring DQ-138 "fixed" while two
-- identified classes of rule-bearing table still carried public write grants is
-- exactly the kind of green reading this repo keeps getting bitten by. The two
-- classes, both named in that review:
--
--   1. lep_zone_coverage -- granted to anon by 009_lep_land_use_table_full_v2.sql
--      itself, and the source of the "13 May 2026 — data may be stale" line on
--      the LEP tab. It decides whether the land-use table is served at all.
--   2. 39 BACKUP tables holding copies of regulatory rows --
--      dcp_setback_controls_* (11) and regulatory_provisions_*backup* (28).
--      A copy of a regulatory row is still a regulatory row: a permissive policy
--      on one of these would let a public key rewrite the history that repairs
--      and audits are checked against.
--
-- Enumerated live from information_schema.tables on 2026-10-09, not guessed.
-- Same reasoning as 085 otherwise: RLS already denies these roles, serving
-- connects as the owner, service_role is untouched, SELECT is untouched. No
-- statement that succeeds today starts failing.
--
-- STILL NOT A DERIVED INVENTORY. This is a longer hand-written list, which is
-- better but not the durable fix. A table created after today is still not
-- covered. The durable fix remains A1 of
-- ~/.claude/plans/ce-rule-provenance-lockdown-PLAN-2026-10-08.md: derive the
-- rule-table set, revoke across it, and make the assertion fail for any
-- inventory table absent from the revoke set.
--
-- VERIFY
--   python scripts/dq_probe_live.py --id DQ-138     -- must stay 0
--   and the assertion below, which refuses to commit otherwise.
--
-- RESTORE: GRANT INSERT, UPDATE, DELETE, TRUNCATE ON <table> TO anon, authenticated;
-- Pre-085 grants for the original 17 are in
-- data/db_rollback_backups/grants_rule_tables_pre_085_2026-10-08.json.

BEGIN;

-- lep_zone_coverage, by name: it is a serving gate, not a backup.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.lep_zone_coverage
    FROM anon, authenticated;

-- Every table holding a copy of regulatory rows. Enumerated from the catalogue
-- rather than typed out, so a copy created between writing and running this is
-- still covered.
DO $$
DECLARE
    t record;
    n integer := 0;
BEGIN
    FOR t IN
        SELECT table_name
          FROM information_schema.tables
         WHERE table_schema = 'public'
           AND table_type = 'BASE TABLE'
           AND (table_name LIKE 'dcp_setback_controls\_%'
                OR table_name LIKE 'regulatory_provisions\_%backup%')
    LOOP
        EXECUTE format(
            'REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.%I FROM anon, authenticated',
            t.table_name
        );
        n := n + 1;
    END LOOP;
    RAISE NOTICE 'revoked public writes on % regulatory copy table(s)', n;
END $$;

-- Refuse to commit a partial revoke: no rule-bearing table may still grant a
-- write to a public role. Covers 085's 17, lep_zone_coverage, and every copy.
DO $$
DECLARE
    remaining integer;
BEGIN
    SELECT count(*) INTO remaining
      FROM (
        SELECT DISTINCT g.table_name, g.grantee
          FROM information_schema.role_table_grants g
          JOIN information_schema.tables t
            ON t.table_schema = g.table_schema
           AND t.table_name = g.table_name
           AND t.table_type = 'BASE TABLE'
         WHERE g.table_schema = 'public'
           AND g.grantee IN ('anon', 'authenticated')
           AND g.privilege_type IN ('INSERT', 'UPDATE', 'DELETE', 'TRUNCATE')
           AND (g.table_name IN ('housing_sepp_standards', 'cdc_eligibility_standards',
                                 'regulatory_provisions', 'instrument_registry',
                                 'sepp_structured_requirements', 'sepp_adg_requirements',
                                 'dcp_setback_controls', 'lep_land_use_table',
                                 'lep_clauses', 'lep_development_type_clauses',
                                 'development_controls', 'control_codes',
                                 'quantitative_standards', 'dcp_base_requirements',
                                 'dcp_precinct_requirements', 'dcp_table_of_contents',
                                 'provision_versions', 'lep_zone_coverage')
                OR g.table_name LIKE 'dcp_setback_controls\_%'
                OR g.table_name LIKE 'regulatory_provisions\_%backup%')) s;
    IF remaining <> 0 THEN
        RAISE EXCEPTION
            'still % (rule table, public role) pair(s) with write grants; refusing to commit',
            remaining;
    END IF;
    RAISE NOTICE 'no rule-bearing table grants a write to anon or authenticated';
END $$;

COMMIT;
