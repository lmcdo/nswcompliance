-- Research Assistant PostgreSQL Schema - OPTIMIZED VERSION
-- Incorporates best practices and performance optimizations

-- ============================================================================
-- SCHEMA SETUP
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS research_assistant;
CREATE SCHEMA IF NOT EXISTS migration_audit;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- For fuzzy text search
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- For composite indexes

-- ============================================================================
-- ENUM TYPES (Better than VARCHAR for constrained values)
-- ============================================================================

CREATE TYPE research_assistant.document_type AS ENUM ('LEP', 'DCP', 'SEPP', 'OTHER');
CREATE TYPE research_assistant.provision_type AS ENUM (
    'setback', 'height', 'fsr', 'site_coverage', 'landscaping', 
    'heritage', 'parking', 'environmental', 'general'
);
CREATE TYPE research_assistant.relationship_type AS ENUM (
    'supersedes', 'complements', 'references', 'conflicts_with'
);
CREATE TYPE research_assistant.confidence_level AS ENUM (
    'explicit', 'geographic', 'inferred', 'uncertain'
);

-- ============================================================================
-- CORE TABLES WITH BEST PRACTICES
-- ============================================================================

-- Documents table with proper constraints and defaults
CREATE TABLE research_assistant.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_name VARCHAR(255) NOT NULL,
    document_type research_assistant.document_type NOT NULL,
    jurisdiction VARCHAR(100) NOT NULL,
    document_url TEXT,
    document_hash VARCHAR(64), -- For detecting document changes
    
    -- Metadata
    version VARCHAR(20),
    effective_date DATE,
    last_updated DATE DEFAULT CURRENT_DATE,
    expiry_date DATE,
    
    -- Scope and applicability
    applicable_zones TEXT[] DEFAULT '{}',
    geographic_scope JSONB, -- GeoJSON for spatial queries
    
    -- Quality metrics
    extraction_confidence DECIMAL(3,2) DEFAULT 0.00 CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),
    completeness_score DECIMAL(3,2) DEFAULT 0.00 CHECK (completeness_score >= 0 AND completeness_score <= 1),
    complexity_level INTEGER DEFAULT 3 CHECK (complexity_level BETWEEN 1 AND 5),
    
    -- Audit fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    
    -- Constraints
    CONSTRAINT uk_document_name_version UNIQUE(document_name, version),
    CONSTRAINT chk_dates CHECK (effective_date <= COALESCE(expiry_date, '9999-12-31'))
);

-- Provisions table with optimizations
CREATE TABLE research_assistant.provisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES research_assistant.documents(id) ON DELETE CASCADE,
    
    -- Core content
    clause_reference VARCHAR(50),
    section_header TEXT,
    provision_text TEXT NOT NULL,
    provision_type research_assistant.provision_type,
    
    -- Location in document
    page_number INTEGER CHECK (page_number > 0),
    section_number VARCHAR(20),
    
    -- Extracted entities (using arrays for performance)
    zone_mentions TEXT[] DEFAULT '{}',
    development_types TEXT[] DEFAULT '{}',
    keywords TEXT[] DEFAULT '{}',
    
    -- Numeric values extracted
    numeric_values JSONB DEFAULT '[]', -- Array of {value, unit, context}
    
    -- Complexity and specialist requirements
    requires_specialist BOOLEAN DEFAULT FALSE,
    specialist_types TEXT[] DEFAULT '{}',
    complexity_keywords TEXT[] DEFAULT '{}',
    red_flags TEXT[] DEFAULT '{}',
    
    -- Confidence and quality
    extraction_confidence research_assistant.confidence_level DEFAULT 'uncertain',
    is_verified BOOLEAN DEFAULT FALSE,
    verification_date DATE,
    verified_by VARCHAR(100),
    
    -- Cross-references
    related_clauses TEXT[] DEFAULT '{}',
    supersedes TEXT[] DEFAULT '{}',
    superseded_by TEXT[] DEFAULT '{}',
    
    -- Full-text search optimization
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', COALESCE(clause_reference, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(section_header, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(provision_text, '')), 'C')
    ) STORED,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT uk_document_clause UNIQUE(document_id, clause_reference)
);

-- Document relationships with bidirectional tracking
CREATE TABLE research_assistant.document_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    primary_document_id UUID NOT NULL REFERENCES research_assistant.documents(id) ON DELETE CASCADE,
    related_document_id UUID NOT NULL REFERENCES research_assistant.documents(id) ON DELETE CASCADE,
    relationship_type research_assistant.relationship_type NOT NULL,
    
    -- Relationship metadata
    relevance_score DECIMAL(3,2) DEFAULT 0.50 CHECK (relevance_score >= 0 AND relevance_score <= 1),
    is_bidirectional BOOLEAN DEFAULT FALSE,
    relationship_context TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100),
    
    -- Constraints
    CONSTRAINT uk_document_pair UNIQUE(primary_document_id, related_document_id, relationship_type),
    CONSTRAINT chk_different_documents CHECK (primary_document_id != related_document_id)
);

