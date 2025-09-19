-- Research Assistant PostgreSQL Schema
-- Focused on document navigation and complexity assessment

CREATE SCHEMA IF NOT EXISTS research_assistant;

-- Core document registry
CREATE TABLE research_assistant.documents (
    id SERIAL PRIMARY KEY,
    document_name VARCHAR(255) NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- LEP, DCP, SEPP
    jurisdiction VARCHAR(100), -- Inner West, City of Sydney, etc
    document_url TEXT,
    last_updated DATE,
    document_scope TEXT[], -- zones this document covers
    complexity_level INTEGER DEFAULT 3, -- 1-5 scale
    created_at TIMESTAMP DEFAULT NOW()
);

-- Provision content for search and navigation
CREATE TABLE research_assistant.provisions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES research_assistant.documents(id),
    clause_reference VARCHAR(50),
    section_header TEXT,
    provision_text TEXT NOT NULL,
    provision_type VARCHAR(50), -- setback, height, heritage, etc
    page_number INTEGER,
    
    -- Keywords for searchability
    keywords TEXT[], -- extracted key terms
    zone_mentions TEXT[], -- zones explicitly mentioned
    development_types TEXT[], -- dwelling, commercial, etc
    
    -- Complexity indicators
    requires_specialist BOOLEAN DEFAULT FALSE,
    complexity_keywords TEXT[], -- "heritage", "flood", "contaminated"
    
    -- Navigation helpers
    related_clauses TEXT[], -- cross-references
    supersedes TEXT[], -- which clauses this overrides
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document relationships (which docs to read together)
CREATE TABLE research_assistant.document_relationships (
    id SERIAL PRIMARY KEY,
    primary_document_id INTEGER REFERENCES research_assistant.documents(id),
    related_document_id INTEGER REFERENCES research_assistant.documents(id),
    relationship_type VARCHAR(50), -- 'supersedes', 'complements', 'references'
    relevance_score DECIMAL(3,2) DEFAULT 0.5,
    notes TEXT
);

-- Planning complexity indicators
CREATE TABLE research_assistant.complexity_indicators (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(100) NOT NULL,
    category VARCHAR(50), -- heritage, environmental, infrastructure
    complexity_weight DECIMAL(3,2) DEFAULT 1.0,
    requires_specialist BOOLEAN DEFAULT FALSE,
    specialist_type VARCHAR(100), -- heritage consultant, traffic engineer
    description TEXT
);

-- Zone-document mapping (what docs apply to which zones)
CREATE TABLE research_assistant.zone_document_matrix (
    id SERIAL PRIMARY KEY,
    zone_code VARCHAR(10) NOT NULL,
    document_id INTEGER REFERENCES research_assistant.documents(id),
    applicability VARCHAR(20) DEFAULT 'applies', -- applies, sometimes, never
    confidence DECIMAL(3,2) DEFAULT 0.8,
    notes TEXT
);

-- Search optimization
CREATE INDEX idx_provisions_text ON research_assistant.provisions USING gin(to_tsvector('english', provision_text));
CREATE INDEX idx_provisions_keywords ON research_assistant.provisions USING gin(keywords);
CREATE INDEX idx_provisions_zones ON research_assistant.provisions USING gin(zone_mentions);
CREATE INDEX idx_provisions_dev_types ON research_assistant.provisions USING gin(development_types);

-- Populate complexity indicators
INSERT INTO research_assistant.complexity_indicators 
(keyword, category, complexity_weight, requires_specialist, specialist_type) 
VALUES
('heritage', 'heritage', 2.0, TRUE, 'heritage consultant'),
('conservation area', 'heritage', 2.0, TRUE, 'heritage consultant'), 
('flood', 'environmental', 1.8, TRUE, 'flood consultant'),
('contaminated', 'environmental', 2.2, TRUE, 'contamination consultant'),
('traffic', 'infrastructure', 1.5, TRUE, 'traffic engineer'),
('acoustic', 'infrastructure', 1.3, TRUE, 'acoustic consultant'),
('geotechnical', 'infrastructure', 1.7, TRUE, 'geotechnical engineer'),
('bushfire', 'environmental', 1.9, TRUE, 'bushfire consultant'),
('affordable housing', 'policy', 1.6, FALSE, NULL),
('design excellence', 'design', 1.4, FALSE, NULL);