-- DQ-61 / DQ-62: separate WHEN THE PLAN COMMENCED from IS OUR COPY CURRENT.
--
-- DQ-60 settled that `stated_date` is the full DCP's commencement -- the date
-- that decides WHICH plan governs an application, and the reason savings
-- provisions work (City of Parramatta: "Any Development Application lodged
-- before 18 September 2023 will be assessed in accordance with the relevant
-- previous DCP"). It says nothing about whether our extract reflects the
-- current text.
--
-- Those are two different facts and government publishes them as two fields.
-- NSW Legislation prints a commencement AND a currency stamp ("Current version
-- for [date] to date"). DCPs are not on NSW Legislation, so councils do the
-- equivalent with a version/amendment table -- Wingecarribee's town plans print
-- "Original ... Effective 16 June 2010" in the same table as "As amended - 7
-- ... 17 June 2015". One row is commencement, the other is currency.
--
-- Conflating them is not hypothetical. It produced parramatta's wrong year
-- (DQ-62), and `scan_statement`'s "latest effective date wins" rule means any
-- plan printing both dates stores the amendment. Giving currency its own
-- columns is what lets the writer stop competing for one column.
--
-- Additive and nullable throughout. NULL currency means "we have never
-- recorded which version we hold", which is the honest state for most councils
-- today and is what the DQ-61 ratchet counts.

ALTER TABLE dcp_plan_as_at
    ADD COLUMN IF NOT EXISTS currency_date date,
    ADD COLUMN IF NOT EXISTS currency_label text,
    ADD COLUMN IF NOT EXISTS currency_evidence text,
    ADD COLUMN IF NOT EXISTS currency_confirmed_at timestamptz;

COMMENT ON COLUMN dcp_plan_as_at.currency_date IS
    'The date the version of the plan WE HOLD took effect -- the last row of '
    'the plan''s amendment/version table. NOT the plan''s commencement, which '
    'is stated_date. DQ-61.';

COMMENT ON COLUMN dcp_plan_as_at.currency_label IS
    'The version as the plan names it, verbatim (e.g. ''As amended - 7'', '
    '''Amendment No. 4''). DQ-61.';

COMMENT ON COLUMN dcp_plan_as_at.currency_evidence IS
    'Verbatim source line with file and page, same contract as '
    'stated_evidence: a reader must be able to re-read it. DQ-61.';

COMMENT ON COLUMN dcp_plan_as_at.currency_confirmed_at IS
    'When we last confirmed this against what the council publishes NOW. A '
    'currency_date with no confirmation is a fact about our copy, not about '
    'the council''s. DQ-61.';
