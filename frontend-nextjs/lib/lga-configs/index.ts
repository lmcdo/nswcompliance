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
import waverleyConfig from './waverley.json';
import woollahraConfig from './woollahra.json';
import cityOfSydneyConfig from './city-of-sydney.json';
import kuRingGaiConfig from './ku-ring-gai.json';
import { LGAConfig, validateLGAConfig, LGAConfigValidationError } from './schema';

/**
 * LGA Configuration Registry
 * Maps LGA IDs to their configuration objects
 */
const LGA_REGISTRY: Record<string, LGAConfig> = {
  inner_west: innerWestConfig as LGAConfig,
  waverley: waverleyConfig as LGAConfig,
  woollahra: woollahraConfig as LGAConfig,
  city_of_sydney: cityOfSydneyConfig as LGAConfig,
  ku_ring_gai: kuRingGaiConfig as LGAConfig,
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
  // Waverley suburbs
  'waverley council': 'waverley',
  'bondi': 'waverley',
  'bondi beach': 'waverley',
  'bondi junction': 'waverley',
  'bronte': 'waverley',
  'clovelly': 'waverley',
  'dover heights': 'waverley',
  'north bondi': 'waverley',
  'tamarama': 'waverley',
  'queens park': 'waverley',
  // Woollahra suburbs
  'woollahra council': 'woollahra',
  'paddington': 'woollahra',
  'double bay': 'woollahra',
  'watsons bay': 'woollahra',
  'rose bay': 'woollahra',
  'bellevue hill': 'woollahra',
  'point piper': 'woollahra',
  'edgecliff': 'woollahra',
  // City of Sydney suburbs
  'city of sydney council': 'city_of_sydney',
  'sydney city': 'city_of_sydney',
  'surry hills': 'city_of_sydney',
  'glebe': 'city_of_sydney',
  'chippendale': 'city_of_sydney',
  'pyrmont': 'city_of_sydney',
  'ultimo': 'city_of_sydney',
  'darlinghurst': 'city_of_sydney',
  'redfern': 'city_of_sydney',
  'haymarket': 'city_of_sydney',
  'alexandria': 'city_of_sydney',
  'erskineville': 'city_of_sydney',
  'eveleigh': 'city_of_sydney',
  // Ku-ring-gai suburbs
  'ku-ring-gai council': 'ku_ring_gai',
  'ku ring gai': 'ku_ring_gai',
  'gordon': 'ku_ring_gai',
  'turramurra': 'ku_ring_gai',
  'pymble': 'ku_ring_gai',
  'wahroonga': 'ku_ring_gai',
  'st ives': 'ku_ring_gai',
  'killara': 'ku_ring_gai',
  'lindfield': 'ku_ring_gai',
  'roseville': 'ku_ring_gai',
  'warrawee': 'ku_ring_gai',
  'north turramurra': 'ku_ring_gai',
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
 * Get LGA config from a document ID string
 * Scans all registered LGAs to find a match based on document ID patterns
 */
export function getConfigFromDocumentId(documentId: string): LGAConfig | null {
  const lower = documentId.toLowerCase();
  for (const [lgaId, config] of Object.entries(LGA_REGISTRY)) {
    const lgaLower = (config.name || lgaId).toLowerCase().replace(/\s+/g, '_');
    if (lower.includes(lgaLower) || lower.includes(lgaLower.replace(/_/g, ''))) {
      return config;
    }
    // Check former councils / aliases
    const formerCouncils = config.former_councils;
    if (formerCouncils) {
      for (const council of formerCouncils) {
        if (lower.includes(council.toLowerCase())) {
          return config;
        }
      }
    }
  }
  // Fallback: match by alias
  for (const [alias, lgaId] of Object.entries(LGA_ALIASES)) {
    if (lower.includes(alias.replace(/\s+/g, '_')) || lower.includes(alias)) {
      const config = LGA_REGISTRY[lgaId];
      if (config) return config;
    }
  }
  return null;
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
