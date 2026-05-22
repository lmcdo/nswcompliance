/**
 * Council-Specific Configuration
 *
 * Loads council configurations from JSON files for multi-LGA support.
 * Each council has its own JSON config defining DCP structure and UI behavior.
 *
 * Configuration files location: lib/council-configs/{council-id}.json
 */

// Import council configs from JSON files
import marrickvilleConfig from './council-configs/marrickville.json';
import leichhardtConfig from './council-configs/leichhardt.json';
import ashfieldConfig from './council-configs/ashfield.json';
import waverleyConfig from './council-configs/waverley.json';
import woollahraConfig from './council-configs/woollahra.json';
import cityOfSydneyConfig from './council-configs/city_of_sydney.json';
import kuRingGaiConfig from './council-configs/ku_ring_gai.json';

export interface CategoryGroup {
  label: string;
  categories: string[];  // LLM categories in this group
  showSubcategories: boolean;  // Whether to show individual categories
  priority: number;  // Display order (lower = higher priority)
}

export interface SetbackGuidance {
  boundary: string;
  text: string;
}

export interface SetbackFallback {
  type: 'numeric' | 'prevailing' | 'not_available';
  message: string;
  method?: string;
  guidance?: SetbackGuidance[];
}

/**
 * DCP Structure Model — three patterns found across NSW councils.
 *
 * dev_type_organized  — Primary chapters keyed to dev categories (Ashfield Chapter F).
 *                       Dev type dropdown = chapter selector. Auto-dismiss of off-category
 *                       chapters is architecturally defensible.
 *
 * zone_organized      — Top-level parts keyed to zone tier (Marrickville Parts 4/5/6).
 *                       Zone gates chapter loading (already done by API layer system).
 *                       Universal topic sections (e.g. Part 2) always load regardless of
 *                       dev type. Dev type = sub-part selector + relevance sort only.
 *
 * topic_universal     — Almost all chapters apply to all dev types (Leichhardt).
 *                       Only explicit dev-type-specific parts (e.g. Part F Food) gated.
 *                       Dev type = relevance sort only. Planner must address or N/A
 *                       every section in universalPartKeys.
 *
 * For new LGA onboarding: read the DCP table of contents, classify each top-level
 * chapter as universal / zone_structural / devtype_structural / condition / precinct,
 * then set this field and populate universalPartKeys + devTypeGatedPartKeys.
 */
// Not a fixed enum — new councils may have hybrid or novel structures.
// Use as a human-readable label only. Business logic branches on
// universalPartKeys and devTypeGatedPartKeys, not on this field.
// Known values: 'dev_type_organized' (Ashfield), 'zone_organized' (Marrickville),
// 'topic_universal' (Leichhardt). Future councils may require different descriptions.
export type DcpStructureModel = string;

export interface CouncilConfig {
  id: string;
  name: string;
  parentLGA?: string | null;  // For merged councils (e.g., Inner West)
  dcpCitation: string;
  /** Full name of the applicable LEP for instrument citation in SEE documents e.g. 'Inner West Local Environmental Plan 2022' */
  lepCitation?: string;
  dcpExplanation: string;
  totalProvisions: number;
  primaryLayer: 'generic' | 'precinct' | 'condition' | 'use_specific';
  zoneFilterEffective: boolean;
  devTypeFilterEffective: boolean;
  devTypeNote?: string; // Displayed when dev type has no effect

  /**
   * DCP structure model — determines how DA mode uses dev type.
   * See DcpStructureModel above. Required for all councils.
   */
  dcpStructureModel: DcpStructureModel;

  /**
   * Part keys (matching v2_dcp_part values in DB) that are ALWAYS in scope
   * for every DA on this council — the planner must address or explicitly
   * mark N/A. The system must never auto-dismiss these based on dev type.
   * Zone/heritage/precinct gating still applies to chapters not in this list.
   */
  universalPartKeys: string[];

  /**
   * Part keys where dev type is a legitimate structural gate — the DCP document
   * itself partitions these by dev category. Auto-dismiss of non-matching
   * part keys is architecturally defensible.
   * Empty for zone_organized and topic_universal councils.
   */
  devTypeGatedPartKeys: string[];

