-- Section-level DA responses
-- Each DA session has one response per DCP section (not per provision).
-- Section key format: "{partKey}::{toc_section_number|general}"

CREATE TABLE IF NOT EXISTS da_section_responses (
  id             SERIAL PRIMARY KEY,
  da_session_id  INTEGER NOT NULL REFERENCES da_sessions(id) ON DELETE CASCADE,
  section_key    TEXT    NOT NULL,
  section_title  TEXT,
  status         TEXT    CHECK (status IN ('complies', 'varies', 'not_applicable', 'flagged')),
  narrative      TEXT,
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (da_session_id, section_key)
);

CREATE INDEX IF NOT EXISTS idx_da_section_responses_session
  ON da_section_responses(da_session_id);
