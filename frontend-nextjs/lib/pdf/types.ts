// PDF Export Types

export interface PropertyContext {
  address: string;
  zone: string;
  former_council: string;

  // Heritage
  heritage_status: {
    in_hca: boolean;
    hca_code?: string;
    hca_name?: string;
    heritage_item?: boolean;
    item_name?: string;
    item_number?: string;
  };

  // LEP Controls
  lep_controls?: {
    height?: string;          // e.g., "12m"
    fsr?: string;             // e.g., "1.5:1"
    acid_sulfate_soils?: string;  // e.g., "Class 5" or "Not affected"
    permitted_uses?: string[];  // Permitted uses in zone
    prohibited_uses?: string[]; // Prohibited uses in zone
  };

  // HCA Details
  hca_details?: {
    significance?: string;    // Statement of significance
    key_attributes?: string[];  // Key heritage attributes
    controls?: string[];      // Specific HCA controls
  };

  // Lot Dimensions
  lot_dimensions?: {
    area?: number;            // m²
    frontage?: number;        // m
    depth?: number;           // m
    is_corner?: boolean;
    corner_roads?: string[];  // e.g., ["SHELLEYS LANE", "VICTORIA RD"]
  };

  // NSW Planning Portal Layers (all layers with numeric values)
  planning_portal_layers?: {
    heritage_map?: number | string;
    fsr_map?: number | string;
    height_map?: number | string;
    acid_sulfate_soils_map?: number | string;
    local_aboriginal_land_council?: number | string;
    sepp_requirements?: number | string;
    land_application_map?: number | string;
    regional_plan_boundary?: number | string;
    land_zoning_map?: number | string;
    tree_canopy_2019?: number | string;
    tree_canopy_2022?: number | string;
    tree_canopy_coverage_class?: string;
    terrestrial_biodiversity_map?: number | string;
  };

  // Environmental Constraints (from NSW Planning Portal + environmental datasets)
  environmental_constraints?: {
    flood_prone: boolean;
    bushfire_prone: boolean;
    acid_sulfate_soils?: string;       // e.g., "Class 5"
    anef_zone: boolean;
    anef_level?: number;
    anef_code?: string;
    mine_subsidence: boolean;
    mine_subsidence_district?: string;
    landslide_risk: boolean;
    contaminated_land: boolean;
    contaminated_site_name?: string;
    contaminated_site_distance?: number;
    contaminated_management_class?: string;
    contaminated_type?: string;
    landslide_risk_class?: string;
    drinking_water_catchment: boolean;
    terrestrial_biodiversity: boolean;
    coastal_management: boolean;
    coastal_zones?: string[];
  };

  // Additional Local Provisions (clause 6.x items)
  additional_local_provisions?: string[];  // e.g., ["Clause 6.1: Acid sulfate soils", "Clause 6.2: Earthworks"]

  // Development description (from DA session — user-entered)
  development_description?: string;

  // Pattern Book CDC Eligibility
  pattern_book_cdc?: {
    status: 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE';
    exclusion_count: number;  // 217 total exclusion triggers
    numeric_standards_count: number;  // 199 total numeric standards
    override_rules_count: number;  // 9 total override rules
    blockers?: string[];  // e.g., ["Heritage item", "Lot area below minimum"]
    pathway_timeframe?: string;  // e.g., "10-day approval"
  };

  // Pathway Comparison
  pathway_summary?: {
    recommended_pathway: string;  // e.g., "Pattern Book CDC"
    pathways: {
      name: string;  // e.g., "Pattern Book CDC"
      status: 'Available' | 'Not Available' | 'Conditional';
      timeframe: string;  // e.g., "10 days"
      notes?: string;  // e.g., "Subject to exclusion checks"
    }[];
  };
}

export interface ProvisionForPDF {
  id: number;
  provision_text: string;
  v2_marker: string;
  v2_topic: string;
  v2_structural_category?: string;
  document_name: string;
  v2_dcp_part: string;
  section_header?: string;
  pdf_page?: number;              // Extraction page number (fallback)
  pdf_printed_page: number;       // Human-readable page number
  v2_is_actionable?: boolean;
  zone_applicability?: string;
  ref_number?: string;
  da_response?: string;
  da_status?: 'complies' | 'varies' | 'not_applicable';
}

export interface ProvisionGroup {
  topic: string;
  topicLabel: string;
  count: number;
  provisions: ProvisionForPDF[];
  subtopics?: ProvisionSubgroup[];
}

export interface ProvisionSubgroup {
  subtopic: string;
  count: number;
  provisions: ProvisionForPDF[];
}

export interface ReportMetadata {
  reportDate: string;
  reportId: string;
  totalProvisions: number;
}
