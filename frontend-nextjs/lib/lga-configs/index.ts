/**
 * LGA Configuration Registry and Loader
 *
 * Central registry for all configured LGAs. Add new LGA configs here
 * as JSON files are created following the schema.
 *
 * @see schema.ts for config structure
 * @see docs/ARCHITECTURE-LGA-EXPANSION.md for setup guide
 */

import innerWestConfig from './inner-west.json';
import { LGAConfig, validateLGAConfig, LGAConfigValidationError } from './schema';

/**
 * LGA Configuration Registry
 * Maps LGA IDs to their configuration objects
 */
const LGA_REGISTRY: Record<string, LGAConfig> = {
  inner_west: innerWestConfig as LGAConfig,
  // Add new LGA configs here as they're created:
  // 'sydney': sydneyConfig as LGAConfig,
  // 'woollahra': woollahraConfig as LGAConfig,
};

/**
 * LGA Name Aliases (for fuzzy matching)
 * Maps alternative names/spellings to canonical LGA IDs
 */
const LGA_ALIASES: Record<string, string> = {
  'inner west': 'inner_west',
  'innerwest': 'inner_west',
  'inner west council': 'inner_west',
  // Amalgamated councils can be looked up by former council names
  'ashfield': 'inner_west',
  'leichhardt': 'inner_west',
  'marrickville': 'inner_west',
};

/**
 * Validate all LGA configs at module load time (fail-fast)
 */
for (const [lgaId, config] of Object.entries(LGA_REGISTRY)) {
  try {
    validateLGAConfig(config);
  } catch (error) {
    if (error instanceof LGAConfigValidationError) {
      console.error(`[LGA Config] Validation failed for '${lgaId}':`, error.message);
      throw error;
    }
    throw error;
  }
}

/**
 * Get LGA configuration by ID
 * @throws LGAConfigValidationError if LGA not found
 */
export function getLGAConfig(lgaId: string): LGAConfig {
  const normalizedId = lgaId.toLowerCase().replace(/\s+/g, '_');
  const config = LGA_REGISTRY[normalizedId];

  if (!config) {
    throw new LGAConfigValidationError(
      lgaId,
      `LGA config not found. Available LGAs: ${Object.keys(LGA_REGISTRY).join(', ')}`
    );
  }

  return config;
}

/**
 * Try to get LGA configuration, returning null if not found
 * Use this when LGA might not be configured yet (graceful degradation)
 */
export function tryGetLGAConfig(lgaId: string): LGAConfig | null {
  try {
    return getLGAConfig(lgaId);
  } catch {
    return null;
  }
}

/**
 * Detect LGA from a name string (handles aliases and fuzzy matching)
 *
 * @example
 * detectLGAFromName('Inner West Council') // => 'inner_west'
 * detectLGAFromName('Ashfield') // => 'inner_west' (former council)
 */
export function detectLGAFromName(name: string): string | null {
  const normalized = name.toLowerCase().trim();

  // Direct registry match
  if (LGA_REGISTRY[normalized.replace(/\s+/g, '_')]) {
    return normalized.replace(/\s+/g, '_');
  }

  // Alias match
  if (LGA_ALIASES[normalized]) {
    return LGA_ALIASES[normalized];
  }

  // Partial match (e.g., "Inner West Council" contains "inner west")
  for (const [alias, lgaId] of Object.entries(LGA_ALIASES)) {
    if (normalized.includes(alias) || alias.includes(normalized)) {
      return lgaId;
    }
  }

  return null;
}

/**
 * Check if an LGA is configured
 */
export function isLGAConfigured(lgaId: string): boolean {
  return tryGetLGAConfig(lgaId) !== null;
}

/**
 * Get all configured LGA IDs
 */
export function getConfiguredLGAs(): string[] {
  return Object.keys(LGA_REGISTRY);
}

/**
 * Check if LGA is an amalgamated council
 */
export function isAmalgamatedLGA(lgaId: string): boolean {
  const config = tryGetLGAConfig(lgaId);
  return config?.type === 'amalgamated';
}

/**
 * Get former council names for amalgamated LGA
 * Returns empty array for single-council LGAs
 */
export function getFormerCouncils(lgaId: string): string[] {
  const config = tryGetLGAConfig(lgaId);
  return config?.former_councils || [];
}

/**
 * Find LGA ID from a former council name
 *
 * @example
 * findLGAByFormerCouncil('Ashfield') // => 'inner_west'
 */
export function findLGAByFormerCouncil(formerCouncil: string): string | null {
  const normalized = formerCouncil.toLowerCase().trim();

  for (const [lgaId, config] of Object.entries(LGA_REGISTRY)) {
    if (config.type === 'amalgamated' && config.former_councils) {
      const match = config.former_councils.find(
        (fc) => fc.toLowerCase() === normalized
      );
      if (match) return lgaId;
    }
  }

  return null;
}

/**
 * Get BASIX area code for an LGA
 */
export function getBasixAreaCode(lgaId: string): string | null {
  const config = tryGetLGAConfig(lgaId);
  return config?.basix.area_code || null;
}

/**
 * Get climate zone for an LGA
 */
export function getClimateZone(lgaId: string): string | null {
  const config = tryGetLGAConfig(lgaId);
  return config?.basix.climate_zone || null;
}

/**
 * Check if LGA requires former council detection from address
 */
export function requiresFormerCouncilDetection(lgaId: string): boolean {
  const config = tryGetLGAConfig(lgaId);
  return config?.former_council_detection?.requires_detection || false;
}

/**
 * Export registry for debugging/testing
 */
export { LGA_REGISTRY, LGA_ALIASES };

/**
 * Export schema types for consumers
 */
export type { LGAConfig, LGAType } from './schema';
export { LGAConfigValidationError } from './schema';
