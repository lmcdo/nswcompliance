-- 123: law_facts - the law figures the low-and-mid-rise / TOD feature rests on, one row per fact.
--
-- WHY: housing_sepp_standards is filled by hand-typed SQL (migrations 045, 047, 084, 090, 114), carries no
-- law-version stamp or text hash, and holds none of the Chapter 5 figures; those are typed into
-- frontend-nextjs/components/compliance/StateLevelControls.tsx. Each row here carries the clause, the PDF
-- page, the sentence it came from, the law version date and a SHA-256 of the saved law text. Rows are loaded
-- from data/law/housing_sepp_lmr_facts.json by scripts/load_law_facts.py; ledger row DQ-151
-- (python scripts/load_law_facts.py --check) proves the table equals the JSON. A newer law version is NEW
-- rows; the old rows stay as history (is_current = false).
--
-- prior-art-checked: no law_facts or law_text_versions table exists (to_regclass NULL on the live database,
-- 2026-11-07). instrument_registry (migration 010) holds ONE row per instrument (key sepp_housing_2021,
-- version 9 October 2026, last checked 2026-10-15), not per figure with clause, page and quote; its
-- content_hash is of the live HTML page, a different hash from the saved-text hash stored here.
--
-- Owner approval: 2026-11-07 ("Yes", to this exact SQL). Read only by the backend (the app connects as the
-- table owner, which bypasses row level security); no public browser role can write it (migration 110
-- default, repeated below) and row level security is on with no policy.
--
-- Rollback: DROP TABLE public.law_facts;   -- a new empty table, nothing depends on it
-- VERIFY:   SELECT count(*) FROM public.law_facts;   -- 0 after this migration; 18 after scripts/load_law_facts.py --apply

BEGIN;

CREATE TABLE public.law_facts (
    id               bigserial PRIMARY KEY,
    instrument_key   text        NOT NULL,                 -- 'sepp_housing_2021', the key instrument_registry uses
    fact_key         text        NOT NULL,
    law_version_date date        NOT NULL,
    clause           text        NOT NULL,
    pdf_page         integer     NOT NULL CHECK (pdf_page > 0),
    pdf_page_to      integer     CHECK (pdf_page_to IS NULL OR pdf_page_to >= pdf_page),
    value            jsonb       NOT NULL,
    value_number     numeric,
    unit             text,
    measured         text,
    quote            text        NOT NULL,
    extra            jsonb       NOT NULL DEFAULT '{}'::jsonb,
    text_file        text        NOT NULL,
    text_sha256      text        NOT NULL CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
    is_current       boolean     NOT NULL DEFAULT true,
    loaded_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (instrument_key, fact_key, law_version_date)
);

CREATE UNIQUE INDEX law_facts_one_current ON public.law_facts (instrument_key, fact_key) WHERE is_current;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.law_facts FROM anon, authenticated;
ALTER TABLE public.law_facts ENABLE ROW LEVEL SECURITY;   -- no policy: only the app's owner role reads it

COMMIT;
