// types/database.ts
export interface DevelopmentControl {
 id: number;
 provision_id: number;
 control_type: string;
 control_subtype?: string;
 value_numeric?: number;
 value_text?: string;
 unit?: string;
 zone_applicable?: string;
 conditions?: string;
 confidence_score: number;
 extraction_method: string;
 provision_text?: string;
 document_id?: string;
 // NSW Planning Authority Information (added for hierarchical queries)
 authority_level?: string;
 legal_precedence?: number; 
 can_be_varied?: boolean;
}

export interface QuantitativeStandard {
 id: number;
 provision_id: number;
 numeric_value: number;
 unit: string;
 qualifier: 'minimum' | 'maximum' | 'exactly';
 context: string;
 confidence_score: number;
 raw_text: string;
 manual_verified: boolean;
 created_timestamp: string;
 provision_text?: string;
 document_id?: string;
}

export interface KGRelationship {
 id: number;
 subject_text: string;
 predicate: string;
 object_text: string;
 subject_entity_id?: number;
 object_entity_id?: number;
 relationship_context?: string;
 document_id: string;
 page_number?: number;
 section_header?: string;
 confidence_score: number;
 original_ref_type?: string;
 original_ref_id?: number;
 extraction_timestamp: string;
}

export interface RegulatoryProvision {
 id: number;
 provision_text: string;
 document_id: string;
 page_number?: number;
 section_header?: string;
 provision_number?: string;
 provision_type?: string;
 confidence_score: number;
 extraction_method: string;
 created_timestamp: string;
}

export interface DevelopmentPathway {
 id: number;
 development_type: string;
 zone: string;
 qualification_criteria: string; // JSON string
 pathway_type: 'exempt' | 'cdc' | 'da';
 confidence_score: number;
 source_provision_ids: string;
 manual_verified: boolean;
 created_timestamp: string;
}