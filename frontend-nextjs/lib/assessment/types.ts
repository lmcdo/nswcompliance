export interface PropertyData {
 propId: number;
 address: string;
 zone: string;
 lga: string;
 area: string;
 landValue?: string;
 heritage?: boolean;
}

export interface AssessmentContext {
 propertyId?: number;
 developmentType?: string;
 assessmentDate: Date;
 versionId?: number;
}

export interface ComplianceResult {
 provision: string;
 clause: string;
 status: 'compliant' | 'non-compliant' | 'pending';
 details?: string;
 requirement?: string;
}

export interface AssessmentData {
 property?: PropertyData;
 compliance: ComplianceResult[];
 checklist: ComplianceResult[];
 versions: {
 current: string;
 effective: string;
 };
}

export type DevelopmentType =
 | 'dwelling_house'
 | 'dual_occupancy'
 | 'multi_dwelling_housing'
 | 'residential_flat_building'
 | 'commercial_premises'
 | 'retail_premises'
 | 'office_premises'
 | 'industrial'
 | 'warehouse'
 | 'mixed_use';

export interface VersionInfo {
 id: number;
 document_type: string;
 document_identifier: string;
 version_number: string;
 version_status: 'CURRENT' | 'PREVIOUS' | 'ARCHIVED';
 effective_date: string;
 superseded_date?: string;
 document_url?: string;
 change_summary?: string;
 metadata?: Record<string, any>;
 created_at?: string;
 created_by?: string;
}

export interface VersionAwareAssessmentContext extends AssessmentContext {
 useHistoricalVersion?: boolean;
 documentType?: string;
 documentIdentifier?: string;
 selectedVersion?: VersionInfo;
}

export interface VersionAwareComplianceResult extends ComplianceResult {
 version_context?: string;
 version_info?: VersionInfo;
}

// Additional types used by assessment components
export interface ComplianceCheck {
 id: string;
 provision_text: string;
 compliance_status: 'compliant' | 'non_compliant' | 'requires_assessment' | 'not_applicable';
 confidence: number;
 details?: string;
 requirement?: string;
 [key: string]: any;
}

export interface Citation {
 source: string;
 document?: string;
 clause?: string;
 url?: string;
 page?: number;
 [key: string]: any;
}

export interface ComplianceProvision {
 id?: string | number;
 ref_number?: string;
 section_header?: string;
 provision_text?: string;
 document_id?: string;
 [key: string]: any;
}

export interface ProvisionSearchFilters {
 documentType?: string;
 lga?: string;
 zone?: string;
 limit?: number;
 offset?: number;
 userZone?: string;
 [key: string]: any;
}

export interface ProvisionSearchResult {
 provisions: ComplianceProvision[];
 total_count: number;
 search_metadata?: Record<string, any>;
}
