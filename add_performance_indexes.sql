-- Performance indexes for complete provision text display
-- Run on nsw_planning_corrected database

-- Index for regulatory_provisions lookups by ID
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_id ON regulatory_provisions(id);

-- Index for regulatory_provisions to legal_instruments relationship
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_instrument_id ON regulatory_provisions(instrument_id);

-- Index for regulatory_provisions to documents relationship
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_document_id ON regulatory_provisions(document_id);

-- Index for legal_instruments primary key lookups
CREATE INDEX IF NOT EXISTS idx_legal_instruments_id ON legal_instruments(id);

-- Index for documents primary key lookups
CREATE INDEX IF NOT EXISTS idx_documents_id ON documents(id);

-- Index for efficient provision searches by reference number
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_ref_number ON regulatory_provisions(ref_number);

-- Index for instrument type filtering
CREATE INDEX IF NOT EXISTS idx_legal_instruments_type ON legal_instruments(instrument_type);

-- Index for legal precedence ordering
CREATE INDEX IF NOT EXISTS idx_legal_instruments_precedence ON legal_instruments(legal_precedence);

-- Composite index for the main JOIN query used in the API
CREATE INDEX IF NOT EXISTS idx_provision_complete_lookup
ON regulatory_provisions(id, instrument_id, document_id);

-- Index for document full_text searches (if needed)
-- Note: This is expensive due to large text fields, only create if doing text searches
-- CREATE INDEX IF NOT EXISTS idx_documents_full_text_search ON documents USING gin(to_tsvector('english', full_text));

-- Verify indexes were created
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('regulatory_provisions', 'legal_instruments', 'documents')
AND indexname LIKE 'idx_%'
ORDER BY tablename, indexname;