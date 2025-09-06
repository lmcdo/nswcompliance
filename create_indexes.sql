-- CRITICAL: Add indexes for fast compliance queries

-- Indexes for regulatory_provisions_clean
CREATE INDEX IF NOT EXISTS idx_reg_prov_clean_doc_id ON regulatory_provisions_clean(document_id);
CREATE INDEX IF NOT EXISTS idx_reg_prov_clean_type ON regulatory_provisions_clean(provision_type);
CREATE INDEX IF NOT EXISTS idx_reg_prov_clean_page ON regulatory_provisions_clean(page_number);
CREATE INDEX IF NOT EXISTS idx_reg_prov_clean_text ON regulatory_provisions_clean(provision_text);

-- Indexes for development_controls
CREATE INDEX IF NOT EXISTS idx_dev_controls_type ON development_controls(control_type);
CREATE INDEX IF NOT EXISTS idx_dev_controls_provision ON development_controls(provision_id);
CREATE INDEX IF NOT EXISTS idx_dev_controls_zone ON development_controls(zone_applicable);

-- Indexes for kg_relationships
CREATE INDEX IF NOT EXISTS idx_kg_rel_subject_entity ON kg_relationships(subject_entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_object_entity ON kg_relationships(object_entity_id);
CREATE INDEX IF NOT EXISTS idx_kg_rel_predicate ON kg_relationships(predicate);
CREATE INDEX IF NOT EXISTS idx_kg_rel_subject_text ON kg_relationships(subject_text);
CREATE INDEX IF NOT EXISTS idx_kg_rel_object_text ON kg_relationships(object_text);

-- Indexes for kg_entities  
CREATE INDEX IF NOT EXISTS idx_kg_entities_name ON kg_entities(entity_name);
CREATE INDEX IF NOT EXISTS idx_kg_entities_type ON kg_entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_kg_entities_doc ON kg_entities(document_id);

-- Indexes for contextual_guidance_real
CREATE INDEX IF NOT EXISTS idx_context_guid_type ON contextual_guidance_real(guidance_type);
CREATE INDEX IF NOT EXISTS idx_context_guid_doc ON contextual_guidance_real(document_id);
CREATE INDEX IF NOT EXISTS idx_context_guid_page ON contextual_guidance_real(page_number);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_dev_controls_type_zone ON development_controls(control_type, zone_applicable);
CREATE INDEX IF NOT EXISTS idx_kg_rel_predicate_subject ON kg_relationships(predicate, subject_text);