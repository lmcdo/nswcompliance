/**
 * TypeScript types for Live Compliance - PostgreSQL Migration
 */

export interface ComplianceCalculationRequest {
  address: string;
  proposed_development: {
    gross_floor_area: number;
    site_area: number;
    building_height: number;
    storeys: number;
    site_coverage_percentage?: number;
  };
  development_type?: string;
}

export interface ComplianceResult {
  compliant: boolean;
  actual_value: number;
  limit_value: number;
  margin?: number;
  units: string;
  confidence: number;
  data_source: string;
  calculation_time_ms: number;
}

export interface LiveComplianceResponse {
  address: string;
  property_zone: string;
  fsr_compliance: ComplianceResult;
  height_compliance: ComplianceResult;
  site_coverage_compliance?: ComplianceResult;
  overall_compliance: {
    all_compliant: boolean;
    major_issues: number;
    minor_issues: number;
  };
  calculation_metadata: {
    total_time_ms: number;
    data_sources: string[];
    implementation: 'postgresql' | 'subprocess';
  };
}