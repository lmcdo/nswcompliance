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
  userZone?: string; // User's zone for Tier 1 ranking boost
}

export interface ProvisionRankingMetadata {
  text_rank: number;
  hierarchy_weight: number;
  quant_boost: number;
  zone_boost: number;
  final_rank: number;
}

export interface ProvisionVersionMetadata {
  regulation_year: number | null;
  amendment_reference: string | null;
  amendment_date: string | null; // ISO date string
  version_status: 'unverified' | 'current' | 'superseded';
  last_verified_date: string; // ISO date string
  days_since_verified: number;
  staleness_level: 'current' | 'caution' | 'stale';
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
  ranking?: ProvisionRankingMetadata; // Tier 1 ranking metadata
  version?: ProvisionVersionMetadata; // Version tracking for certifier compliance
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
    ranking_enabled?: boolean; // Indicates if Tier 1 ranking used
  };
}

export interface ProvisionSearchError {
  error: string;
  code: string;
  details?: any;
  fallback_available: boolean;
}