-- Complexity indicators with categories
CREATE TABLE research_assistant.complexity_indicators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    keyword VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    
    -- Weighting and impact
    complexity_weight DECIMAL(3,2) DEFAULT 1.00 CHECK (complexity_weight >= 0 AND complexity_weight <= 5),
    requires_specialist BOOLEAN DEFAULT FALSE,
    specialist_type VARCHAR(100),
    
    -- Additional metadata
    description TEXT,
    common_issues TEXT[],
    typical_resolution TEXT,
    
    -- Active flag for easy enable/disable
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Zone-document mapping with confidence scoring
CREATE TABLE research_assistant.zone_document_matrix (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_code VARCHAR(10) NOT NULL,
    document_id UUID NOT NULL REFERENCES research_assistant.documents(id) ON DELETE CASCADE,
    
    -- Applicability with nuance
    applicability VARCHAR(20) DEFAULT 'applies' CHECK (applicability IN ('always', 'applies', 'sometimes', 'rarely', 'never')),
    confidence DECIMAL(3,2) DEFAULT 0.80 CHECK (confidence >= 0 AND confidence <= 1),
    
    -- Context
    specific_sections TEXT[], -- Which sections apply to this zone
    exceptions TEXT[], -- Known exceptions
    notes TEXT,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified_at TIMESTAMP WITH TIME ZONE,
    verified_by VARCHAR(100),
    
    -- Constraints
    CONSTRAINT uk_zone_document UNIQUE(zone_code, document_id)
);

-- User search history for analytics
CREATE TABLE research_assistant.search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(100),
    search_query TEXT NOT NULL,
    search_type VARCHAR(50), -- 'zone', 'keyword', 'address', 'provision'
    
    -- Results
    result_count INTEGER DEFAULT 0,
    results_clicked UUID[], -- provision IDs clicked
    
    -- Performance
    response_time_ms INTEGER,
    
    -- Context
    zone_filter TEXT[],
    document_filter UUID[],
    
    -- Timestamp
    searched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Session tracking
    session_id UUID,
    ip_address INET
);

-- Provision feedback for continuous improvement
CREATE TABLE research_assistant.provision_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provision_id UUID NOT NULL REFERENCES research_assistant.provisions(id) ON DELETE CASCADE,
    user_id VARCHAR(100),
    
    -- Feedback type
    feedback_type VARCHAR(50), -- 'helpful', 'not_helpful', 'incorrect', 'outdated'
    feedback_text TEXT,
    
    -- Suggested corrections
    suggested_zone_mentions TEXT[],
    suggested_keywords TEXT[],
    
    -- Timestamp
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- MATERIALIZED VIEWS FOR PERFORMANCE
-- ============================================================================

-- Pre-computed zone coverage for fast lookups
CREATE MATERIALIZED VIEW research_assistant.zone_coverage AS
SELECT 
    z.zone_code,
    COUNT(DISTINCT d.id) as document_count,
    COUNT(DISTINCT p.id) as provision_count,
    ARRAY_AGG(DISTINCT d.document_type) as document_types,
    ARRAY_AGG(DISTINCT p.provision_type) FILTER (WHERE p.provision_type IS NOT NULL) as provision_types,
    AVG(p.extraction_confidence::INTEGER) as avg_confidence
FROM 
    (SELECT DISTINCT unnest(zone_mentions) as zone_code FROM research_assistant.provisions) z
    LEFT JOIN research_assistant.provisions p ON z.zone_code = ANY(p.zone_mentions)
    LEFT JOIN research_assistant.documents d ON p.document_id = d.id
GROUP BY z.zone_code;

-- Create index on materialized view
CREATE UNIQUE INDEX idx_zone_coverage_zone ON research_assistant.zone_coverage(zone_code);

-- ============================================================================
-- OPTIMIZED INDEXES
-- ============================================================================

-- Primary search indexes
CREATE INDEX idx_provisions_search_vector ON research_assistant.provisions USING GIN(search_vector);
CREATE INDEX idx_provisions_zones ON research_assistant.provisions USING GIN(zone_mentions);
CREATE INDEX idx_provisions_keywords ON research_assistant.provisions USING GIN(keywords);
CREATE INDEX idx_provisions_dev_types ON research_assistant.provisions USING GIN(development_types);

-- Foreign key indexes (often missed but critical for joins)
CREATE INDEX idx_provisions_document_id ON research_assistant.provisions(document_id);
CREATE INDEX idx_relationships_primary ON research_assistant.document_relationships(primary_document_id);
CREATE INDEX idx_relationships_related ON research_assistant.document_relationships(related_document_id);