  /**
   * What the dev type dropdown does in DA mode for this council.
   * chapter_selector  — selects which devTypeGatedPartKeys are active (Ashfield)
   * subpart_selector  — selects primary sub-part within zone-gated chapters + sort (Marrickville)
   * sort_only         — relevance sort only, no section filtering (Leichhardt)
   */
  daDevTypeRole: 'chapter_selector' | 'subpart_selector' | 'sort_only';
  availableDevTypes?: { id: string; name: string; count: number }[];
  topicFilterRequired: boolean;
  warningThreshold: number;
  resultGuidance: {
    DA_expected: string;
    CDC_expected: string;
  };
  suggestedTopics: string[];
  topicOrder: {
    certifier: string[];
    planner: string[];
  };
  // Council-specific layer labels
  layerLabels: {
    generic: string;
    use_specific: string;
    condition: string;
    precinct: string;
  };
  // Hide layers with 0 or minimal provisions
  hideLayers?: ('generic' | 'use_specific' | 'condition' | 'precinct')[];
  // Category groupings for UI display
  categoryGroups: Record<string, CategoryGroup>;
  // Fallback setback guidance when DB has no data
  setbackFallback?: SetbackFallback;
}

/**
 * Returns true if the given part key is a "universal" chapter for this council —
 * one that must always be shown to the planner and cannot be auto-dismissed
 * by dev type. Use this as a guard in auto-dismiss logic.
 *
 * Note: zone/heritage/precinct gating still applies for chapters NOT in
 * universalPartKeys — those are handled by the for-property API layer system.
 */
export function isUniversalChapter(councilId: string | null, partKey: string): boolean {
  const config = getCouncilConfig(councilId);
  return config.universalPartKeys.includes(partKey);
}

/**
 * Returns true if dev type is a legitimate structural gate for this chapter —
 * i.e. the DCP document itself partitions this chapter by dev category.
 * Auto-dismissing non-matching parts is architecturally defensible.
 */
export function isDevTypeGatedChapter(councilId: string | null, partKey: string): boolean {
  const config = getCouncilConfig(councilId);
  return config.devTypeGatedPartKeys.some(k => partKey === k || partKey.startsWith(k));
}

/**
 * Returns the role of the dev type dropdown in DA mode for this council.
 * Use this to control what downstream filtering the dropdown triggers.
 */
export function getDaDevTypeRole(councilId: string | null): CouncilConfig['daDevTypeRole'] {
  return getCouncilConfig(councilId).daDevTypeRole;
}

/**
 * Inner West LGA Overview - shown as collapsible header for all Inner West addresses
 */
export const INNER_WEST_OVERVIEW = `Inner West Council was formed in 2016 from three former councils: Ashfield, Leichhardt, and Marrickville. Each retains its own DCP with distinct organizational approaches. Your address determines which former council's DCP applies.

MARRICKVILLE (1,866 provisions) has chapters for residential, commercial, and industrial development, but the majority of provisions are in Part 2 Generic Provisions which apply universally. Heritage has a dedicated chapter (Part 8) covering 37 Heritage Conservation Areas. Precinct Character controls (Part 9) cover 48 suburb areas with desired future character statements.

LEICHHARDT (3,355 provisions) is topic-centric with the highest provision count. Heritage provisions are distributed across multiple topics rather than consolidated in a dedicated chapter. The 26 Distinctive Neighbourhood controls provide character guidance for specific areas. Use topic filters and DCP Part accordions to navigate.

ASHFIELD (1,892 provisions) is heritage-focused with Chapter E1 providing extensive controls for Heritage Conservation Areas including conservation principles, character assessment, building form, and materials guidance. The 11 Village Precinct controls cover urban village areas with local character guidance.

All three DCPs use topic-based filtering. Select a topic to see relevant provisions grouped by DCP Part.`;

/**
 * Council configurations loaded from JSON files
 * Key: council ID (lowercase)
 * Value: CouncilConfig object
 */
export const COUNCIL_CONFIGS: Record<string, CouncilConfig> = {
  marrickville: marrickvilleConfig as CouncilConfig,
  leichhardt: leichhardtConfig as CouncilConfig,
  ashfield: ashfieldConfig as CouncilConfig,
  waverley: waverleyConfig as CouncilConfig,
  woollahra: woollahraConfig as CouncilConfig,
  city_of_sydney: cityOfSydneyConfig as CouncilConfig,
  ku_ring_gai: kuRingGaiConfig as CouncilConfig,
};

/**
 * Aliases for council detection
 * Maps various name variations to canonical council IDs
 */
