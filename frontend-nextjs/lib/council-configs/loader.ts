/**
 * Dynamic Council Config Loader
 *
 * Supports loading council configs from:
 * 1. Bundled JSON files (for Inner West - always available)
 * 2. External lga-data directory (for new LGAs)
 * 3. Database (lga_registry table - future)
 *
 * This allows the core codebase to remain clean while supporting
 * unlimited LGAs without code changes.
 */

import type { CouncilConfig } from '../council-config';
import fs from 'fs';
import path from 'path';

// Bundled configs (always available, compiled into the app)
import marrickvilleConfig from './marrickville.json';
import leichhardtConfig from './leichhardt.json';
import ashfieldConfig from './ashfield.json';
import waverleyConfig from './waverley.json';
import woollahraConfig from './woollahra.json';
import cityOfSydneyConfig from './city_of_sydney.json';
import kuRingGaiConfig from './ku_ring_gai.json';

// Cache for loaded configs
const configCache = new Map<string, CouncilConfig>();

// Bundled configs that ship with the app
const BUNDLED_CONFIGS: Record<string, CouncilConfig> = {
  marrickville: marrickvilleConfig as CouncilConfig,
  leichhardt: leichhardtConfig as CouncilConfig,
  ashfield: ashfieldConfig as CouncilConfig,
  waverley: waverleyConfig as CouncilConfig,
  woollahra: woollahraConfig as CouncilConfig,
  city_of_sydney: cityOfSydneyConfig as CouncilConfig,
  ku_ring_gai: kuRingGaiConfig as CouncilConfig,
};

/**
 * Get the path to external LGA data directory
 * Can be configured via environment variable
 */
function getLgaDataPath(): string {
  // Check environment variable first
  if (process.env.LGA_DATA_PATH) {
    return process.env.LGA_DATA_PATH;
  }

  // Default: sibling directory to compliance-engine
  // compliance-engine/../lga-data
  const projectRoot = process.cwd();
  return path.resolve(projectRoot, '..', 'lga-data');
}

/**
 * Load a council config from external lga-data directory
 */
function loadExternalConfig(councilId: string): CouncilConfig | null {
  try {
    const lgaDataPath = getLgaDataPath();
    const configPath = path.join(lgaDataPath, councilId, 'config.json');

    if (!fs.existsSync(configPath)) {
      return null;
    }

    const configJson = fs.readFileSync(configPath, 'utf-8');
    const config = JSON.parse(configJson) as CouncilConfig;

    // Validate required fields
    if (!config.id || !config.name || !config.layerLabels) {
      console.warn(`[Config Loader] Invalid config for ${councilId}: missing required fields`);
      return null;
    }

    console.log(`[Config Loader] Loaded external config for ${councilId}`);
    return config;
  } catch (error) {
    console.warn(`[Config Loader] Failed to load external config for ${councilId}:`, error);
    return null;
  }
}

/**
 * Get all available council IDs (bundled + external)
 */
export function getAvailableCouncils(): string[] {
  const councils = new Set<string>(Object.keys(BUNDLED_CONFIGS));

  // Check for external configs
  try {
    const lgaDataPath = getLgaDataPath();
    if (fs.existsSync(lgaDataPath)) {
      const dirs = fs.readdirSync(lgaDataPath, { withFileTypes: true });
      for (const dir of dirs) {
        if (dir.isDirectory() && !dir.name.startsWith('.')) {
          const configPath = path.join(lgaDataPath, dir.name, 'config.json');
          if (fs.existsSync(configPath)) {
            councils.add(dir.name);
          }
        }
      }
    }
  } catch {
    // External path not available, that's fine
  }

  return Array.from(councils);
}

/**
 * Load council config with fallback chain:
 * 1. Check cache
 * 2. Check bundled configs
 * 3. Try external lga-data directory
 * 4. Return null if not found
 */
export function loadCouncilConfig(councilId: string): CouncilConfig | null {
  const id = councilId.toLowerCase().trim();

  // Check cache
  if (configCache.has(id)) {
    return configCache.get(id)!;
  }

  // Check bundled configs first (fastest)
  if (BUNDLED_CONFIGS[id]) {
    configCache.set(id, BUNDLED_CONFIGS[id]);
    return BUNDLED_CONFIGS[id];
  }

  // Try external config
  const externalConfig = loadExternalConfig(id);
  if (externalConfig) {
    configCache.set(id, externalConfig);
    return externalConfig;
  }

  return null;
}

/**
 * Check if a council has a config available
 */
export function hasCouncilConfig(councilId: string): boolean {
  const id = councilId.toLowerCase().trim();

  // Check bundled
  if (BUNDLED_CONFIGS[id]) return true;

  // Check cache
  if (configCache.has(id)) return true;

  // Check external
  try {
    const lgaDataPath = getLgaDataPath();
    const configPath = path.join(lgaDataPath, id, 'config.json');
    return fs.existsSync(configPath);
  } catch {
    return false;
  }
}

/**
 * Clear the config cache (useful for development/testing)
 */
export function clearConfigCache(): void {
  configCache.clear();
}

/**
 * Get the bundled configs (for cases where external loading isn't available)
 */
export function getBundledConfigs(): Record<string, CouncilConfig> {
  return { ...BUNDLED_CONFIGS };
}