-- Composite indexes for common queries
CREATE INDEX idx_provisions_doc_type ON research_assistant.provisions(document_id, provision_type);
CREATE INDEX idx_zone_matrix_lookup ON research_assistant.zone_document_matrix(zone_code, confidence DESC);

-- Partial indexes for filtered queries
CREATE INDEX idx_provisions_specialist ON research_assistant.provisions(requires_specialist) 
    WHERE requires_specialist = TRUE;
CREATE INDEX idx_provisions_verified ON research_assistant.provisions(is_verified, verification_date) 
    WHERE is_verified = TRUE;

-- Trigram indexes for fuzzy search
CREATE INDEX idx_documents_name_trgm ON research_assistant.documents USING GIN(document_name gin_trgm_ops);
CREATE INDEX idx_provisions_header_trgm ON research_assistant.provisions USING GIN(section_header gin_trgm_ops);

-- ============================================================================
-- TRIGGERS FOR DATA INTEGRITY
-- ============================================================================

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION research_assistant.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_documents_updated_at 
    BEFORE UPDATE ON research_assistant.documents
    FOR EACH ROW EXECUTE FUNCTION research_assistant.update_updated_at();

CREATE TRIGGER update_provisions_updated_at 
    BEFORE UPDATE ON research_assistant.provisions
    FOR EACH ROW EXECUTE FUNCTION research_assistant.update_updated_at();

-- Validate zone codes
CREATE OR REPLACE FUNCTION research_assistant.validate_zone_code()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.zone_mentions IS NOT NULL THEN
        FOR i IN 1..array_length(NEW.zone_mentions, 1) LOOP
            IF NOT NEW.zone_mentions[i] ~ '^[A-Z]+[0-9]+[A-Z]*$' THEN
                RAISE EXCEPTION 'Invalid zone code format: %', NEW.zone_mentions[i];
            END IF;
        END LOOP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER validate_provision_zones 
    BEFORE INSERT OR UPDATE ON research_assistant.provisions
    FOR EACH ROW EXECUTE FUNCTION research_assistant.validate_zone_code();

-- ============================================================================
-- PARTITIONING FOR SCALE (if needed for large datasets)
-- ============================================================================

-- Example: Partition search_history by month for performance
/*
CREATE TABLE research_assistant.search_history_2024_01 PARTITION OF research_assistant.search_history
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
    
CREATE TABLE research_assistant.search_history_2024_02 PARTITION OF research_assistant.search_history
    FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
*/

-- ============================================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- ============================================================================

