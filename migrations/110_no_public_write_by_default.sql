-- 110: new tables are never writable by the public browser roles by default.
--
-- Applied to production 2026-10-12 with the user's yes (this file records it; re-running is
-- harmless). Supabase's default privileges gave anon and authenticated INSERT/UPDATE/DELETE/TRUNCATE
-- on every table postgres creates in public. Four backup tables made by
-- scripts/dcp_restore_citations.py on 2026-10-12 were therefore writable with the public key for
-- about an hour (DQ-138 read 8; fixed by REVOKE + ROW LEVEL SECURITY). At least 12 scripts create
-- backup tables the same way, so the default is changed once rather than each script patched.
--
-- Proven after applying: a scratch table created by postgres got only SELECT, REFERENCES and
-- TRIGGER for anon/authenticated. Existing grants are not changed by this statement.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM anon, authenticated;

-- setback_rules_readable is an auto-updatable view owned by postgres, so writes through it bypass
-- setback_rules' row level security. Nothing in the app uses it (only its creating migration).
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.setback_rules_readable FROM anon, authenticated;

-- The four 2026-10-12 backup tables (already applied).
REVOKE ALL ON TABLE public.regulatory_provisions_citation_backup_20261012_100318 FROM anon, authenticated;
REVOKE ALL ON TABLE public.regulatory_provisions_citation_backup_20261012_100341 FROM anon, authenticated;
REVOKE ALL ON TABLE public.regulatory_provisions_citation_backup_20261012_100407 FROM anon, authenticated;
REVOKE ALL ON TABLE public.regulatory_provisions_citation_backup_20261012_100427 FROM anon, authenticated;
ALTER TABLE public.regulatory_provisions_citation_backup_20261012_100318 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_provisions_citation_backup_20261012_100341 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_provisions_citation_backup_20261012_100407 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_provisions_citation_backup_20261012_100427 ENABLE ROW LEVEL SECURITY;
