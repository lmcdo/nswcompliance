// types/regulatory.ts
// Types for regulatory data used by AI integration

/**
 * Property context - core property information for regulatory lookups
 */
export interface PropertyContext {
  address: string;
  zone: string;
  lga: string;
  formerCouncil: string;
  precinctId?: string;
  heritage?: {
    isHeritage: boolean;
    heritageType?: string;
    hcaCode?: string;
  };
  lotArea?: number;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

/**
 * LEP capacity data from /api/capacity/calculate
 */
export interface LepCapacityData {
  capacity: {
    maxGFA: number | null;
    gfaSource: string;
    maxHeight: number | null;
    maxFSR: number | null;
    approxStoreys: number | null;
    lotArea: number;
  };
  setbacks: SetbackResult;
  parking: Array<{
    text: string;
    spaces: number;
  }>;
  landscaping: Array<{
    text: string;
    value: number;
    unit: string;
  }>;
  lepClauses: LepClause[];
}

export interface SetbackResult {
  type: 'numeric' | 'prevailing' | 'precinct_specific' | 'mixed' | 'not_available';
  front?: number;
  side?: number;
  rear?: number;
  message?: string;
  method?: string;
  source?: string;
  precinct_name?: string;
  values?: Array<{
    boundary: string;
    value?: number;
    range?: string;
    unit?: string;
    conditional?: boolean;
    condition?: string;
    text: string;
  }>;
  guidance?: Array<{
    boundary: string;
    text: string;
  }>;
}

export interface LepClause {
  clause_number: string;
  clause_title: string;
  requirements: string[];
  applies_to_zones: string[];
}

/**
 * SEPP structured requirements from /api/sepp/structured-requirements
 */
export interface SeppData {
  hasStructuredRequirements: boolean;
  requirements?: SeppRequirement[];
  count?: number;
  developmentType?: string;
  developmentCategory?: string;
  seppId?: string;
  message?: string;
}

export interface SeppRequirement {
  id: number;
  seppId: string;
  seppName: string;
  schedule: string;
  scheduleName: string;
  section: string | null;
  sectionName: string | null;
  developmentTypeCategory: string;
  requirementData: {
    title: string;
    categories: Array<{
      name: string;
      reference: string;
      requirements: Array<Record<string, string>>;
    }>;
  };
  sourceProvisionId: number | null;
  pdfPageImageUrl: string | null;
  pdfPage: number | null;
}

/**
 * DCP provisions from /api/provisions/for-property
 */
export interface DcpData {
  by_layer: DcpLayerResult[];
  by_topic: Record<string, DcpProvision[]>;
  by_toc?: Record<string, DcpTocPart>;
  summary: {
    total_provisions: number;
    layer_1_generic: number;
    layer_2_use_specific: number;
    layer_3_condition: number;
    layer_4_precinct: number;
  };
}

export interface DcpLayerResult {
  layer: 'generic' | 'use_specific' | 'condition' | 'precinct';
  layer_name: string;
  provisions: DcpProvision[];
  count: number;
}

export interface DcpProvision {
  id: number;
  document_id: string;
  provision_text: string;
  v2_dcp_layer: string;
  v2_dcp_part: string;
  v2_topic: string;
  v2_provision_type: string;
  v2_precinct_id: string | null;
  v2_marker: string | null;
  v2_display_behavior: string | null;
  pdf_page: number | null;
  pdf_source_file: string | null;
  pdf_page_image_url: string | null;
  v2_heritage_type?: string | null;
  v2_heritage_element?: string | null;
  v2_heritage_hca?: string | null;
  toc_section_number?: string | null;
  toc_section_title?: string | null;
  layer?: string; // Added during grouping
}

export interface DcpTocPart {
  part_id: string;
  part_name: string;
  provision_count: number;
  sections: Record<string, DcpTocSection>;
}

export interface DcpTocSection {
  section_id: string;
  section_title: string;
  provision_count: number;
  provisions: DcpProvision[];
}

/**
 * Loading state for parallel data fetching
 */
export type LoadingState = 'pending' | 'loading' | 'done' | 'error';

export interface RegulatoryLoadingProgress {
  property: LoadingState;
  lep: LoadingState;
  sepp: LoadingState;
  dcp: LoadingState;
}

/**
 * Full regulatory context for AI queries
 */
export interface FullRegulatoryContext {
  property: PropertyContext | null;
  lepData: LepCapacityData | null;
  seppData: SeppData | null;
  dcpData: DcpData | null;
  isAllDataReady: boolean;
  loadingProgress: RegulatoryLoadingProgress;
  errors: {
    property: string | null;
    lep: string | null;
    sepp: string | null;
    dcp: string | null;
  };
}
