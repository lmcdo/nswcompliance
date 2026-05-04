-- Pre-DA Site History Reports table
-- Columns traced from:
--   services/pre_da_history.py (INSERT/UPDATE)
--   frontend-nextjs/app/api/satellite/pre-da-history/route.ts (INSERT via Supabase, SELECT)
--   frontend-nextjs/app/api/reports/pre-da-history/generate/route.ts (SELECT)

CREATE TABLE IF NOT EXISTS pre_da_history_reports (
    id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    address     text NOT NULL,
    lat         double precision,
    lon         double precision,
    council     text,
    report_json jsonb,
    status      text NOT NULL DEFAULT 'pending',   -- pending | complete | error
    error_msg   text,
    is_paid     boolean NOT NULL DEFAULT false,
    run_date    date,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Index for polling by id+status (frontend polls every 3s)
CREATE INDEX IF NOT EXISTS idx_pre_da_history_reports_status
    ON pre_da_history_reports (id, status);

COMMENT ON TABLE pre_da_history_reports IS 'Pre-DA Site History Report results. Rows pre-allocated as pending by Next.js API, updated to complete/error by Python pipeline.';
