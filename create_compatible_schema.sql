-- CREATE COMPATIBLE POSTGRESQL SCHEMA
-- Fixes the schema incompatibility issue that caused 4x migration failures
-- This schema accepts SQLite data directly without transformation

-- Create a compatible table that matches SQLite structure
CREATE TABLE IF NOT EXISTS public.regulatory_provisions (
    id SERIAL PRIMARY KEY,
    
    -- Direct SQLite compatibility fields
    zone VARCHAR(10),                    -- Single zone (not array)
    development_type VARCHAR(100),       -- Single dev type (not array)  
    provision_text TEXT,
    ref_number VARCHAR(100),
    document_id VARCHAR(200),
    section_header VARCHAR(200),
    
    -- Additional fields from SQLite
    provision_type VARCHAR(100),
    confidence_score DECIMAL(5,3) DEFAULT 0.85,
    classification_confidence DECIMAL(5,3),
    
    -- Extracted quantitative data
    numeric_value DECIMAL(10,2),
    unit VARCHAR(20),
    boundary_type VARCHAR(50),
    measurement_context VARCHAR(100),
    
    -- Legal hierarchy
    legal_source VARCHAR(200),
    clause_reference VARCHAR(100), 
    authority_level VARCHAR(50),
    legal_precedence INTEGER DEFAULT 3,
    
    -- Metadata
    extraction_method VARCHAR(50) DEFAULT 'sqlite_migration',
    created_at TIMESTAMP DEFAULT NOW(),
    is_current BOOLEAN DEFAULT true
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_zone ON public.regulatory_provisions(zone);
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_dev_type ON public.regulatory_provisions(development_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_boundary ON public.regulatory_provisions(boundary_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_numeric ON public.regulatory_provisions(numeric_value);

-- Create quantitative standards table (compatible)
CREATE TABLE IF NOT EXISTS public.quantitative_standards (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES public.regulatory_provisions(id),
    
    -- Direct SQLite compatibility
    numeric_value DECIMAL(10,2) NOT NULL,
    unit VARCHAR(20),
    qualifier VARCHAR(20) DEFAULT 'minimum',
    context VARCHAR(100),          -- setback_front, setback_rear, etc
    
    -- Quality metrics  
    confidence_score DECIMAL(5,3) DEFAULT 0.85,
    manual_verified BOOLEAN DEFAULT false,
    
    -- Metadata
    raw_text TEXT,
    created_timestamp TIMESTAMP DEFAULT NOW()
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_quantitative_standards_provision ON public.quantitative_standards(provision_id);
CREATE INDEX IF NOT EXISTS idx_quantitative_standards_context ON public.quantitative_standards(context);

-- Create a view that transforms data for the frontend
CREATE OR REPLACE VIEW public.frontend_compatible_provisions AS
SELECT 
    rp.id,
    rp.zone,
    rp.development_type,
    rp.provision_text,
    rp.numeric_value,
    rp.unit,
    rp.boundary_type,
    rp.measurement_context,
    rp.confidence_score,
    rp.legal_source,
    rp.clause_reference,
    rp.authority_level,
    rp.legal_precedence,
    
    -- Create arrays for compatibility with frontend expectations
    CASE WHEN rp.zone IS NOT NULL THEN ARRAY[rp.zone] ELSE NULL END as applicable_zones,
    CASE WHEN rp.development_type IS NOT NULL THEN ARRAY[rp.development_type] ELSE NULL END as applicable_dev_types,
    
    rp.created_at,
    rp.is_current
FROM public.regulatory_provisions rp
WHERE rp.is_current = true;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON public.regulatory_provisions TO postgres;
GRANT SELECT, INSERT, UPDATE ON public.quantitative_standards TO postgres;
GRANT SELECT ON public.frontend_compatible_provisions TO postgres;
GRANT USAGE ON SEQUENCE regulatory_provisions_id_seq TO postgres;
GRANT USAGE ON SEQUENCE quantitative_standards_id_seq TO postgres;

-- Verification queries
-- SELECT COUNT(*) FROM public.regulatory_provisions;
-- SELECT zone, COUNT(*) FROM public.regulatory_provisions WHERE zone IS NOT NULL GROUP BY zone ORDER BY count DESC;
-- SELECT * FROM public.frontend_compatible_provisions LIMIT 5;