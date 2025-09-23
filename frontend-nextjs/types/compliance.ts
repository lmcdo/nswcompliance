// types/compliance.ts
export interface ExplanationRequest {
 requirement_type: 'height' | 'fsr' | 'setback' | 'heritage' | 'vegetation';
 property_context?: Record<string, any>;
}

export interface ExplanationResponse {
 success: boolean;
 why_exists: string;
 what_protects: string;
 confidence: 'HIGH' | 'MEDIUM' | 'LOW';
 source_count: number;
 database_relationships_used: string[];
 error?: string;
}

export interface HeritageRequest {
 property_id: number;
 zone: string;
 heritage_overlays?: string[];
}

export interface HeritageResponse {
 success: boolean;
 heritage_status: string;
 applicable_controls: number;
 key_protections: string[];
 controls_detail: Array<{
 requirement: string;
 confidence: number;
 source: string;
 provision: string;
 }>;
 confidence_assessment: string;
 error?: string;
}

export interface PathwayRequest {
 property_data: import('./property').PropertyData;
 development_intent: {
 type: 'renovation' | 'addition' | 'new_dwelling' | 'subdivision';
 estimated_cost?: number;
 height?: number;
 fsr?: number;
 site_coverage?: number;
 };
}

export interface PathwayResponse {
 success: boolean;
 recommended_pathway: 'EXEMPT' | 'CDC' | 'DA';
 development_type: string;
 qualification_criteria: Record<string, any>;
 confidence: number;
 timeline: string;
 cost_estimate: string;
 requirements: string[];
 next_steps?: string[];
 error?: string;
}