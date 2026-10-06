// types/setback.ts
export interface SetbackResult {
 boundary_type: 'front' | 'rear' | 'side_left' | 'side_right' | 'side';
 required_setback: number; // meters to 2 decimal places
 buildable_depth?: number;
 reasoning: string;
 confidence: number; // 0-1
 database_source?: string;
 precision_level: 'centimeter' | 'meter' | 'approximate' | 'legislative_clause';
 // Enhanced legislative information from Python engine
 legal_source?: string; // Full document source
 clause_reference?: string; // Specific clause reference
 authority?: 'SEPP' | 'LEP' | 'DCP'; // Authority level
 authority_level?: string; // 'SEPP - State Policy', 'LEP - Local Environmental Plan', 'DCP - Development Control Plan' 
 legal_precedence?: number; // 1 = SEPP (highest), 2 = LEP, 3 = DCP
 precedence?: number; // Alias for legal_precedence
 can_be_varied?: boolean; // Whether this control can be varied under Clause 4.6
 // PRP-K3 Enhanced Citation and Explanation Fields
 full_clause_text?: string; // Full text of the regulatory clause
 document_section?: string; // Document section reference
 page_number?: number; // Page number in source document
 authority_explanation?: string; // Explanation of legal authority
 legal_context?: string; // Context about what this setback controls
 conditions?: string; // Special conditions or qualifiers
 unit?: string; // Unit of measurement (usually 'm')

 // Phase 1A Enhanced Domain Classification and Legal Authority
 domain_classification?: 'RESIDENTIAL_BUILDINGS' | 'COMMERCIAL_BUILDINGS' | 'INDUSTRIAL_BUILDINGS' | 'SIGNAGE_ADVERTISING' | 'PARKING_TRANSPORT' | 'HERITAGE_CONSERVATION' | 'ENVIRONMENTAL_PROTECTION' | 'INFRASTRUCTURE_UTILITIES' | 'GENERAL_PROVISIONS';
 relevance_score?: number; // 0-1, measures how relevant this provision is to the query
 cross_contamination_checked?: boolean; // Whether cross-domain contamination was prevented
 legal_authority?: {
 primary_authority: string; // "Inner West LEP 2022"
 secondary_authority: string; // "Marrickville DCP 2011"
 clause_reference: string; // "4.2.4.3 Building setbacks"
 amendment_reference: string; // "IWLEP 2022 amendments"
 document_source: string; // Full document ID
 override_authority?: string; // SEPP override if applicable
 };
 zone_applicability?: string; // The specific zone this applies to (R2, R3, etc.)
 provision_id?: number;
}

/**
 * Buildable-area figures, each independently measurable or not.
 *
 * `null` means NOT MEASURED, and is distinct from 0, which is a measurement.
 * Until 2026-10-06 every field was a bare `number`, so the zone-only endpoint
 * filled them with a lot area invented from the zone (500 m2 for R2, 400 m2
 * otherwise) multiplied by a flat 0.6 — neither derived from the setbacks it had
 * just queried. `unavailable_reason` carries why, for display.
 */
export interface BuildableAreaAnalysis {
 total_lot_area: number | null;
 buildable_area: number | null;
 buildable_percentage: number | null;
 setback_area_lost: number | null;
 note?: string; // Optional explanatory note
 unavailable_reason?: string; // Why the null fields could not be measured
}

/**
 * Both optional fields are optional at the endpoint too — its zod schema has
 * always had `lot_geometry` and `lot_area` optional, while this interface
 * declared them required. Callers therefore filled them to satisfy the compiler:
 * `lot_area` with an uncorrected shoelace, `property_zone` with a literal 'R2'.
 * Omit a field rather than inventing a value for it.
 */
export interface SetbackCalculationRequest {
 property_id: number;
 lot_geometry?: import('./property').LotGeometry;
 property_zone: string;
 lot_area?: number;
}

export interface SetbackCalculationResponse {
 success: boolean;
 setback_results: SetbackResult[];
 buildable_area_analysis: BuildableAreaAnalysis;
 precision_level: string;
 processing_method: string;
 processing_time_ms: number;
 error?: string;
}

export interface BoundaryLine {
 start: { x: number; y: number };
 end: { x: number; y: number };
 length: number;
 bearing: number;
 boundary_type: string;
}

export interface SetbackRequirement {
 boundary_type: string;
 distance: number; // meters
 qualifier: 'minimum' | 'maximum' | 'exactly';
 confidence: number;
 source_provision: string;
 reasoning?: string;
 // NSW Planning Authority Information
 authority_level?: string; // 'SEPP - State Policy', 'LEP - Local Environmental Plan', 'DCP - Development Control Plan'
 legal_precedence?: number; // 1 = SEPP (highest), 2 = LEP, 3 = DCP
 can_be_varied?: boolean; // Whether this control can be varied under Clause 4.6 or design flexibility
}