const COUNCIL_ALIASES: Record<string, string> = {
  // Inner West councils
  'marrickville': 'marrickville',
  'leichhardt': 'leichhardt',
  'ashfield': 'ashfield',
  // Eastern Suburbs / North Shore
  'waverley': 'waverley',
  'woollahra': 'woollahra',
  'city_of_sydney': 'city_of_sydney',
  'sydney': 'city_of_sydney',
  'ku_ring_gai': 'ku_ring_gai',
  'ku-ring-gai': 'ku_ring_gai',
};

/**
 * Detect council from LGA or formerCouncil field
 * Returns the canonical council ID or null if not found
 */
export function detectCouncil(lga?: string, formerCouncil?: string): string | null {
  const council = (formerCouncil || '').toLowerCase().trim();
  const lgaLower = (lga || '').toLowerCase().trim();

  // Check direct match first
  if (council && COUNCIL_CONFIGS[council]) {
    return council;
  }

  // Check aliases
  for (const [alias, id] of Object.entries(COUNCIL_ALIASES)) {
    if (council.includes(alias) || lgaLower.includes(alias)) {
      return id;
    }
  }

  // Default for Inner West if not specific
  if (lgaLower.includes('inner west')) {
    // Could try to detect from address/precinct, for now return null
    return null;
  }

  return null;
}

/**
 * Get council config by ID, with fallback to marrickville defaults
 */
export function getCouncilConfig(councilId: string | null): CouncilConfig {
  if (councilId && COUNCIL_CONFIGS[councilId]) {
    return COUNCIL_CONFIGS[councilId];
  }
  // Default fallback
  return COUNCIL_CONFIGS.marrickville;
}

/**
 * Get all configured council IDs
 */
export function getConfiguredCouncils(): string[] {
  return Object.keys(COUNCIL_CONFIGS);
}

/**
 * Check if a council is configured
 */
export function isCouncilConfigured(councilId: string): boolean {
  return councilId in COUNCIL_CONFIGS;
}

/**
 * Get council config by LGA name (handles aliases and fuzzy matching)
 */
export function getCouncilConfigByLGA(lgaName: string): CouncilConfig | null {
  const councilId = detectCouncil(lgaName);
  if (councilId) {
    return COUNCIL_CONFIGS[councilId];
  }
  return null;
}

/**
 * Get setback fallback guidance for a council
 * Used when database has no setback data for the property
 */
export function getSetbackFallback(councilId: string | null): SetbackFallback {
  const config = getCouncilConfig(councilId);
  if (config.setbackFallback) {
    return config.setbackFallback;
  }
  // Default fallback if not configured
  return {
    type: 'not_available',
    message: `Setback data not yet available for ${config.name}`,
    method: 'Refer to DCP provisions or contact Council'
  };
}

/**
 * Topic display labels
 */
export const TOPIC_LABELS: Record<string, string> = {
  setbacks: 'Setbacks',
  setback_front: 'Front Setback',
  setback_side: 'Side Setback',
  setback_rear: 'Rear Setback',
  height: 'Height & Envelope',
  building_height: 'Building Height',
  parking: 'Parking',
  heritage: 'Heritage',
  landscaping: 'Landscaping',
  building_form: 'Building Form & Character',
  building_design: 'Building Design',
  solar: 'Solar Access',
  solar_access: 'Solar Access',
  privacy: 'Privacy',
  access: 'Access & Movement',
  accessibility: 'Accessibility',
  vehicle_access: 'Vehicle Access',
  bicycle_parking: 'Bicycle Parking',
  trees: 'Trees & Vegetation',
  tree_preservation: 'Tree Preservation',
  waste: 'Waste Management',
  waste_management: 'Waste Management',
  stormwater: 'Stormwater',
  water: 'Water Management',
  water_management: 'Water Management',
  flooding: 'Flooding',
  flood_management: 'Flood Management',
  signage: 'Signage',
  fencing: 'Fencing',
  contamination: 'Site Contamination',
  views: 'Views',
  environmental: 'Environmental',
  wsud: 'Water Sensitive Urban Design',
  safety: 'Safety & Security',
  site_analysis: 'Site Analysis',
  open_space: 'Open Space',
  general: 'General',
  precinct: 'Precinct Controls',
  site_specific: 'Site Specific',
  roofing: 'Roofing',
  energy: 'Energy & BASIX',
  other: 'Other Requirements',
  streetscape: 'Streetscape',
  subdivision: 'Subdivision',
  character: 'Character',
  sustainability: 'Sustainability',
  energy_efficiency: 'Energy Efficiency',
  biodiversity: 'Biodiversity',
  social_impact: 'Social Impact',
  transport: 'Transport',
  amenity: 'Amenity',
  acoustic: 'Acoustic',
  health_wellbeing: 'Health & Wellbeing',
  land_use: 'Land Use',
  location: 'Location',
  da_requirements: 'DA Requirements',
  drainage: 'Drainage',
};

