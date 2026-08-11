-- Lead qualification + consent audit fields for canibuildit_leads.
-- Additive and nullable only — existing rows and the existing insert path are
-- unaffected. Backfills nothing; new qualified leads populate these going forward.
--
-- qualification: {timeline, ownership, finance, budget} from the multi-step
--   qualifier (CXL qualify-first pattern) — turns an L0/L1 email into an L2 lead.
-- consent: append-only-by-convention audit of the express third-party-share
--   consent (OAIC: entity bears the burden of proving consent) —
--   {version, wording, shared_with, marketing_opt_in, ip, captured_at}.
-- Lead rows are insert-only (never updated), so the row itself is the record.

ALTER TABLE canibuildit_leads
  ADD COLUMN IF NOT EXISTS first_name    text,
  ADD COLUMN IF NOT EXISTS phone         text,
  ADD COLUMN IF NOT EXISTS qualification jsonb,
  ADD COLUMN IF NOT EXISTS consent       jsonb;
