/**
 * Setback Calculation Helpers
 *
 * Utility functions for setback data processing and classification.
 */

/**
 * Legal authority levels in NSW planning hierarchy
 */
export type AuthorityLevel = 'SEPP' | 'LEP' | 'DCP';

/**
 * Development type classifications
 */
export type DevelopmentType =
  | 'dwelling_house'
  | 'dual_occupancy'
  | 'multi_dwelling_housing'
  | 'residential_flat_building'
  | 'shop_top_housing'
  | 'general';

/**
 * Correctly classify authority level from source string
 */
export function getAuthorityLevel(source: string): AuthorityLevel {
  const sourceUpper = source.toUpperCase();

  if (sourceUpper.includes('SEPP')) return 'SEPP';
  if (sourceUpper.includes('LEP') && !sourceUpper.includes('DCP')) return 'LEP';
  return 'DCP'; // Most provisions are DCP level
}

/**
 * Get legal precedence value (lower = higher priority)
 */
export function getAuthorityPrecedence(authority: AuthorityLevel): number {
  const precedence: Record<AuthorityLevel, number> = {
    'SEPP': 1,
    'LEP': 2,
    'DCP': 3
  };
  return precedence[authority];
}

/**
 * Identify development type from source text and provision content
 */
export function identifyDevelopmentType(source: string, text?: string): DevelopmentType {
  const combined = `${source} ${text || ''}`.toLowerCase();

  if (combined.includes('multi dwelling') || combined.includes('multi-dwelling')) {
    return 'multi_dwelling_housing';
  }
  if (combined.includes('residential flat') || combined.includes('rfb')) {
    return 'residential_flat_building';
  }
  if (combined.includes('dwelling house') || combined.includes('single dwelling')) {
    return 'dwelling_house';
  }
  if (combined.includes('dual occupancy')) {
    return 'dual_occupancy';
  }
  if (combined.includes('shop top') || combined.includes('shoptop')) {
    return 'shop_top_housing';
  }

  return 'general';
}

/**
 * Check if a setback value is realistic (filter data errors)
 */
export function isRealisticSetback(value: number, boundaryType: string): boolean {
  // Maximum realistic setback values by boundary type
  const maxSetbacks: Record<string, number> = {
    'front': 20,
    'side': 15,
    'rear': 20,
    'default': 50
  };

  const maxValue = maxSetbacks[boundaryType.toLowerCase()] || maxSetbacks['default'];
  return value > 0 && value <= maxValue;
}

/**
 * Transform raw setback data to standardized format
 */
export interface RawSetbackData {
  boundary_type: string;
  required_setback: number;
  confidence: number;
  legal_source: string;
  clause_reference: string;
  provision_id?: number;
  legal_authority?: {
    primary_authority?: string;
    secondary_authority?: string;
  };
  domain_classification?: string;
  cross_contamination_checked?: boolean;
  contextual_requirements?: string;
  provision_text?: string;
}

export interface TransformedSetback {
  boundary_type: string;
  development_type: DevelopmentType;
  value: number;
  setback_distance: number;
  required_setback: number;
  unit: string;
  confidence: number;
  confidence_score: number;
  rule_source: string;
  clause_reference: string;
  legal_source: string;
  authority: AuthorityLevel;
  precedence: number;
  provision_id?: number;
  legal_authority?: object;
  domain_classification?: string;
  cross_contamination_checked?: boolean;
  full_text?: string;
}

/**
 * Transform a raw setback into standardized format
 */
export function transformSetback(setback: RawSetbackData): TransformedSetback | null {
  // Filter out unrealistic values (likely data errors)
  if (!isRealisticSetback(setback.required_setback, setback.boundary_type)) {
    console.warn(`[Setback Helper] Filtering unrealistic value: ${setback.required_setback}m for ${setback.boundary_type}`);
    return null;
  }

  const devType = identifyDevelopmentType(setback.legal_source, setback.provision_text);
  const authority = getAuthorityLevel(
    setback.legal_authority?.secondary_authority || setback.legal_source || 'DCP'
  );

  return {
    boundary_type: setback.boundary_type,
    development_type: devType,
    value: setback.required_setback,
    setback_distance: setback.required_setback,
    required_setback: setback.required_setback,
    unit: 'meters',
    confidence: setback.confidence,
    confidence_score: setback.confidence,
    rule_source: setback.legal_source,
    clause_reference: setback.clause_reference,
    legal_source: setback.legal_source,
    authority,
    precedence: getAuthorityPrecedence(authority),
    provision_id: setback.provision_id,
    legal_authority: setback.legal_authority,
    domain_classification: setback.domain_classification,
    cross_contamination_checked: setback.cross_contamination_checked,
    full_text: setback.contextual_requirements || setback.provision_text
  };
}

/**
 * Group setbacks by development type
 */
export function groupSetbacksByDevType(
  setbacks: TransformedSetback[]
): Record<DevelopmentType | string, TransformedSetback[]> {
  return setbacks.reduce((acc, setback) => {
    const devType = setback.development_type || 'general';
    if (!acc[devType]) {
      acc[devType] = [];
    }
    acc[devType].push(setback);
    return acc;
  }, {} as Record<string, TransformedSetback[]>);
}

/**
 * Determine the controlling authority from a list of setbacks
 */
export function determineControllingAuthority(
  setbacks: Array<{ legal_authority?: { primary_authority?: string } }>
): AuthorityLevel {
  const authorities = [...new Set(
    setbacks.map(r => r.legal_authority?.primary_authority || 'DCP')
  )];

  if (authorities.includes('SEPP')) return 'SEPP';
  if (authorities.includes('LEP')) return 'LEP';
  return 'DCP';
}
