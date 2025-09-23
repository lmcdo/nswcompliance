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
