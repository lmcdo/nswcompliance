/**
 * TypeScript types for Provision Search - PostgreSQL Migration
 * Replaces Python subprocess types with proper TypeScript definitions
 */

export interface ProvisionSearchFilters {
  documentTypes?: string[];
  categories?: string[];
  zones?: string[];
  developmentTypes?: string[];
  limit?: number;
}

export interface ProvisionSearchResult {
  id: number;
  ref_number: string;
  provision_text: string;
  document_id: string;
  provision_type: string;
  authority_level: 'SEPP' | 'LEP' | 'DCP';
  zone?: string;
  development_type?: string;
  page_number?: number;
  confidence_score?: number;
}

export interface ProvisionSearchResponse {
  provisions: ProvisionSearchResult[];
  total_count: number;
  search_metadata: {
    query: string;
    filters_applied: ProvisionSearchFilters;
    search_time_ms: number;
    data_source: string;
    performance_improvement?: string;
  };
}

export interface ProvisionSearchError {
  error: string;
  code: string;
  details?: any;
  fallback_available: boolean;
}