/**
 * Sort topics by professional priority order
 */
export function sortTopicsByPriority(
  topics: string[],
  councilId: string | null,
  mode: 'certifier' | 'planner' = 'certifier'
): string[] {
  const config = getCouncilConfig(councilId);
  const priorityOrder = config.topicOrder[mode];

  return [...topics].sort((a, b) => {
    const aIndex = priorityOrder.indexOf(a);
    const bIndex = priorityOrder.indexOf(b);

    // If both in priority list, sort by priority
    if (aIndex !== -1 && bIndex !== -1) {
      return aIndex - bIndex;
    }
    // Priority list items come first
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    // Otherwise alphabetical
    return a.localeCompare(b);
  });
}

/**
 * Get category groups sorted by priority
 */
export function getSortedCategoryGroups(councilId: string | null): Array<{
  key: string;
  group: CategoryGroup;
}> {
  const config = getCouncilConfig(councilId);
  return Object.entries(config.categoryGroups)
    .map(([key, group]) => ({ key, group }))
    .sort((a, b) => a.group.priority - b.group.priority);
}

/**
 * Find which group a category belongs to
 */
export function getCategoryGroup(
  category: string,
  councilId: string | null
): { groupKey: string; group: CategoryGroup } | null {
  const config = getCouncilConfig(councilId);
  const lowerCategory = category.toLowerCase();

  for (const [groupKey, group] of Object.entries(config.categoryGroups)) {
    if (group.categories.includes(lowerCategory)) {
      return { groupKey, group };
    }
  }

  // Default to 'other' group if not found
  if (config.categoryGroups.other) {
    return { groupKey: 'other', group: config.categoryGroups.other };
  }

  return null;
}

/**
 * Group provisions by category group
 */
export function groupProvisionsByCategory<T extends { category?: string }>(
  provisions: T[],
  councilId: string | null
): Record<string, { group: CategoryGroup; provisions: T[]; subcategories: Record<string, T[]> }> {
  const config = getCouncilConfig(councilId);
  const grouped: Record<string, { group: CategoryGroup; provisions: T[]; subcategories: Record<string, T[]> }> = {};

  // Initialize all groups
  for (const [groupKey, group] of Object.entries(config.categoryGroups)) {
    grouped[groupKey] = { group, provisions: [], subcategories: {} };
  }

  // Assign provisions to groups
  for (const provision of provisions) {
    const category = (provision.category || 'other').toLowerCase();
    const result = getCategoryGroup(category, councilId);

    if (result) {
      const { groupKey, group } = result;
      grouped[groupKey].provisions.push(provision);

      // Track subcategories if group shows them
      if (group.showSubcategories) {
        if (!grouped[groupKey].subcategories[category]) {
          grouped[groupKey].subcategories[category] = [];
        }
        grouped[groupKey].subcategories[category].push(provision);
      }
    }
  }

  return grouped;
}

/**
 * Category display labels (for subcategories)
 */
export const CATEGORY_LABELS: Record<string, string> = {
  setback_front: 'Front Setback',
  setback_side: 'Side Setback',
  setback_rear: 'Rear Setback',
  setbacks: 'General Setbacks',
  building_form: 'Building Form',
  building_height: 'Building Height',
  tree_preservation: 'Tree Preservation',
  waste_management: 'Waste Management',
  water_management: 'Water Management',
  solar_access: 'Solar Access',
  site_area: 'Site Area',
  site_coverage: 'Site Coverage',
  deep_soil: 'Deep Soil',
  open_space: 'Open Space',
  da_requirements: 'DA Requirements',
  health_wellbeing: 'Health & Wellbeing',
  flood_management: 'Flood Management',
  energy_efficiency: 'Energy Efficiency',
  social_impact: 'Social Impact',
  public_domain: 'Public Domain',
  public_art: 'Public Art',
};