-- Find relevant provisions for a zone
CREATE OR REPLACE FUNCTION research_assistant.get_zone_provisions(
    p_zone_code VARCHAR(10),
    p_limit INTEGER DEFAULT 100
)
RETURNS TABLE (
    provision_id UUID,
    document_name VARCHAR(255),
    clause_reference VARCHAR(50),
    provision_text TEXT,
    confidence research_assistant.confidence_level
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        d.document_name,
        p.clause_reference,
        p.provision_text,
        p.extraction_confidence
    FROM research_assistant.provisions p
    JOIN research_assistant.documents d ON p.document_id = d.id
    WHERE p_zone_code = ANY(p.zone_mentions)
    ORDER BY 
        p.extraction_confidence DESC,
        d.document_type,
        p.clause_reference
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Calculate complexity score for a set of provisions
CREATE OR REPLACE FUNCTION research_assistant.calculate_complexity_score(
    p_provision_ids UUID[]
)
RETURNS DECIMAL AS $$
DECLARE
    v_score DECIMAL := 0;
    v_provision RECORD;
BEGIN
    FOR v_provision IN 
        SELECT p.*, ci.complexity_weight
        FROM research_assistant.provisions p
        LEFT JOIN research_assistant.complexity_indicators ci 
            ON ci.keyword = ANY(p.complexity_keywords)
        WHERE p.id = ANY(p_provision_ids)
    LOOP
        v_score := v_score + COALESCE(v_provision.complexity_weight, 1.0);
        
        IF v_provision.requires_specialist THEN
            v_score := v_score + 2.0;
        END IF;
    END LOOP;
    
    RETURN LEAST(v_score, 5.0); -- Cap at 5
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SECURITY AND PERMISSIONS
-- ============================================================================

-- Create read-only role for API access
CREATE ROLE research_assistant_readonly;
GRANT USAGE ON SCHEMA research_assistant TO research_assistant_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA research_assistant TO research_assistant_readonly;

-- Create write role for admin operations
CREATE ROLE research_assistant_admin;
GRANT ALL ON SCHEMA research_assistant TO research_assistant_admin;
GRANT ALL ON ALL TABLES IN SCHEMA research_assistant TO research_assistant_admin;
GRANT ALL ON ALL SEQUENCES IN SCHEMA research_assistant TO research_assistant_admin;

-- ============================================================================
-- MONITORING AND MAINTENANCE
-- ============================================================================

-- Table for tracking slow queries
CREATE TABLE migration_audit.slow_query_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT,
    duration_ms INTEGER,
    called_from VARCHAR(255),
    parameters JSONB,
    logged_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Function to log slow queries
CREATE OR REPLACE FUNCTION migration_audit.log_slow_query(
    p_query TEXT,
    p_duration_ms INTEGER,
    p_called_from VARCHAR(255) DEFAULT NULL,
    p_parameters JSONB DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    IF p_duration_ms > 1000 THEN -- Log queries over 1 second
        INSERT INTO migration_audit.slow_query_log (query, duration_ms, called_from, parameters)
        VALUES (p_query, p_duration_ms, p_called_from, p_parameters);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA POPULATION
-- ============================================================================

-- Insert default complexity indicators
INSERT INTO research_assistant.complexity_indicators 
(keyword, category, subcategory, complexity_weight, requires_specialist, specialist_type, description)
VALUES
-- Heritage
('heritage', 'heritage', 'conservation', 2.0, TRUE, 'heritage consultant', 'Heritage conservation requirements'),
('conservation area', 'heritage', 'conservation', 2.0, TRUE, 'heritage consultant', 'Located in conservation area'),
('contributory item', 'heritage', 'item', 1.8, TRUE, 'heritage consultant', 'Contributory heritage item'),
('heritage item', 'heritage', 'item', 2.2, TRUE, 'heritage consultant', 'Listed heritage item'),

-- Environmental
('flood', 'environmental', 'flood', 1.8, TRUE, 'flood consultant', 'Flood-prone land'),
('flooding', 'environmental', 'flood', 1.8, TRUE, 'flood consultant', 'Flooding risk area'),
('contaminated', 'environmental', 'contamination', 2.2, TRUE, 'contamination consultant', 'Potentially contaminated land'),
('contamination', 'environmental', 'contamination', 2.2, TRUE, 'contamination consultant', 'Contamination assessment required'),
('acid sulfate', 'environmental', 'soil', 1.6, TRUE, 'environmental consultant', 'Acid sulfate soils'),
('bushfire', 'environmental', 'bushfire', 1.9, TRUE, 'bushfire consultant', 'Bushfire prone land'),

-- Infrastructure
('traffic', 'infrastructure', 'transport', 1.5, TRUE, 'traffic engineer', 'Traffic impact assessment'),
('acoustic', 'infrastructure', 'noise', 1.3, TRUE, 'acoustic consultant', 'Acoustic assessment required'),
('geotechnical', 'infrastructure', 'ground', 1.7, TRUE, 'geotechnical engineer', 'Geotechnical investigation required'),
('stormwater', 'infrastructure', 'water', 1.4, FALSE, NULL, 'Stormwater management required'),

-- Planning complexity
('design excellence', 'planning', 'design', 1.4, FALSE, NULL, 'Design excellence requirements'),
('design competition', 'planning', 'design', 1.6, FALSE, NULL, 'Design competition required'),
('planning agreement', 'planning', 'legal', 1.5, FALSE, NULL, 'VPA or planning agreement'),
('affordable housing', 'planning', 'policy', 1.6, FALSE, NULL, 'Affordable housing contribution'),
('clause 4.6', 'planning', 'variation', 1.8, FALSE, NULL, 'Development standard variation');

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON SCHEMA research_assistant IS 'Planning research assistant schema optimized for document navigation and complexity assessment';
COMMENT ON TABLE research_assistant.documents IS 'Master registry of planning documents (LEP, DCP, SEPP)';
COMMENT ON TABLE research_assistant.provisions IS 'Individual provisions extracted from planning documents';
COMMENT ON TABLE research_assistant.document_relationships IS 'Relationships between planning documents (supersedes, references, etc)';
COMMENT ON TABLE research_assistant.complexity_indicators IS 'Keywords and patterns that indicate planning complexity';
COMMENT ON TABLE research_assistant.zone_document_matrix IS 'Mapping of which documents apply to which zones';
COMMENT ON COLUMN research_assistant.provisions.search_vector IS 'Pre-computed full-text search vector for performance';
COMMENT ON COLUMN research_assistant.provisions.numeric_values IS 'JSON array of numeric standards extracted from text';

-- ============================================================================
-- PERFORMANCE BASELINE
-- ============================================================================

-- Create statistics for query planner
ANALYZE research_assistant.documents;
ANALYZE research_assistant.provisions;
ANALYZE research_assistant.document_relationships;
ANALYZE research_assistant.complexity_indicators;
ANALYZE research_assistant.zone_document_matrix;