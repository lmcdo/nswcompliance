/**
 * LGA Configuration Schema
 *
 * Defines the structure for per-LGA configuration data.
 * LGA configs sit between state-level (NSW) and council-level (DCP) configs.
 *
 * @see docs/ARCHITECTURE-LGA-EXPANSION.md for design rationale
 */

/**
 * LGA Type - single council or amalgamated from multiple councils
 */
export type LGAType = 'single' | 'amalgamated';

/**
 * BASIX Area Configuration
 * SEPP (Sustainable Buildings) 2022 divides NSW into BASIX areas
 */
export interface BasixConfig {
  /** BASIX area code (e.g., "Area 5") */
  area_code: string;

  /** Human-readable area name (e.g., "Inner West") */
  area_name: string;

  /** Climate zone number as string (e.g., "56" for Sydney Metro) */
  climate_zone: string;

  /** Water consumption reduction target percentage */
  water_target_percent: number;
}

/**
 * Planning Zone Configuration
 * Defines which NSW standard zones apply to this LGA
 */
export interface PlanningZonesConfig {
  /** Residential zones that permit dwelling houses */
  residential_zones: string[];

  /** Industrial and employment zones */
  industrial_zones: string[];

  /** Zones that permit apartment developments (post-LMR reforms) */
  apartment_permitting_zones: string[];
}

/**
 * SEPP Configuration
 * Defines which State Environmental Planning Policies apply to this LGA
 */
export interface SeppConfig {
  /** List of applicable SEPP identifiers from Planning Portal */
  applicable_sepps: string[];

  /**
   * Optional: Custom SEPP ID mapping if this LGA uses non-standard naming
   * Defaults to NSW-wide mapping from state-config if not provided
   */
  sepp_id_mapping?: Record<string, string>;
}

/**
 * Transport Infrastructure Configuration
 * TOD thresholds and transport-related planning rules
 */
export interface TransportConfig {
  /**
   * TOD (Transit Oriented Development) distance thresholds in meters
   * Most LGAs use standard NSW thresholds, but some may have local variations
   */
  tod_thresholds?: {
    heavy_rail_m: number;
    light_rail_m: number;
    bus_m: number;
  };

  /**
   * Whether this LGA has designated TOD precincts
   * Used to determine if TOD section should be shown
   */
  has_tod_precincts?: boolean;
}

/**
 * Former Council Detection Configuration
 * For amalgamated councils only
 */
export interface FormerCouncilConfig {
  /** Whether this LGA requires former council area detection from address */
  requires_detection: boolean;

  /**
   * Postcode-based mapping: postcode -> council
   * Used for fast initial detection
   */
  postcode_mapping?: Record<string, string>;

  /**
   * Suburb-based mapping: suburb -> council
   * Used when postcode is ambiguous (split postcodes)
   */
  suburb_mapping?: Record<string, string>;
}

/**
 * Complete LGA Configuration
 */
export interface LGAConfig {
  /** Unique LGA identifier (lowercase, hyphenated) */
  id: string;

  /** Official LGA name */
  name: string;

  /** LGA type (single or amalgamated) */
  type: LGAType;

  /** Former council names (for amalgamated councils only) */
  former_councils?: string[];

  /** BASIX area configuration */
  basix: BasixConfig;

  /** Planning zones applicable to this LGA */
  planning: PlanningZonesConfig;

  /** State Environmental Planning Policies applicable to this LGA */
  sepp: SeppConfig;

  /** Transport infrastructure configuration */
  transport?: TransportConfig;

  /** Former council detection (for amalgamated councils) */
  former_council_detection?: FormerCouncilConfig;

  /**
   * Optional: Custom metadata for this LGA
   * Can store LGA-specific settings that don't fit other categories
   */
  metadata?: {
    /** Population (for analytics/prioritization) */
    population?: number;

    /** Area in square kilometers */
    area_km2?: number;

    /** Website URL */
    website_url?: string;

    /** Planning portal URL (if different from NSW PP) */
    planning_portal_url?: string;

    /** Any LGA-specific notes */
    notes?: string;
  };
}

/**
 * LGA Configuration Validation Error
 */
export class LGAConfigValidationError extends Error {
  constructor(lgaId: string, message: string) {
    super(`LGA config validation failed for '${lgaId}': ${message}`);
    this.name = 'LGAConfigValidationError';
  }
}

/**
 * Validate LGA configuration completeness and correctness
 * Throws LGAConfigValidationError if invalid
 */
export function validateLGAConfig(config: LGAConfig): void {
  // Required fields
  if (!config.id || config.id.trim() === '') {
    throw new LGAConfigValidationError(config.id || 'unknown', 'id is required');
  }

  if (!config.name || config.name.trim() === '') {
    throw new LGAConfigValidationError(config.id, 'name is required');
  }

  if (!['single', 'amalgamated'].includes(config.type)) {
    throw new LGAConfigValidationError(config.id, `type must be 'single' or 'amalgamated', got '${config.type}'`);
  }

  // Amalgamated councils must have former_councils
  if (config.type === 'amalgamated' && (!config.former_councils || config.former_councils.length === 0)) {
    throw new LGAConfigValidationError(config.id, 'amalgamated councils must specify former_councils');
  }

  // BASIX validation
  if (!config.basix) {
    throw new LGAConfigValidationError(config.id, 'basix config is required');
  }
  if (!config.basix.area_code || !config.basix.climate_zone) {
    throw new LGAConfigValidationError(config.id, 'basix.area_code and basix.climate_zone are required');
  }

  // Planning zones validation
  if (!config.planning) {
    throw new LGAConfigValidationError(config.id, 'planning config is required');
  }
  if (!config.planning.residential_zones || config.planning.residential_zones.length === 0) {
    throw new LGAConfigValidationError(config.id, 'planning.residential_zones must not be empty');
  }

  // SEPP validation
  if (!config.sepp || !config.sepp.applicable_sepps) {
    throw new LGAConfigValidationError(config.id, 'sepp.applicable_sepps is required');
  }

  // Zone code format validation (basic check)
  const allZones = [
    ...config.planning.residential_zones,
    ...config.planning.industrial_zones,
    ...config.planning.apartment_permitting_zones,
  ];

  for (const zone of allZones) {
    if (!/^[A-Z0-9]+$/.test(zone)) {
      throw new LGAConfigValidationError(
        config.id,
        `Invalid zone code format: '${zone}' (must be uppercase alphanumeric)`
      );
    }
  }
}

/**
 * Type guard: check if config is valid LGAConfig
 */
export function isValidLGAConfig(obj: any): obj is LGAConfig {
  try {
    validateLGAConfig(obj);
    return true;
  } catch {
    return false;
  }
}
